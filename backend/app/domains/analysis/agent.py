"""
==============================================================================
FMS_FILE_SPEC
agent.py - LLM 계획·추출과 근거 연결
==============================================================================
설명:
    - LLM 계획·추출과 근거 연결
입력·출력 명세:
    - 입력: 분할 원문 구간·JSON 스키마·분석 실행 ID
    - 출력: 표준 식품 변경 후보·근거·모델 호출 기록
실행 가정:
    - 모델 후보는 승인이나 DB 반영을 대신하지 않음
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

    2026-10-21  미지정      v0.1.0   업체 표 직접 정규화·중복 통합·원문 이력 보존

    2026-10-21  김재현(Finn) v0.1.0   Agent 도구 선택 기반 리빌드·업무 경계 및 검증

    2026-10-22  김재현(Finn) v0.1.0   이미지 예산 초과 자료 격리·나머지 자료 처리 지속

    2026-10-22  김재현(Finn) v0.1.0   자료·Agent·검수 승인·식품 DB 중심 흐름 및 알레르기 표기 정리

    2026-10-22  김재현(Finn) v0.1.0   25MB·표 삽입 이미지 근거 보완 및 검수 오류 개선

    2026-10-22  김재현(Finn) v0.1.0   라벨 응답 축소·형식 오류 격리·안전한 진단 및 부분 완료 검수

    2026-10-22  김재현(Finn) v0.1.0   원재료 전용 추출·함량 없는 표시사항 보존·OCR 근거 연결 검증

    2026-10-22  김재현(Finn) v0.1.0   OCR 문장 좌표·상품 소속·필드 근거 보존 및 발표 자료 단순화

    상세 Git 이력: git log --follow -- backend/app/domains/analysis/agent.py
    공통 규칙: doc/file-header-policy.md

기존 모듈 설명:
    LLM plans and interprets source facts; host resolves catalog and stages changes.
    Evidence-bound facts and review artifacts remain available even for unresolved data.
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

import json
import re
import asyncio
import functools
from contextvars import ContextVar
from backend.app.runtime.execution import boundary
from backend.app.runtime.execution import report_metrics
from decimal import Decimal
from decimal import InvalidOperation
from datetime import date
from backend.app.infrastructure.database import Problem
from backend.app.infrastructure.database import get
from backend.app.infrastructure.database import now
from backend.app.infrastructure.database import put
from backend.app.infrastructure.database import tx
from backend.app.infrastructure.database import uid
from backend.app.domains.analysis.provider import LocalModel
from backend.app.domains.analysis.schemas import event_schema

_MODEL=ContextVar('food_model')

def managed_model(fn):
    @functools.wraps(fn)
    async def wrapped(state):
        model=LocalModel()
        if hasattr(model,'use_role'):model.use_role('planner' if fn.__name__=='plan' else 'extractor')
        token=_MODEL.set(model)
        try:return await fn(state)
        finally:
            _MODEL.reset(token)
            close=getattr(model,'aclose',None)
            if close:await close()
    return wrapped

async def model_call(model,task,payload,schema,state):
    from backend.app.domains.analysis.workflow import check_running
    def active():
        with tx() as c:check_running(c,get(c,'analysis_run',state['run_id']))
    await asyncio.to_thread(active)
    inference=asyncio.create_task(model.agenerate(task,payload,schema) if hasattr(model,'agenerate') else asyncio.to_thread(model.generate,task,payload,schema))
    try:
        while True:
            done,_=await asyncio.wait([inference],timeout=1)
            await asyncio.to_thread(active)
            from backend.app.runtime.execution import STOP_REQUESTED; from backend.app.runtime.execution import AnalysisYield
            if STOP_REQUESTED.is_set():raise AnalysisYield()
            if done:return inference.result()
    finally:
        if not inference.done():
            inference.cancel()
            try:await inference
            except asyncio.CancelledError:pass

def save_report(c,report,state):
    from backend.app.domains.analysis.workflow import check_running
    from backend.app.domains.jobs.service import getjob; from backend.app.domains.jobs.service import savejob
    run=get(c,'analysis_run',state['run_id']);check_running(c,run);metrics=report_metrics(report)
    put(c,'agent_report',report)
    if run.get('job_id'):
        job=getjob(c,run['job_id'],True);job.update(performance=metrics)
        if report.get('coverage',{}).get('total_batches'):
            job.update(processed_count=report['batches_completed'],total_count=report['coverage']['total_batches'])
        savejob(c,job)

def progress(runid,stage):
    from backend.app.domains.analysis.workflow import check_running
    from backend.app.domains.jobs.service import getjob; from backend.app.domains.jobs.service import savejob
    with tx() as c:
        run=get(c,'analysis_run',runid);check_running(c,run)
        if run.get('job_id'):
            j=getjob(c,run['job_id'],True);j['stage']=stage;savejob(c,j);c.execute("UPDATE jobs SET lease_until=now()+interval '15 minutes' WHERE id=%s",(j['id'],))

@managed_model
async def plan(state):
    with tx() as c:
        run=get(c,'analysis_run',state['run_id']);r=get(c,'revision',state['revision_id']);doc=get(c,'document',r['document_id']);ex=get(c,'extraction',state['extraction_id'])
        if run.get('agent_report_id'):return {'agent_report_id':run['agent_report_id']}
    model=_MODEL.get();progress(state['run_id'],'AI가 문서 종류와 처리 계획을 판단하는 중')
    from backend.app.domains.analysis.consolidation import enrich_tables
    from backend.app.domains.analysis.planning import decide
    async def call(task,payload,schema):return await model_call(model,task,payload,schema,state)
    result=await decide(enrich_tables(ex['segments']),r['title'],call)
    with tx() as c:
        report=put(c,'agent_report',{'id':uid(),'analysis_run_id':state['run_id'],'document_revision_id':r['id'],'model':model.name,'plan':result,'events':[],'model_calls':model.calls,'batches_completed':0,'proposal_ids':[],'export_asset_id':None,'status':'interpreting','created_at':now(),'coverage':{'source_segments':len(ex['segments']),'processed_segments':0},'warnings':[]})
        run=get(c,'analysis_run',state['run_id'],True);run['agent_report_id']=report['id'];put(c,'analysis_run',run)
    return {'agent_report_id':report['id']}

def compact_location(locator):
    result={k:v for k,v in locator.items() if k in ('kind','page_number','sheet_name','cell_range','block_id')}
    # Source-specific extraction payloads add normalized OCR boxes when available.
    return result

def model_mapping(segments):
    from backend.app.domains.analysis.spatial import ordered_lines
    rows=ordered_lines(segments) if segments and all(s.get('region_label') for s in segments) else segments
    return {f'S{j+1}':s for j,s in enumerate(rows)}


def source_payload(mapping):
    region=any(s.get('region_label') for s in mapping.values())
    if region:
        # One location per region; compact line objects preserve exact text and boxes.
        return [{'id':key,'text':s['text'],**({'bbox':[round(v*1000) for v in s['locator']['bbox']]} if s['locator'].get('bbox') else {}),'role':s.get('source_role','product')} for key,s in mapping.items()]
    return [{'id':key,'text':s['text'],'location':compact_location(s['locator']),**({'bbox':[round(v*1000) for v in s['locator']['bbox']]} if s['locator'].get('bbox') else {})} for key,s in mapping.items()]

def extraction_payload(revision,document_type,mapping):
    return {'title':revision['title'],'published_at':revision.get('published_at'),'files':[a['filename'][:60] for a in revision.get('assets',[])[:5]], 'document_type':document_type,'source_context':[],'segments':source_payload(mapping), 'location':compact_location(next(iter(mapping.values()))['locator']) if mapping else {},'coordinates':'bbox=[x1,y1,x2,y2] 0~1000; role=product or context','kind_definitions':{'price':'가격이 실제로 명시된 품목 단가','temporarily_unavailable':'일시품절·일시 공급중단','supply_ended':'공급처의 취급·납품 종료','discontinued':'제조사의 생산 단종(일시품절은 해당 안 됨)','available':'정상발주·공급 가능','substitution':'명시된 대체품 관계','new_product':'신제품 소개','food_profile':'가격·공급 변경 없이 식품명·속성·규격을 전달하는 기준정보'},'instructions':'field_evidence에 각 필드의 근거 source_ids를 반환하라. context 역할의 공통 안내를 상품 가격·규격·원재료·알레르기로 사용하지 마라. 좌표의 행·열과 상품 소속을 유지하라. 모든 텍스트·OCR·표에서 식품 정보를 추출하라. 변경 공지가 아니어도 식품 정보가 있으면 kind=food_profile로 추출하라. company_name은 원문에 명시된 업체명이며 제조사·브랜드·판매사 구분 없이 하나로 추출한다. 없으면 null이다. food_code는 원문의 공통식품코드, ingredients_text는 원재료 목록 원문이며 함량이 없는 원재료도 모두 포함하라. attributes_text는 원산지·원재료·등급·용도 등 식품속성 원문, allergen_text는 함유/같은 제조시설/불포함 표시 원문이다. (5,6,12), 5,6,15,18, 5.6.12 같은 학교급식 알레르기 번호도 괄호 유무와 무관하게 해당 상품의 알레르기 원문으로 보존하라. 알레르기 열·설명·상품 위치를 함께 보고 규격·날짜와 혼동하지 마라. 없으면 null이다. 이 구간에 나타난 실제 품목별 변경 사실/표의 가격 행을 추출하라. 원문에 명확하지 않은 필드는 null. 다른 가격 열은 price_basis에 이름을 밝혀라. OCR 조각은 같은 품목의 이름·규격·사유·시작일 근거를 함께 연결하라. source_ids는 제공된 ID만 사용. 공급 중단과 제조 단종을 구별하라. 적용일은 ISO YYYY-MM-DD, 명시되지 않으면 null. 단가는 원문의 판매 규격당 가격이며 자동으로 kg 가격으로 환산하지 말라. quantity는 규격 중 판매 기준의 실제 수량이다. 포장 무게를 수량 1로 잘못 바꾸지 마라. source_ids에는 품목·금액뿐 아니라 적용일과 사유가 나온 구간도 반드시 포함하라.'}


def batches(segments,byte_limit=3000):
    current=[];size=0
    for original in segments:
        # Windows preserve the same immutable evidence ID; no text is silently dropped.
        chunks=[];part='';part_bytes=0
        for char in original['text']:
            char_bytes=len(char.encode())
            if part_bytes+char_bytes>byte_limit-300:chunks.append(part);part='';part_bytes=0
            part+=char;part_bytes+=char_bytes
        if part:chunks.append(part)
        offset=0
        for text in chunks or ['']:
            s={**original,'text':text,'window_start':offset,'window_end':offset+len(text)};offset+=len(text);n=len(text.encode())+200
            if current and (size+n>byte_limit or (current[-1].get('asset_id'),current[-1]['locator'].get('page_number'))!=(s.get('asset_id'),s['locator'].get('page_number')) or len(current)>=(8 if s['locator']['kind']=='spreadsheet' else 60)):yield current;current=[];size=0
            current.append(s);size+=n
    if current:yield current

@managed_model
async def interpret(state):
    with tx() as c:
        report=get(c,'agent_report',state['agent_report_id']);r=get(c,'revision',state['revision_id']);ex=get(c,'extraction',state['extraction_id'])
    from backend.app.domains.catalog.record import upgrade_event
    from backend.app.domains.analysis.consolidation import enrich_tables,table_event,consolidate,VERSION as CONSOLIDATION_VERSION
    ex['segments']=enrich_tables(ex['segments'])
    from backend.app.domains.analysis.planning import selected_sources,image_regions,group_references,restore_groups
    model=_MODEL.get();structured=[];groups=[];execution=[];manual=[]
    async def call(task,payload,schema):return await model_call(model,task,payload,schema,state)
    # Persist expensive layout decisions before executing extraction; resumes reuse
    # them instead of repeating the same planning/model calls.
    if report.get('execution_groups') is not None:
        groups=restore_groups(report['execution_groups'],ex['segments'],report.get('tool_executions'))
        chosen={eid for trace in report.get('tool_executions',[]) if trace['tool']=='normalize_table' for eid in trace['evidence_ids']}
        structured=[s for s in ex['segments'] if s['evidence_id'] in chosen and s.get('food_record')]
    else:
        for route,source in selected_sources(report['plan'],ex['segments']):
            trace={**route,'location':source['location'],'asset_id':source['segments'][0]['asset_id'],'evidence_ids':[s['evidence_id'] for s in source['segments']]}
            cached=report.get('tool_results',{}).get(route['source_id'])
            before_groups=len(groups);before_manual=len(manual)
            if not cached:
                report['active_tool']={**route,'started_at':now()}
                progress(state['run_id'],'Agent가 '+route['source_id']+' 자료의 처리 도구를 실행하는 중')
                with tx() as c:save_report(c,report,state)
            if cached:
                groups.extend(restore_groups(cached['groups'],ex['segments'],[cached['trace']]));manual.extend(cached['manual']);trace=cached['trace']
                if route['tool']=='normalize_table':structured.extend(s for s in source['segments'] if s.get('food_record'))
            elif route['tool']=='normalize_table':
                # The table tool registers the original workbook as an artifact;
                # it never interprets every row through the LLM.
                with tx() as c:
                    asset=get(c,'asset',source['segments'][0]['asset_id'])
                    if asset['filename'].lower().endswith('.xlsx'):
                        from backend.app.domains.pricing.workbooks import register
                        table=register(c,state['revision_id'],asset['id'])
                        trace['registered_table_id']=table['id']
                structured.extend(s for s in source['segments'] if s.get('food_record'))
                leftovers=[s for s in source['segments'] if not s.get('food_record') and not s.get('structured_table_header') and re.sub(r'[|:\s-]+','',s['text'])]
                # Choosing a table tool cannot silently discard prose or unknown rows.
                if leftovers:manual.extend(s['evidence_id'] for s in leftovers)
            elif route['tool']=='extract_text':groups.extend(batches(source['segments']))
            elif route['tool']=='extract_image_regions':
                try:
                    loc=source['location'];matches=[]
                    if loc.get('embedded_image') and loc.get('row_start'):
                        for row in ex['segments']:
                            cell=row['locator'].get('cell_range','');number=re.search(r'\d+',cell)
                            if row.get('food_record') and row['asset_id']==trace['asset_id'] and row['locator'].get('sheet_name')==loc.get('sheet_name') and number and loc['row_start']<=int(number[0])<=loc['row_end']:matches.append(row)
                    if len(matches)==1:
                        label='엑셀 행 '+matches[0]['locator']['cell_range']
                        region_groups=[[{**matches[0],'region_label':label,'table_context':True,'source_role':'product'}]+[{**s,'region_label':label,'source_role':'product'} for s in source['segments']]]
                        unassigned=[];layout={'method':'explicit_spreadsheet_anchor','table_evidence_id':matches[0]['evidence_id']}
                    elif loc.get('embedded_image') and any(s.get('food_record') and s['asset_id']==trace['asset_id'] for s in ex['segments']):
                        region_groups=[];unassigned=trace['evidence_ids'];layout={'method':'ambiguous_spreadsheet_anchor'}
                        trace['review_required']={'code':'XLSX_IMAGE_ROW_AMBIGUOUS','message':'삽입 이미지에 연결할 상품 행이 하나로 정해지지 않아 원문 확인이 필요합니다.'}
                        report['warnings'].append(f"{route['source_id']}: "+trace['review_required']['message'])
                    else:region_groups,unassigned,layout=await image_regions(source,call)
                    groups.extend(region_groups);manual.extend(unassigned);trace['layout']=layout
                except Problem as error:
                    if error.code not in ('IMAGE_LAYOUT_BUDGET','IMAGE_REGION_BUDGET','MODEL_INPUT_BUDGET','IMAGE_REGION_SOURCE','IMAGE_REGION_COVERAGE','MODEL_SCHEMA_INVALID','MODEL_OUTPUT_LIMIT'):raise
                    # A source too large for bounded inference stays available for
                    # manual review; it must not discard all other source results.
                    report['model_calls'].extend(model.calls);model.calls=[]
                    manual.extend(trace['evidence_ids'])
                    trace['review_required']={'code':error.code,'message':error.message}
                    report['warnings'].append(f"{route['source_id']}: {error.message}")
            else:manual.extend(s['evidence_id'] for s in source['segments'])
            if not cached:trace.update(started_at=report['active_tool']['started_at'],prepared_at=now(),status='review_required' if trace.get('review_required') else 'prepared')
            report.pop('active_tool',None)
            execution.append(trace)
            report.setdefault('tool_results',{})[route['source_id']]={'trace':trace,'groups':group_references(groups[before_groups:]),'manual':manual[before_manual:]}
            report['model_calls'].extend(model.calls);model.calls=[]
            with tx() as c:save_report(c,report,state)
        report['tool_executions']=execution;report['manual_evidence_ids']=list(dict.fromkeys(manual))
        report['execution_groups']=group_references(groups)
        report['spatial_version']='ocr-spatial-v1'
        report['model_calls'].extend(model.calls);model.calls=[]
        if manual:report['warnings'].append(f'자동 처리하지 못해 원문 확인이 필요한 구간 {len(set(manual))}개')
        with tx() as c:save_report(c,report,state)
    budget=128
    if report.get('processing_version')!='food-record-v2':
        if report['batches_completed']:
            report.setdefault('prior_processing_events',[]).extend(report['events']);report['events']=[];report['batches_completed']=0;report['coverage']['processed_segments']=0
        report['processing_version']='food-record-v2'
        with tx() as c:save_report(c,report,state)
    if len(groups)>budget:raise Problem(422,'MODEL_RUN_BUDGET','자료가 한 실행의 AI 호출 상한을 넘습니다. 문서 분할이 필요합니다.')
    if report.get('structured_version')!=CONSOLIDATION_VERSION:
        report['events'].extend(table_event(segment) for segment in structured)
        report['structured_processed']=True;report['structured_version']=CONSOLIDATION_VERSION
        report['coverage']['structured_rows']=len(structured)
        with tx() as c:save_report(c,report,state)
    report['coverage']['total_batches']=len(groups)
    with tx() as c:save_report(c,report,state)
    for i,segments in enumerate(groups):
        if i<report['batches_completed']:continue
        boundary()
        progress(state['run_id'],f'AI 정보 추출 {i+1}/{len(groups)} · 품목·단가·공급 변경 해석')
        mapping=model_mapping(segments)
        # A small source-context prefix supplies dates/header labels that span rows/batches.
        context=[]
        payload=extraction_payload(r,report['plan']['document_type'],mapping)
        table_context=next((s for s in segments if s.get('table_context')),None)
        schema=event_schema(list(mapping),spatial=any(s.get('region_label') for s in mapping.values()))
        if table_context:
            payload={'title':r['title'],'segments':payload['segments'],'coordinates':payload['coordinates'],'location':payload['location'],'instructions':'field_evidence에 원재료·알레르기의 근거 문장 ID를 각각 반환하라. 이 이미지는 함께 제공한 엑셀 행 상품의 라벨이다. 해당 상품의 원재료·함량·알레르기·원산지 속성만 보완하라. ingredients_text는 원재료 목록 원문만 넣고 함량이 없어도 빠짐없이 보존하라. 보관방법·업체 주소는 원재료가 아니다. attributes_text와 allergen_text는 해당 원문 그대로이며 없으면 null이다. 상품·규격·가격은 추출하지 마라. source_ids는 제공된 ID만 사용하라.'}
            from backend.app.domains.analysis.schemas import label_schema
            schema=label_schema(list(mapping))
        try:
            task='한 상품 라벨의 원재료·함량·원산지와 알레르기 표시 원문만 반환하라. 상품·규격·단가는 추출하지 마라.' if table_context else '추출 자료를 해석해 실제 식품별 사실을 JSON events로 반환하라. 단순 회사명·연락처·안내 제목은 품목이 아니다.'
            data=await model_call(model,task,payload,schema,state)
            if table_context:
                from backend.app.domains.analysis.schemas import EVENT_FIELDS
                data={'events':[{**{key:None for key in EVENT_FIELDS},**data,'kind':'food_profile','product_name':table_context['food_record']['food_name'],'replacements':[],'uncertainties':[]}]}
            if len(data['events'])>=24:raise Problem(422,'EVENT_WINDOW_CAPACITY','AI 추출 항목 상한에 도달했습니다. 누락 방지를 위해 더 작은 구간으로 재처리해야 합니다.')
        except Problem as error:
            if error.code not in ('MODEL_SCHEMA_INVALID','MODEL_OUTPUT_LIMIT','EVENT_WINDOW_CAPACITY','MODEL_INPUT_BUDGET'):raise
            report['model_calls'].extend(model.calls);model.calls=[]
            failure={'batch':i+1,'code':error.code,'evidence_ids':list(dict.fromkeys(s['evidence_id'] for s in segments))}
            if isinstance(error.details,dict) and error.details.get('validation'):failure['validation']=error.details['validation']
            if len(segments)>1 and not any(s.get('region_label') for s in segments) and len(groups)+2<=budget:
                middle=len(segments)//2
                groups[i]=[];groups.extend([segments[:middle],segments[middle:]])
                report['warnings'].append('AI 출력 형식·예산 오류 구간을 원본 행 경계로 나누어 재처리했습니다: '+error.code)
                failure['resolution']='split'
            else:
                report['manual_evidence_ids']=list(dict.fromkeys(report.get('manual_evidence_ids',[])+[s['evidence_id'] for s in segments]))
                report['warnings'].append('자동 추출 형식·예산 오류 원문은 검토 대상으로 보존했습니다: '+error.code)
                failure['resolution']='manual_review'
                groups[i]=[]
            report.setdefault('extraction_failures',[]).append(failure)
            report['execution_groups']=group_references(groups)
            report['batches_completed']=i+1;report['coverage']['total_batches']=len(groups)
            with tx() as c:save_report(c,report,state)
            continue
        report['verification_calls_skipped']=report.get('verification_calls_skipped',0)+1
        for event in data['events']:
            for key,value in event.items():
                if isinstance(value,str) and value.strip().lower() in ('null','none'):event[key]=None
            event['replacements']=[value for value in event.get('replacements',[]) if value.strip().lower() not in ('null','none')]
            for extra in ('company_name','food_code','attributes_text','allergen_text'):event.setdefault(extra,None)
            from backend.app.domains.analysis.spatial import ground_fields
            field_manual=ground_fields(event,mapping)
            if field_manual:
                report['manual_evidence_ids']=list(dict.fromkeys(report.get('manual_evidence_ids',[])+field_manual))
                report.setdefault('extraction_failures',[]).append({'batch':i+1,'code':'IMAGE_FIELD_EVIDENCE','evidence_ids':field_manual,'resolution':'manual_review'})
                report['warnings'].append('상품 소속 또는 필드 근거가 불명확한 값은 원문 검수로 남겼습니다.')
            event['id']=uid();event['evidence_ids']=list(dict.fromkeys(eid for k in event.pop('source_ids') for eid in [mapping[k]['evidence_id'],*mapping[k].get('related_evidence_ids',[])]));event.setdefault('validation_warnings',[])
            if any(s.get('region_label') for s in mapping.values()):
                event['evidence_ids']=list(dict.fromkeys(s['evidence_id'] for s in mapping.values()))
            quote=' '.join(mapping[k]['text'] for k in mapping if mapping[k]['evidence_id'] in event['evidence_ids'])
            for field in ('food_code','attributes_text','allergen_text','ingredients_text'):
                if event.get(field) and canonical(event[field]) not in canonical(quote):event[field]=None;event['validation_warnings'].append('원문에서 재확인할 수 없는 '+field+' 값을 제외했습니다.')
            if event.get('food_code') and not re.fullmatch(r'\d{10}',event['food_code']):
                event['food_code']=None;event['validation_warnings'].append('공통식품코드는 10자리 원문 코드를 확인해야 합니다.')
            if event.get('company_name') and canonical(event['company_name']) not in canonical(quote):event['company_name']=None;event['validation_warnings'].append('원문에서 확인할 수 없는 업체명을 제외했습니다.')
            if event['amount'] is not None:
                try:
                    amount=Decimal(event['amount'].replace(',','').replace('원','').strip());assert amount.is_finite() and 0<=amount<Decimal('10000000000000000') and amount.as_tuple().exponent>=-4
                    event['amount']=format(amount,'f')
                    normalized=re.sub(r'[,\s]','',quote)
                    if event['amount'] not in normalized:event['amount']=None;event['validation_warnings'].append('원문 인용에서 찾을 수 없는 금액을 제외했습니다.')
                except (InvalidOperation,ValueError,AssertionError):event['amount']=None;event['validation_warnings'].append('금액이 유효한 10진수가 아닙니다.')
            for key in ('effective_from','effective_to'):
                if event[key]:
                    try:date.fromisoformat(event[key])
                    except ValueError:event[key]=None;event['validation_warnings'].append('적용일 형식 확인 필요')
            if event['kind']!='price':event.update(amount=None,quantity=None,unit=None)
            # Host checks dimensional consistency; never publish 500g pack price as 1g.
            if event['kind']=='price' and event['spec']:
                measure=re.fullmatch(r'\s*(\d+(?:\.\d+)?)\s*(kg|g|ml|l|개|ea)\s*',event['spec'],re.I)
                if measure:
                    quantity,unit=measure.groups();unit='ea' if unit=='개' else unit.lower()
                    if event['quantity']!=quantity or event['unit']!=unit:
                        event['quantity']=quantity;event['unit']=unit;event['validation_warnings'].append('판매 규격과 가격 기준 수량을 일치시켰습니다. 원문과 확인하세요.')
            # Attach verbatim supporting date/reason blocks, even when model omitted them.
            for field in ('reason','effective_from','effective_to'):
                value=event.get(field)
                if not value:continue
                hits=[]
                for source in (mapping.values() if any(s.get('region_label') for s in mapping.values()) else ex['segments']):
                    if field=='reason':matched=value in source['text']
                    else:
                        y,m,d=value.split('-');matched=bool(re.search(rf'{y}\s*[-./년]\s*0?{int(m)}\s*[-./월]\s*0?{int(d)}(?:일|\b)',source['text']))
                    if matched:hits.append(source['evidence_id'])
                if hits:event['evidence_ids']=list(dict.fromkeys(event['evidence_ids']+hits[:4]))
                else:
                    if field.startswith('effective'):event[field]=None
                    event['validation_warnings'].append(('적용일' if field.startswith('effective') else '사유')+'을 원문에서 재확인해야 합니다.')
            if event['kind']=='discontinued' and not re.search(r'단종|(?:생산|제조)\s*(?:종료|중단)',quote):
                event['excluded_reason']='제조 단종의 명시적 근거가 없어 DB 변경안에서 제외했습니다.'
                event['validation_warnings'].append(event['excluded_reason'])
            if event['kind']=='supply_ended' and not re.search(r'(?:공급|취급|납품)\s*종료',quote):
                event['excluded_reason']='공급 종료의 명시적 근거가 없어 DB 변경안에서 제외했습니다.'
                event['validation_warnings'].append(event['excluded_reason'])
            if event['kind']=='price' and event['amount'] is None:
                event['excluded_reason']='가격 근거를 확인할 수 없어 단가 변경안에서 제외했습니다.'
            # Keep distinct specs/periods and both baseline/correction evidence.
            if table_context:
                from backend.app.domains.catalog.record import from_event
                from backend.app.domains.catalog.record import ingredient_section
                if not event.get('ingredients_text') and 'ingredients' not in event.get('extracted_field_sources',{}):
                    product_quote='\n'.join(s['text'] for s in mapping.values() if s.get('source_role')!='context')
                    event['ingredients_text']=ingredient_section(product_quote)
                    if event['ingredients_text']:
                        recovered={'ingredients_text':event['ingredients_text']}
                        ground_fields(recovered,mapping)
                        origin=recovered.get('extracted_field_sources',{}).get('ingredients')
                        if origin:
                            origin['origin']='ocr_parser'
                            event.setdefault('extracted_field_sources',{})['ingredients']=origin
                supplement=from_event(event);base=table_context['food_record']
                def fill_missing(primary,extra):
                    if isinstance(primary,dict):
                        other=extra if isinstance(extra,dict) else {}
                        return {k:fill_missing(v,other.get(k)) for k,v in primary.items()}
                    return extra if primary is None or primary=='' or primary==[] else primary
                combined=fill_missing(base,supplement)
                if not base['allergens'].get('original_text') and supplement['allergens'].get('original_text'):combined['allergens']=supplement['allergens']
                for field in ('attributes','allergens'):
                    if combined[field]!=base[field]:combined['field_sources'][field]=supplement['field_sources'].get(field) or {'evidence_ids':event['evidence_ids'],'origin':'ocr_llm'}
                if combined['attributes']['ingredients']!=base['attributes']['ingredients']:
                    combined['field_sources']['ingredients']=supplement['field_sources'].get('ingredients') or {'evidence_ids':event['evidence_ids'],'raw_value':event.get('ingredients_text') or event.get('attributes_text'),'origin':'ocr_llm'}
                event.update(product_name=base['food_name'],company_name=base.get('company_name'),spec=base['specification']['original_text'],food_record=combined)
            report['events'].append(event)
        report['model_calls'].extend(model.calls);model.calls=[];report['batches_completed']=i+1;report['coverage']['processed_windows']=sum(len(g) for g in groups[:i+1]);report['coverage']['total_windows']=sum(len(g) for g in groups);report['coverage']['completed_batches']=i+1;report['coverage']['processed_segments']=len(ex['segments']) if i+1==len(groups) else min(len(ex['segments']),len(structured)+len({s['evidence_id'] for group in groups[:i+1] for s in group}))
        with tx() as c:save_report(c,report,state)
    before=len(report['events'])
    report['events'],merged=consolidate(report['events'])
    report.setdefault('merged_events',[]).extend(merged)
    report['consolidation']={'version':CONSOLIDATION_VERSION,'input_events':before,'review_items':len(report['events']),'merged_or_excluded':len(merged)}
    report['coverage']['manual_segments']=len(report.get('manual_evidence_ids',[]))
    report['coverage']['processed_segments']=len(ex['segments'])-report['coverage']['manual_segments']
    report['status']='matching'
    with tx() as c:save_report(c,report,state)
    return {'agent_report_id':report['id']}

def canonical(text):return re.sub(r'\W+','',text or '').casefold()
