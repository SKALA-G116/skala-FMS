"""LLM plans and interprets source facts; host resolves catalog and stages changes.
Evidence-bound facts and review artifacts remain available even for unresolved data.
"""
import json
import re
import asyncio
import functools
from contextvars import ContextVar
from backend.app.runtime.execution import boundary
from backend.app.runtime.execution import report_metrics
from contextlib import nullcontext
from decimal import Decimal
from decimal import InvalidOperation
from datetime import date
from backend.app.infrastructure.database import Problem
from backend.app.infrastructure.database import entities
from backend.app.infrastructure.database import get
from backend.app.infrastructure.database import now
from backend.app.infrastructure.database import put
from backend.app.infrastructure.database import tx
from backend.app.infrastructure.database import uid
from backend.app.domains.review.proposals import create
from backend.app.infrastructure.contracts import schema_check
from backend.app.domains.analysis.provider import LocalModel
from backend.app.domains.analysis.schemas import PLAN
from backend.app.domains.analysis.schemas import event_schema

_MODEL=ContextVar('food_model')

def managed_model(fn):
    @functools.wraps(fn)
    async def wrapped(state):
        model=LocalModel();token=_MODEL.set(model)
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

def needs_verification(events):
    # Baseline/profile descriptions do not assert a business change. Changes retain a second pass.
    return any(e.get('kind') not in ('food_profile','new_product') for e in events)

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
    payload={'title':r['title'],'published_at':r['published_at'],'files':[a['filename'][:60] for a in r['assets'][:5]],'preview':r['body_text'][:600],'first_segments':[s['text'][:160] for s in ex['segments'][:4]]}
    structured_only=any(s.get('food_record') for s in ex['segments']) and all(s.get('food_record') or s.get('structured_table_header') or re.fullmatch(r'[|:\s-]+',s['text']) for s in ex['segments'])
    result=({'document_type':'price_table','summary':'표의 열을 표준 식품 DTO에 맞춰 자동 정리했습니다. 조사 가격은 공급 단가로 확정하지 않습니다.','tasks':['match_catalog','create_review_excel']} if structured_only else await model_call(model,'이 자료가 전달하는 정보와 필요한 처리 작업을 분류하라.',payload,PLAN,state))
    result['tasks']=list(dict.fromkeys(result['tasks']))
    with tx() as c:
        report=put(c,'agent_report',{'id':uid(),'analysis_run_id':state['run_id'],'document_revision_id':r['id'],'model':model.name,'plan':result,'events':[],'model_calls':model.calls,'batches_completed':0,'proposal_ids':[],'export_asset_id':None,'status':'interpreting','created_at':now(),'coverage':{'source_segments':len(ex['segments']),'processed_segments':0},'warnings':[]})
        run=get(c,'analysis_run',state['run_id'],True);run['agent_report_id']=report['id'];put(c,'analysis_run',run)
    return {'agent_report_id':report['id']}

def compact_location(locator):
    result={k:v for k,v in locator.items() if k in ('kind','page_number','sheet_name','cell_range','block_id')}
    # Pixel coordinates remain in evidence; repeating them in every LLM input wastes tokens.
    return result

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
        for text in chunks or ['']:
            s={**original,'text':text};n=len(text.encode())+200
            if current and (size+n>byte_limit or (current[-1].get('asset_id'),current[-1]['locator'].get('page_number'))!=(s.get('asset_id'),s['locator'].get('page_number')) or len(current)>=(8 if s['locator']['kind']=='spreadsheet' else 60)):yield current;current=[];size=0
            current.append(s);size+=n
    if current:yield current

