"""
==============================================================================
FMS_FILE_SPEC
workflow.py - LangGraph 분석 흐름
==============================================================================
설명:
    - LangGraph 분석 흐름
입력·출력 명세:
    - 입력: 분석 실행 ID·원본 revision ID·저장된 checkpoint
    - 출력: 추출·계획·해석·연결·Excel 단계의 결과 ID
실행 가정:
    - 큰 원문은 저장소에 두고 checkpoint는 ID 위주로 유지
작성 정보:
    - 작성자: 김재현(Finn)
    - 이메일: penguin.klg@gmail.com
    - 작성일: 2026-10-21 (최초 Git 등록일 기준)
    - 라이선스: 미지정
    - 버전: 0.1.0
    - 상태: Development
변경 이력 (Revision History):
    DATE        AUTHOR      VERSION  DESCRIPTION
    --------------------------------------------------------------------
    2026-10-21  미지정      v0.1.0   최초 Git 등록 a11ef05a
    2026-10-21  미지정      v0.1.0   파일 역할·입출력·가정·이력 명세 추가

    2026-10-21  김재현(Finn) v0.1.0   Agent 도구 선택 기반 리빌드·업무 경계 및 검증

    2026-10-22  김재현(Finn) v0.1.0   자료·Agent·검수 승인·식품 DB 중심 흐름 및 알레르기 표기 정리

    2026-10-22  김재현(Finn) v0.1.0   25MB·표 삽입 이미지 근거 보완 및 검수 오류 개선

    상세 Git 이력: git log --follow -- backend/app/domains/analysis/workflow.py
    공통 규칙: doc/file-header-policy.md

기존 모듈 설명:
    Small durable LangGraph state: IDs only; source bodies live in storage.
==============================================================================
"""

# FMS_MODULE_METADATA_BEGIN
__author__ = "김재현(Finn)"
__email__ = "penguin.klg@gmail.com"
__version__ = "0.1.0"
__status__ = "Development"
# FMS_MODULE_METADATA_END

# ---------------------------------------------------------------------------
# 1. Imports / Module implementation
# ---------------------------------------------------------------------------

import re
import time
import asyncio
from typing import TypedDict
from langgraph.graph import StateGraph
from langgraph.graph import START
from langgraph.graph import END
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from backend.app.runtime.execution import ATTEMPT_START
from backend.app.runtime.limits import EXTRACTION_BYTES
from backend.app.infrastructure.database import DSN
from backend.app.infrastructure.database import Problem
from backend.app.infrastructure.database import entities
from backend.app.infrastructure.database import get
from backend.app.infrastructure.database import now
from backend.app.infrastructure.database import put
from backend.app.infrastructure.database import tx
from backend.app.infrastructure.database import uid
from backend.app.parsers.documents import parse
from backend.app.domains.ingestion.documents import DATA
from backend.app.domains.review.proposals import create
from backend.app.infrastructure.contracts import schema_check

class State(TypedDict,total=False):
    run_id:str
    revision_id:str
    proposal_id:str
    extraction_id:str
    agent_report_id:str
    proposal_ids:list[str]
    export_asset_id:str

def check_running(c,run):
    if run.get('job_id'):
        r=c.execute('SELECT status,fence FROM jobs WHERE id=%s',(run['job_id'],)).fetchone()
        if r and run.get('active_fence') and r['fence']!=run['active_fence']:raise Problem(409,'LEASE_LOST','분석 실행 권한이 만료되었습니다.')
        if r and r['status']=='cancelled':raise Problem(409,'CANCELLED','취소된 분석입니다.')

def get_asset_key(asset_id):
    with tx() as c:return get(c,'asset',asset_id)['storage_key']

