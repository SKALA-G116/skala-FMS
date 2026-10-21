"""Small durable LangGraph state: IDs only; source bodies live in storage."""
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
    with tx() as c:
        run=get(c,'analysis_run',state['run_id']);check_running(c,run);r=get(c,'revision',state['revision_id']);a=get(c,'asset',r['snapshot_asset_id'])
        if run.get('extraction_id'):
            previous=get(c,'extraction',run['extraction_id'])
            if previous.get('parser_version')=='food-parser-v4':return {'extraction_id':run['extraction_id']}
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
            parts=parse(DATA/get_asset_key(asset['id']),asset['filename'])
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
        for i,b in enumerate(blocks):
            loc=b['locator']
            if loc['kind'] in ('image','pdf','spreadsheet'):loc['asset_id']=b['asset_id']
            ev={'id':uid(),'document_revision_id':r['id'],'source_url':get(c,'document',r['document_id'])['source_url'],'quote':b['text'],'locator':loc,'extraction_id':eid,'ocr_confidence':b['confidence'],'created_at':now()};put(c,'evidence',ev)
            b['evidence_id']=ev['id'];b['id']=f'segment-{i}'
            if b.get('food_record'):
                for field,source in b['food_record']['field_sources'].items():
                    source.update(evidence_ids=[ev['id']],document_revision_id=r['id'])
                    source['locator']['asset_id']=b['asset_id']
        put(c,'extraction',{'id':eid,'revision_id':r['id'],'segments':blocks,'parser_version':'food-parser-v4','issues':parse_issues,'created_at':now()})
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

def run_analysis(runid,rid):
    return asyncio.run(arun_analysis(runid,rid))

async def arun_analysis(runid,rid):
    with tx() as c:mode=get(c,'analysis_run',runid)['mode']
    async with AsyncPostgresSaver.from_conn_string(DSN) as checkpointer:
        graph=StateGraph(State);graph.add_node('extract',extract)
        if mode=='rules':
            graph.add_node('propose',propose);nodes=['extract','propose']
        else:
            from backend.app.domains.analysis.agent import plan; from backend.app.domains.analysis.agent import interpret; from backend.app.domains.analysis.agent import resolve_and_stage
            from backend.app.domains.analysis.export import export_review
            for name,fn in [('plan',plan),('interpret',interpret),('resolve',resolve_and_stage),('export',export_review)]:graph.add_node(name,fn)
            nodes=['extract','plan','interpret','resolve','export']
        graph.add_edge(START,nodes[0])
        for first,second in zip(nodes,nodes[1:]):graph.add_edge(first,second)
        graph.add_edge(nodes[-1],END)
        token=ATTEMPT_START.set(time.monotonic())
        try:return await graph.compile(checkpointer=checkpointer).ainvoke({'run_id':runid,'revision_id':rid},{'configurable':{'thread_id':f'analysis:{runid}'}})
        finally:ATTEMPT_START.reset(token)