@managed_model
async def interpret(state):
    with tx() as c:
        report=get(c,'agent_report',state['agent_report_id']);r=get(c,'revision',state['revision_id']);ex=get(c,'extraction',state['extraction_id'])
    from backend.app.domains.catalog.record import upgrade_event
    model=_MODEL.get();structured=[s for s in ex['segments'] if s.get('food_record')]
    interpreted=[s for s in ex['segments'] if not s.get('food_record') and not s.get('structured_table_header')]
    if structured and all(s.get('food_record') or s.get('structured_table_header') or re.fullmatch(r'[|:\s-]+',s['text']) for s in ex['segments']):interpreted=[]
    groups=list(batches(interpreted));budget=128
    if report.get('processing_version')!='food-record-v2':
        if report['batches_completed']:
            report.setdefault('prior_processing_events',[]).extend(report['events']);report['events']=[];report['batches_completed']=0;report['coverage']['processed_segments']=0
        report['processing_version']='food-record-v2'
        with tx() as c:save_report(c,report,state)
    if len(groups)>budget:raise Problem(422,'MODEL_RUN_BUDGET','자료가 한 실행의 AI 호출 상한을 넘습니다. 문서 분할이 필요합니다.')
    if not report.get('structured_processed'):
        seen={}
        for segment in structured:
            record=segment['food_record'];signature=json.dumps({k:v for k,v in record.items() if k not in ('field_sources','issues')},sort_keys=True,ensure_ascii=False)
            if signature in seen:
                seen[signature]['evidence_ids'].append(segment['evidence_id'])
                for key,source in record['field_sources'].items():seen[signature]['food_record']['field_sources'].setdefault(key,{}).setdefault('additional_sources',[]).append(source)
                continue
            report['events'].append({'id':uid(),'kind':'food_profile','product_name':record['food_name'],'spec':record['specification']['original_text'],'amount':None,'quantity':None,'unit':None,'effective_from':None,'effective_to':None,'reason':None,'replacements':[],'price_basis':None,'uncertainties':[],'validation_warnings':record['issues'],'evidence_ids':[segment['evidence_id']],'food_record':record,'extraction_origin':'parser'})
            seen[signature]=report['events'][-1]
        report['structured_processed']=True;report['coverage']['structured_rows']=len(structured)
        with tx() as c:save_report(c,report,state)
    signatures={tuple(str(e.get(k)) for k in ('kind','product_name','spec','amount','effective_from','effective_to')) for e in report['events']}
    report['coverage']['total_batches']=len(groups)
    with tx() as c:save_report(c,report,state)
    for i,segments in enumerate(groups):
        if i<report['batches_completed']:continue
        boundary()
        progress(state['run_id'],f'AI 정보 추출 {i+1}/{len(groups)} · 품목·단가·공급 변경 해석')
        mapping={f'S{j+1}':s for j,s in enumerate(segments)}
        # A small source-context prefix supplies dates/header labels that span rows/batches.
        context=[{'id':f'C{j+1}','text':s['text'][:120]} for j,s in enumerate(ex['segments'][:4])]
        for j,s in enumerate(ex['segments'][:4]):mapping[f'C{j+1}']=s
        payload={'title':r['title'],'published_at':r['published_at'],'files':[a['filename'][:60] for a in r['assets'][:5]], 'document_type':report['plan']['document_type'],'source_context':context,'segments':[{'id':key,'text':s['text'],'location':compact_location(s['locator'])} for key,s in mapping.items() if key.startswith('S')], 'kind_definitions':{'price':'가격이 실제로 명시된 품목 단가','temporarily_unavailable':'일시품절·일시 공급중단','supply_ended':'공급처의 취급·납품 종료','discontinued':'제조사의 생산 단종(일시품절은 해당 안 됨)','available':'정상발주·공급 가능','substitution':'명시된 대체품 관계','new_product':'신제품 소개','food_profile':'가격·공급 변경 없이 식품명·속성·규격을 전달하는 기준정보'},'instructions':'모든 텍스트·OCR·표에서 식품 정보를 추출하라. 변경 공지가 아니어도 식품 정보가 있으면 kind=food_profile로 추출하라. company_name은 원문에 명시된 업체명이며 제조사·브랜드·판매사 구분 없이 하나로 추출한다. 없으면 null이다. food_code는 원문의 공통식품코드, attributes_text는 원산지·원재료·등급·용도 등 식품속성 원문, allergen_text는 함유/같은 제조시설/불포함 표시 원문이며 없으면 null이다. 이 구간에 나타난 실제 품목별 변경 사실/표의 가격 행을 추출하라. 원문에 명확하지 않은 필드는 null. 다른 가격 열은 price_basis에 이름을 밝혀라. OCR 조각은 같은 품목의 이름·규격·사유·시작일 근거를 함께 연결하라. source_ids는 제공된 ID만 사용. 공급 중단과 제조 단종을 구별하라. 적용일은 ISO YYYY-MM-DD, 명시되지 않으면 null. 단가는 원문의 판매 규격당 가격이며 자동으로 kg 가격으로 환산하지 말라. quantity는 규격 중 판매 기준의 실제 수량이다. 포장 무게를 수량 1로 잘못 바꾸지 마라. source_ids에는 품목·금액뿐 아니라 적용일과 사유가 나온 구간도 반드시 포함하라.'}
        data=await model_call(model,'추출 자료를 해석해 실제 식품별 사실을 JSON events로 반환하라. 단순 회사명·연락처·안내 제목은 품목이 아니다.',payload,event_schema(list(mapping)),state)
        if len(data['events'])>=24:raise Problem(422,'EVENT_WINDOW_CAPACITY','AI 추출 항목 상한에 도달했습니다. 누락 방지를 위해 더 작은 구간으로 재처리해야 합니다.')
        if report['plan']['document_type'] in ('notice','mixed') and data['events'] and needs_verification(data['events']):
            verified=await model_call(model,'독립적인 원문 대조 검증이다. 아래 초안의 오추출을 고치고 빠진 실제 변경만 보완하라. 일시품절은 temporarily_unavailable, 정상발주 가능은 available, 제조 단종만 discontinued. 원문에 없는 가격·적용일은 null. 초안이 원문보다 우선하지 않는다. 같은 표의 규격별 상태를 각각 구분하라.',{**{k:v for k,v in payload.items() if k not in ('instructions','kind_definitions','files')},'draft_events':data['events']},event_schema(list(mapping)),state)
            data=verified
        elif data['events'] and not needs_verification(data['events']):report['verification_calls_skipped']=report.get('verification_calls_skipped',0)+1
        if len(data['events'])>=24:raise Problem(422,'EVENT_WINDOW_CAPACITY','AI 검증 결과가 항목 상한에 도달해 누락 검사가 필요합니다.')
        for event in data['events']:
            for extra in ('company_name','food_code','attributes_text','allergen_text'):event.setdefault(extra,None)
            event['id']=uid();event['evidence_ids']=list(dict.fromkeys(mapping[k]['evidence_id'] for k in event.pop('source_ids')));event['validation_warnings']=[]
            quote=' '.join(mapping[k]['text'] for k in mapping if mapping[k]['evidence_id'] in event['evidence_ids'])
            for field in ('food_code','attributes_text','allergen_text'):
                if event.get(field) and canonical(event[field]) not in canonical(quote):event[field]=None;event['validation_warnings'].append('원문에서 재확인할 수 없는 '+field+' 값을 제외했습니다.')
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
                for source in ex['segments']:
                    if field=='reason':matched=value in source['text']
                    else:
                        y,m,d=value.split('-');matched=bool(re.search(rf'{y}\s*[-./년]\s*0?{int(m)}\s*[-./월]\s*0?{int(d)}(?:일|\b)',source['text']))
                    if matched:hits.append(source['evidence_id'])
                if hits:event['evidence_ids']=list(dict.fromkeys(event['evidence_ids']+hits[:4]))
                else:event['validation_warnings'].append(('적용일' if field.startswith('effective') else '사유')+'을 원문에서 재확인해야 합니다.')
            if event['kind']=='discontinued' and not re.search(r'단종|(?:생산|제조)\s*(?:종료|중단)',quote):
                event['excluded_reason']='제조 단종의 명시적 근거가 없어 DB 변경안에서 제외했습니다.'
                event['validation_warnings'].append(event['excluded_reason'])
            if event['kind']=='price' and event['amount'] is None:
                event['excluded_reason']='가격 근거를 확인할 수 없어 단가 변경안에서 제외했습니다.'
            # Keep distinct specs/periods and both baseline/correction evidence.
            signature=tuple(str(event.get(k)) for k in ('kind','product_name','spec','amount','effective_from','effective_to'))
            if signature not in signatures:report['events'].append(event);signatures.add(signature)
        report['model_calls'].extend(model.calls);model.calls=[];report['batches_completed']=i+1;report['coverage']['processed_windows']=sum(len(g) for g in groups[:i+1]);report['coverage']['total_windows']=sum(len(g) for g in groups);report['coverage']['completed_batches']=i+1;report['coverage']['processed_segments']=len(ex['segments']) if i+1==len(groups) else min(len(ex['segments']),len(structured)+len({s['evidence_id'] for group in groups[:i+1] for s in group}))
        with tx() as c:save_report(c,report,state)
    # Broad prose and an attached detailed table often repeat the same notice.
    # Prefer a single explicitly identified spec; retain the broad evidence in provenance.
    remaining=[]
    for event in report['events']:
        specific=[other for other in report['events'] if other['spec'] and other['kind']==event['kind'] and canonical(other['product_name'])==canonical(event['product_name'])]
        if not event['spec'] and len(specific)==1:
            specific[0]['evidence_ids']=list(dict.fromkeys(specific[0]['evidence_ids']+event['evidence_ids']))
            event['merged_into_event_id']=specific[0]['id'];report.setdefault('merged_events',[]).append(event)
        else:remaining.append(event)
    report['events']=[upgrade_event(event) for event in remaining]
    report['coverage']['processed_segments']=len(ex['segments'])
    report['status']='matching'
    with tx() as c:save_report(c,report,state)
    return {'agent_report_id':report['id']}

