"""
==============================================================================
FMS_FILE_SPEC
server.py - 식품 도메인 MCP stdio 제공
==============================================================================
설명:
    - 식품 도메인 MCP stdio 제공
입력·출력 명세:
    - 입력: Tool 인자·Resource URI·Prompt 이름·선택 host 모드
    - 출력: 제한된 조회/초안 Tool 결과·정책/근거·작업 안내
실행 가정:
    - 기본 서버에 승인·최종 반영·임의 SQL을 노출하지 않음
작성 정보:
    - 작성자: 미지정
    - 이메일: 미지정
    - 작성일: 2026-10-21 (최초 Git 등록일 기준)
    - 라이선스: 미지정
    - 버전: 0.1.0
    - 상태: Development
변경 이력 (Revision History):
    DATE        AUTHOR      VERSION  DESCRIPTION
    --------------------------------------------------------------------
    2026-10-21  미지정      v0.1.0   최초 Git 등록 a11ef05a
    2026-10-21  미지정      v0.1.0   파일 역할·입출력·가정·이력 명세 추가

    상세 Git 이력: git log --follow -- backend/app/mcp/server.py
    공통 규칙: doc/file-header-policy.md

기존 모듈 설명:
    Local stdio adapter. Default mode exposes only read tools to model clients.
    Host-only tools are registered only with --host, in a separate trusted process.
    Never pass the host server to the model's tool registry.
==============================================================================
"""

# FMS_MODULE_METADATA_BEGIN
__author__ = "미지정"
__email__ = "미지정"
__version__ = "0.1.0"
__status__ = "Development"
# FMS_MODULE_METADATA_END

# ---------------------------------------------------------------------------
# 1. Imports / Module implementation
# ---------------------------------------------------------------------------

import json
import sys
from fastmcp import FastMCP
from backend.app.infrastructure.database import ROOT
from datetime import date
from backend.app.infrastructure.database import entity
from backend.app.infrastructure.database import get
from backend.app.infrastructure.database import init
from backend.app.infrastructure.database import now
from backend.app.infrastructure.database import pool
from backend.app.infrastructure.database import tx
from backend.app.domains.review.proposals import create
from backend.app.domains.review.proposals import validate
from backend.app.infrastructure.contracts import schema_check
from backend.app.domains.catalog.queries import active_facts

mcp=FastMCP('Food Ledger')

HOST='--host' in sys.argv

def bounded(value):
    if len(json.dumps(value,ensure_ascii=False).encode())>32768:raise ValueError('Result exceeds 32 KiB. Request fewer records.')
    return value

@mcp.tool(annotations={'readOnlyHint': True})
def find_product_candidates(query:str,limit:int=10)->dict:
    """Search exact catalog references. Never writes catalog data."""
    if not 1<=limit<=20 or not 1<=len(query)<=200:raise ValueError('query/limit out of bounds')
    with tx() as c:
        rows=c.execute("SELECT data,id,version FROM catalog_entities WHERE name ILIKE %s ORDER BY id LIMIT %s",('%'+query+'%',limit)).fetchall()
        return bounded({'items':[{**r['data'],'id':str(r['id']),'version':r['version']} for r in rows],'queried_at':now()})

@mcp.tool(annotations={'readOnlyHint': True})
def get_supplier_item_facts(ids:list[str],as_of:str)->dict:
    """Read versioned facts at an explicit business date."""
    if not 1<=len(ids)<=20:raise ValueError('max 20 IDs')
    from datetime import date
    date.fromisoformat(as_of)
    with tx() as c:return bounded({'items':[{'entity':entity(c,id),'prices':active_facts(c,id,'set_price',as_of),'availability':active_facts(c,id,'set_availability',as_of)} for id in ids],'as_of':as_of,'queried_at':now()})

@mcp.tool(annotations={'readOnlyHint': True})
def get_product_history(product_id:str,limit:int=10)->dict:
    """Read immutable product audit events."""
    if not 1<=limit<=20:raise ValueError('max 20')
    with tx() as c:return bounded({'items':[r['data'] for r in c.execute("SELECT data FROM app_records WHERE kind='audit' AND data->>'product_id'=%s ORDER BY created_at DESC LIMIT %s",(product_id,limit))]})

if HOST:
    @mcp.tool()
    def parse_document_segment(document_revision_id:str)->dict:
        """Trusted host: register durable bounded analysis. Does not execute OCR in MCP."""
        from backend.app.domains.jobs.service import enqueue
        with tx() as c:
            from backend.app.domains.analysis.service import queue_analysis
            run,job=queue_analysis(c,document_revision_id)
            from backend.app.domains.jobs.service import getjob
            return bounded(job or getjob(c,run['job_id']))

    @mcp.tool()
    def validate_change_set(proposal_id:str)->dict:
        """Trusted host: report issues only; does not mutate the stored proposal."""
        with tx() as c:
            p=get(c,'proposal',proposal_id);validate(c,p);return bounded({'issues':p['issues'],'target_versions':p['target_versions']})
    @mcp.tool()
    def stage_change_proposal(title:str,document_revision_ids:list[str],changes:list[dict])->dict:
        """Trusted host: save review draft only. Never approve or apply."""
        schema_check('ProposalCreate',{'title':title,'source_document_revision_ids':document_revision_ids,'changes':changes})
        with tx() as c:
            p=create(c,title,document_revision_ids,changes);return bounded({'proposal_id':p['summary']['id'],'status':p['summary']['status'],'issues':p['issues']})

@mcp.resource('food://schemas/{schema_version}')
def schema_resource(schema_version:str)->str:
    if schema_version!='food-change-v1':raise ValueError('unknown version')
    return json.dumps(bounded(json.loads((ROOT/'doc/food-agent/schemas/food-change-v1.json').read_text())),ensure_ascii=False)

@mcp.resource('food://policies/{policy_version}')
def policy_resource(policy_version:str)->str:
    if policy_version!='food-policy-v1':raise ValueError('unknown version')
    return (ROOT/'doc/food-agent/policies/food-policy-v1.md').read_text()

@mcp.resource('food://documents/{revision_id}/segments/{segment_id}')
def document_segment(revision_id:str,segment_id:str)->str:
    with tx() as c:
        rev=get(c,'revision',revision_id)
        if not rev['extraction_ids']:raise ValueError('parse not complete; resource read never starts parsing')
        return extraction_segment(rev['extraction_ids'][0],segment_id)

@mcp.resource('food://extractions/{extraction_id}/segments/{segment_id}')
def extraction_segment(extraction_id:str,segment_id:str)->str:
    with tx() as c:
        ex=get(c,'extraction',extraction_id);seg=next((s for s in ex['segments'] if s['id']==segment_id),None)
        if not seg:raise ValueError('segment not found')
        return json.dumps(bounded(seg),ensure_ascii=False)

@mcp.resource('food://evidence/{evidence_id}')
def evidence_resource(evidence_id:str)->str:
    with tx() as c:return json.dumps(bounded(get(c,'evidence',evidence_id)),ensure_ascii=False)

@mcp.prompt()
def analyze_food_notice()->str:return (ROOT/'doc/food-agent/prompts/notice-v1.md').read_text()

@mcp.prompt()
def analyze_price_table()->str:return (ROOT/'doc/food-agent/prompts/price-table-v1.md').read_text()

@mcp.prompt()
def review_change_evidence()->str:return (ROOT/'doc/food-agent/prompts/review-evidence-v1.md').read_text()

if __name__=='__main__':
    init()
    try:mcp.run(transport='stdio',show_banner=False)
    finally:pool.close()