def extract(state):
    previous=None
    with tx() as c:
        run=get(c,'analysis_run',state['run_id']);check_running(c,run);r=get(c,'revision',state['revision_id']);a=get(c,'asset',r['snapshot_asset_id'])
        if run.get('extraction_id'):
            previous=get(c,'extraction',run['extraction_id'])
            if previous.get('parser_version')=='food-parser-v7' or previous.get('parser_version') in ('food-parser-v4','food-parser-v5','food-parser-v6') and run.get('agent_report_id'):return {'extraction_id':run['extraction_id']}
    blocks=[];parse_issues=[];eid=uid();started=time.monotonic();extracted_bytes=0
    for index,asset in enumerate(r['assets']):
        with tx() as c:
            current=get(c,'analysis_run',state['run_id']);check_running(c,current)
            if current.get('job_id'):
                from backend.app.domains.jobs.service import getjob; from backend.app.domains.jobs.service import savejob
                job=getjob(c,current['job_id'],True);job.update(stage=f"첨부 {index+1}/{len(r['assets'])} · {asset['filename']} 추출",processed_count=index,total_count=len(r['assets']));savejob(c,job)
                c.execute("UPDATE jobs SET lease_until=now()+interval '15 minutes' WHERE id=%s",(job['id'],))
        if time.monotonic()-started>600:raise Problem(422,'ANALYSIS_DEADLINE','문서 처리 시간이 초과되었습니다. 자료를 나누어 주세요.')
        try:
            if asset['id']==r['snapshot_asset_id'] and not r['body_text'].strip() and len(r['assets'])>1:continue
            reusable=[b for b in (previous or {}).get('segments',[]) if b.get('asset_id')==asset['id']]
            parts=reusable if reusable and not asset['filename'].lower().endswith(('.xlsx','.xls')) else parse(DATA/get_asset_key(asset['id']),asset['filename'])
            for b in parts:b['asset_id']=asset['id']
            extracted_bytes+=sum(len(b['text'].encode()) for b in parts)
            if extracted_bytes>EXTRACTION_BYTES:raise Problem(422,'EXTRACTION_MEMORY_BUDGET','자료의 추출 텍스트가 메모리 예산을 초과했습니다. 자료를 나눠 주세요.')
            blocks.extend(parts)
        except Problem as ex:
            if ex.code=='EXTRACTION_MEMORY_BUDGET':raise
            parse_issues.append({'asset_id':asset['id'],'code':ex.code,'message':ex.message})
    if not blocks:raise Problem(422,'EXTRACTION_FAILED',parse_issues[0]['message'] if parse_issues else '추출할 내용이 없습니다.')
    if len(blocks)>2000:raise Problem(422,'SEGMENT_LIMIT','문서 전체 추출 구간이 2,000개를 초과했습니다.')
    with tx() as c:
        check_running(c,get(c,'analysis_run',state['run_id'],True))
        for i,b in enumerate(blocks):b['evidence_id']=uid();b['id']=f'segment-{i}'
        row_evidence={(b['asset_id'],b['locator'].get('sheet_name'),re.search(r'\d+',b['locator'].get('cell_range',''))[0]):b['evidence_id'] for b in blocks if b['locator'].get('kind')=='spreadsheet' and re.search(r'\d+',b['locator'].get('cell_range',''))}
        for i,b in enumerate(blocks):
            loc=b['locator']
            if loc['kind'] in ('image','pdf','spreadsheet'):loc['asset_id']=b['asset_id']
            ev={'id':b['evidence_id'],'document_revision_id':r['id'],'source_url':get(c,'document',r['document_id'])['source_url'],'quote':b['text'],'locator':loc,'extraction_id':eid,'ocr_confidence':b['confidence'],'created_at':now()};put(c,'evidence',ev)
            b['evidence_id']=ev['id'];b['id']=f'segment-{i}'
            if b.get('food_record'):
                for field,source in b['food_record']['field_sources'].items():
                    anchor=re.search(r'\d+',source.get('locator',{}).get('cell_range',''))
                    related=row_evidence.get((b['asset_id'],loc.get('sheet_name'),anchor[0])) if anchor and source.get('origin')=='merged_cell' else None
                    source.update(evidence_ids=list(dict.fromkeys([ev['id']]+([related] if related else []))),document_revision_id=r['id'])
                    source['locator']['asset_id']=b['asset_id']
        put(c,'extraction',{'id':eid,'revision_id':r['id'],'segments':blocks,'parser_version':'food-parser-v7','issues':parse_issues,'created_at':now()})
        run=get(c,'analysis_run',state['run_id'],True);run['extraction_id']=eid;put(c,'analysis_run',run)
        r['extraction_ids']=[eid];r['segment_manifest_id']=eid;r['parse_issues']=parse_issues;put(c,'revision',r)
    return {'extraction_id':eid}