def canonical(text):return re.sub(r'\W+','',text or '').casefold()

def resolve_and_stage(state,connection=None):
    if not state.get("review_mode"):progress(state['run_id'],'AI 추출 결과를 DB 품목·규격과 대조하고 변경안 만드는 중')
    with (nullcontext(connection) if connection is not None else tx()) as c:
        report=get(c,'agent_report',state['agent_report_id'],True);r=get(c,'revision',state['revision_id']);doc=get(c,'document',r['document_id'])
        if report['proposal_ids']:return {'proposal_ids':report['proposal_ids']}
        products=entities(c,'product');variants=entities(c,'variant');items=entities(c,'supplier_item')
        author=doc.get('author_display_name');supplier=None
        if author:
            found=c.execute("SELECT data FROM app_records WHERE kind='supplier' AND data->>'name'=%s LIMIT 1",(author,)).fetchone()
            supplier=found['data'] if found else put(c,'supplier',{'id':uid(),'name':author,'roles':['supplier'],'aliases':[],'verification_status':'publisher_candidate'})
        base_supplier=supplier
        bundles=[];pending=[];pending_events=[];local_products={};local_variants={};local_items={}
        def finish():
            nonlocal pending,pending_events,local_products,local_variants,local_items
            if not pending:return
            title=r['title']+f' · AI 변경안 {len(bundles)+1}'
            schema_check('ProposalCreate',{'title':title,'source_document_revision_ids':[r['id']],'changes':pending})
            p=create(c,title,[r['id']],pending,state['run_id']);bundles.append(p['summary']['id'])
            for event in pending_events:event['proposal_id']=p['summary']['id']
            pending=[];pending_events=[];local_products={};local_variants={};local_items={}
        for event in report['events']:
            item=None
            if state.get('review_mode') and event.get('review',{}).get('status')!='confirmed':event['proposal_id']=None;continue
            from backend.app.domains.catalog.record import from_event
            record=from_event(event);event['food_record']=record
            name=record['food_name'] or event['product_name'];event['product_name']=name
            event['review_reasons']=list(dict.fromkeys(event['uncertainties']+event['validation_warnings']));event['match_status']='unresolved';event['proposal_id']=None
            if event.get('excluded_reason'):event['review_reasons'].append(event['excluded_reason']);continue
            if not name:event['review_reasons'].append('원문의 품목을 특정할 수 없습니다.');continue
            if len(pending)>43:finish()
            if event.get('review',{}).get('fields',{}).get('supplier_id'):supplier=get(c,'supplier',event['review']['fields']['supplier_id'])
            elif record.get('company_id'):supplier=get(c,'supplier',record['company_id'])
            elif record.get('company_name'):
                found=c.execute("SELECT data FROM app_records WHERE kind='supplier' AND data->>'name'=%s LIMIT 1",(record['company_name'],)).fetchone();supplier=found['data'] if found else None
            else:supplier=base_supplier
            if supplier and not record.get('company_name'):record.update(company_id=supplier['id'],company_name=supplier['name'])
            selected_product=event.get('review',{}).get('fields',{}).get('product_id')
            exact=[p for p in products if p['id']==selected_product] if selected_product else ([p for p in products if p.get('common_food_code')==record['food_code']] if record.get('food_code') else [p for p in products if canonical(p['name'])==canonical(name) and p.get('record_type','commercial_product')=='commercial_product'])
            if len(exact)>1:event['review_reasons'].append('같은 이름의 제품이 여럿 있어 자동 연결을 보류했습니다.');continue
            ops=[];product=exact[0] if exact else None;pkey='common:'+record['food_code'] if record.get('food_code') else canonical(name)
            if product:pref={'id':product['id']};event['match_status']='exact_product';event['matched_product_id']=product['id']
            elif pkey in local_products:pref={'local_ref':local_products[pkey]}
            else:
                ref='p'+str(len(local_products));local_products[pkey]=ref;pref={'local_ref':ref};ops.append({'kind':'create_product','local_ref':ref,'name':name,'manufacturer_id':None,'brand_id':None,**({'record_type':'common_food','common_food_code':record['food_code']} if record.get('food_code') else {})});event['match_status']='new_product'
            spec=event['spec'] or '규격 미기재 · 검토 필요'
            if not event['spec']:event['review_reasons'].append('규격이 원문에 명확하지 않습니다.')
            normalized_spec=('common:'+record['food_code']+':'+canonical(spec)) if record.get('food_code') else spec
            vfound=[v for v in variants if product and v['product_id']==product['id'] and (v['spec_normalized']==normalized_spec or (not record.get('food_code') and canonical(v['spec_original'])==canonical(spec)))]
            vkey=(pkey,canonical(spec));variant=vfound[0] if len(vfound)==1 else None
            if variant:vref={'id':variant['id']}
            elif vkey in local_variants:vref={'local_ref':local_variants[vkey]}
            else:
                ref='v'+str(len(local_variants));local_variants[vkey]=ref;vref={'local_ref':ref};ops.append({'kind':'create_variant','local_ref':ref,'product_ref':pref,'spec_original':spec,'spec_normalized':normalized_spec,'barcode':None})
            ops.append({'kind':'set_food_profile','variant_ref':vref,'profile':record,'clear_fields':event.get('review',{}).get('cleared_profile_fields',[])})
            if event['kind'] in ('food_profile','new_product'):
                for op in ops:pending.append({'id':uid(),'operation':op,'field_evidence':[{'field_path':'/'+k,'evidence_ids':event['evidence_ids'],'origin':'reviewer' if state.get('review_mode') else 'extracted',**({'reviewer_justification':event['review']['reason']} if state.get('review_mode') else {})} for k in op if k not in ('kind','local_ref','supersedes_fact_id','manufacturer_id','brand_id','barcode','supplier_code')]})
                pending_events.append(event);continue
            if event['kind']=='discontinued':
                target_kind='set_product_status';target={'product_ref':pref};value={'status':'discontinued'}
            else:
                found=[x for x in items if variant and x['variant_id']==variant['id'] and (not supplier or x['supplier_id']==supplier['id'])]
                item=found[0] if len(found)==1 else None
                if item:iref={'id':item['id']};event['matched_supplier_item_id']=item['id'];event['match_status']='exact_supplier_item'
                elif supplier:
                    ikey=(vkey,supplier['id'])
                    if ikey in local_items:iref={'local_ref':local_items[ikey]}
                    else:
                        ref='i'+str(len(local_items));local_items[ikey]=ref;iref={'local_ref':ref};ops.append({'kind':'create_supplier_item','local_ref':ref,'variant_ref':vref,'supplier_id':supplier['id'],'supplier_code':None,'sales_unit':event['unit'] or event['spec'] or '규격 확인 필요'})
                    if supplier.get('verification_status')=='publisher_candidate':event['review_reasons'].append(f"게시자 ‘{author}’를 공급처 후보로 연결했습니다. 실제 공급처인지 확인하세요.")
                else:event['review_reasons'].append('실제 공급처를 확인할 수 없습니다.');iref=None
                if event['kind']=='price' and event['amount'] is not None and iref:
                    unit=event['unit'] or 'ea';quantity=event['quantity'] or '1'
                    try:
                        assert re.fullmatch(r'\d{1,16}(?:\.\d{1,4})?',quantity);q=Decimal(quantity);assert q.is_finite() and q>0;quantity=format(q,'f')
                    except Exception:quantity='1';event['review_reasons'].append('가격 기준 수량을 확인하세요.')
                    if event['unit'] is None:event['review_reasons'].append('가격 기준 단위 미기재: 임시로 1개 기준을 제안했습니다.')
                    target_kind='set_price';target={'supplier_item_ref':iref};value={'value':{'amount':event['amount'],'currency':'KRW','quantity':quantity,'unit':unit,'tax':'unknown','price_kind':'unknown','condition_key':'public'}}
                    if event.get('price_basis') and any(x in event['price_basis'] for x in ['조사','비교','참고']):event['review_reasons'].append('조사·참고 가격을 실제 공급 단가로 반영할지 확인하세요.')
                elif event['kind'] in ('temporarily_unavailable','supply_ended','available') and iref:target_kind='set_availability';target={'supplier_item_ref':iref};value={'status':event['kind']}
                else:
                    if event['kind']=='substitution':event['review_reasons'].append('대체품 후보의 조합·선택 관계를 확인해야 합니다.')
                    target_kind=None
            if event['effective_from']:start=event['effective_from']
            else:
                start=(r['published_at'] or r['collected_at'])[:10];event['review_reasons'].append(f'적용일 미기재: {start}을 검토용 임시 날짜로 제안했습니다.')
            if target_kind:
                op={'kind':target_kind,**target,**value,'period':{'effective_from':start,'effective_to':event['effective_to']},'reason':{'original_text':event['reason'],'summary':event['reason'],'code':None},'supersedes_fact_id':None}
                if item and event['kind']!='discontinued':
                    previous=c.execute("SELECT id FROM facts WHERE target_id=%s AND kind=%s AND condition_key=%s AND (effective_to IS NULL OR effective_to>%s::date)",(item['id'],target_kind,'public' if target_kind=='set_price' else '',start)).fetchall()
                    if len(previous)==1:op['supersedes_fact_id']=str(previous[0]['id']);event['review_reasons'].append('기존 사실의 적용 기간을 정정하는 변경안입니다.')
                ops.append(op)
            for op in ops:
                pending.append({'id':uid(),'operation':op,'field_evidence':[{'field_path':'/'+k,'evidence_ids':event['evidence_ids'],'origin':'reviewer' if state.get('review_mode') else 'extracted',**({'reviewer_justification':event['review']['reason']} if state.get('review_mode') else {})} for k in op if k not in ('kind','local_ref','supersedes_fact_id','manufacturer_id','brand_id','barcode','supplier_code')]})
            if ops:pending_events.append(event)
        finish();report['proposal_ids']=bundles;report['status']='exporting';put(c,'agent_report',report)
        # Revalidate now that confirmation reasons and proposal bindings are persisted.
        from backend.app.domains.review.proposals import validate
        for pid in bundles:
            p=get(c,'proposal',pid);validate(c,p);put(c,'proposal',p)
        run=get(c,'analysis_run',state['run_id'],True);run['proposal_id']=bundles[0] if bundles else None;run['proposal_ids']=bundles;put(c,'analysis_run',run)
        doc['analysis_status']='completed';doc['proposal_count']+=len(bundles);put(c,'document',doc)
    return {'proposal_ids':bundles}