def rule_changes(c,extraction):
    """Deliberately narrow, explicit template; never guesses ambiguous notice semantics."""
    changes=[]
    for block in extraction['segments']:
        # item CODE | 공급 일시중단/공급 재개/공급 종료 | ISO date | reason
        # price CODE | decimal amount | ISO date | reason
        m=re.fullmatch(r'(item|price)\s+([^|]+)\s*\|\s*([^|]+)\s*\|\s*(\d{4}-\d{2}-\d{2})\s*\|\s*(.+)',block['text'])
        if not m:continue
        typ,code,value,start,reason=[s.strip() for s in m.groups()]
        candidates=[x for x in entities(c,'supplier_item') if x['supplier_code']==code]
        if len(candidates)!=1:raise Problem(422,'AMBIGUOUS_PRODUCT','품목코드가 중복되거나 없습니다. 수동 변경안으로 정확한 상품을 연결하세요.')
        item=candidates[0];op={'kind':'set_price' if typ=='price' else 'set_availability','supplier_item_ref':{'id':item['id']},'period':{'effective_from':start,'effective_to':None},'reason':{'original_text':reason,'summary':reason,'code':None},'supersedes_fact_id':None}
        if typ=='price':
            if not re.fullmatch(r'\d+(\.\d{1,4})?',value):raise Problem(422,'PRICE_FORMAT','가격은 10진 숫자로 입력하세요.')
            op['value']={'amount':value,'currency':'KRW','quantity':'1','unit':'kg','tax':'unknown','price_kind':'regular','condition_key':'public'}
        else:
            statuses={'공급 일시중단':'temporarily_unavailable','공급 재개':'available','공급 종료':'supply_ended'}
            if value not in statuses:raise Problem(422,'STATUS_UNCLEAR','공급 상태를 확정할 수 없습니다.')
            op['status']=statuses[value]
        changes.append({'id':uid(),'operation':op,'field_evidence':[{'field_path':'/'+k,'evidence_ids':[block['evidence_id']],'origin':'extracted'} for k in op if k not in ('kind','supersedes_fact_id')]})
    if not changes:raise Problem(422,'MANUAL_REVIEW_REQUIRED','규칙 분석 형식과 일치하지 않습니다. 추출 근거를 확인해 수동 변경안을 작성하거나 모델 분석을 설정하세요.')
    return changes

def propose(state):
    """Explicit fixture/demo path only. Production agent nodes are selected below."""
    with tx() as c:
        run=get(c,'analysis_run',state['run_id']);check_running(c,run);r=get(c,'revision',state['revision_id'])
        if run.get('proposal_id'):return {'proposal_id':run['proposal_id']}
        changes=rule_changes(c,get(c,'extraction',state['extraction_id']))
        schema_check('ProposalCreate',{'title':r['title'],'source_document_revision_ids':[r['id']],'changes':changes})
        p=create(c,r['title'],[r['id']],changes,state['run_id']);run['proposal_id']=p['summary']['id'];put(c,'analysis_run',run)
        doc=get(c,'document',r['document_id']);doc['proposal_count']+=1;doc['analysis_status']='completed';put(c,'document',doc)
    return {'proposal_id':p['summary']['id']}

def route_after_tools(state):
    with tx() as c:report=get(c,'agent_report',state['agent_report_id'])
    return 'match' if 'match_catalog' in report['plan']['tasks'] else 'export'


def run_analysis(runid,rid):
    return asyncio.run(arun_analysis(runid,rid))

async def arun_analysis(runid,rid):
    with tx() as c:mode=get(c,'analysis_run',runid)['mode']
    async with AsyncPostgresSaver.from_conn_string(DSN) as checkpointer:
        graph=StateGraph(State);graph.add_node('extract',extract)
        if mode=='rules':
            graph.add_node('propose',propose);nodes=['extract','propose']
        else:
            from backend.app.domains.analysis.agent import plan; from backend.app.domains.analysis.agent import interpret; from backend.app.domains.analysis.matching import match_candidates
            from backend.app.domains.analysis.export import export_review
            for name,fn in [('plan',plan),('execute_tools',interpret),('match',match_candidates),('export',export_review)]:graph.add_node(name,fn)
            nodes=['extract','plan','execute_tools','match','export']
        graph.add_edge(START,nodes[0])
        for first,second in zip(nodes,nodes[1:]):
            if mode!='rules' and first=='execute_tools':
                graph.add_conditional_edges(first,route_after_tools,{'match':'match','export':'export'})
            else:graph.add_edge(first,second)
        graph.add_edge(nodes[-1],END)
        token=ATTEMPT_START.set(time.monotonic())
        try:return await graph.compile(checkpointer=checkpointer).ainvoke({'run_id':runid,'revision_id':rid},{'configurable':{'thread_id':f'analysis:{runid}'}})
        finally:ATTEMPT_START.reset(token)
