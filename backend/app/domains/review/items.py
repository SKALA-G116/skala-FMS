"""Versioned, field-editable FoodChangeDTO review. No model calls during review."""
from copy import deepcopy
import re
from datetime import date
from decimal import Decimal
from decimal import InvalidOperation
from jsonschema import Draft202012Validator
from jsonschema import FormatChecker
from backend.app.infrastructure.database import Problem
from backend.app.infrastructure.database import entity
from backend.app.infrastructure.database import get
from backend.app.infrastructure.database import now
from backend.app.infrastructure.database import put
from backend.app.infrastructure.database import uid
from backend.app.domains.review.proposals import bump
from backend.app.domains.review.proposals import validate
from backend.app.domains.review.proposals import revision
from backend.app.domains.analysis.schemas import EVENT_FIELDS
from backend.app.domains.catalog.record import record_schema
from backend.app.domains.catalog.record import validate_record
from backend.app.domains.catalog.record import from_event
from backend.app.domains.catalog.record import specification

FIELDS=['kind','product_name','spec','amount','quantity','unit','effective_from','effective_to','reason','replacements','price_basis','food_record']

FIELD_SCHEMA={k:EVENT_FIELDS[k] for k in FIELDS if k!='food_record'}

FIELD_SCHEMA['food_record']=record_schema()

FIELD_SCHEMA.update(supplier_id={'type':['string','null'],'format':'uuid'},product_id={'type':['string','null'],'format':'uuid'})

for field,schema in FIELD_SCHEMA.items():
    if 'string' in schema.get('type',[]):schema={**schema,'maxLength':2000};FIELD_SCHEMA[field]=schema

INPUT_SCHEMA={'type':'object','additionalProperties':False,'required':['version','status','fields','reason'],'properties':{'version':{'type':'integer','minimum':1},'status':{'enum':['pending','confirmed','skipped']},'fields':{'type':'object','additionalProperties':False,'properties':FIELD_SCHEMA},'reason':{'type':'string','minLength':1,'maxLength':1000}}}

def current(c,runid,version):
    run=get(c,'analysis_run',runid,True)
    if not run.get('agent_report_id'):raise Problem(409,'NOT_READY','AI 추출이 끝난 뒤 검토할 수 있습니다.')
    report=get(c,'agent_report',run['agent_report_id'],True)
    if report['status']!='completed':raise Problem(409,'NOT_READY','AI 추출이 아직 진행 중입니다.')
    if version!=report.get('version',1):raise Problem(409,'REVIEW_CHANGED','다른 검토 내용이 저장되었습니다. 다시 불러오세요.')
    for pid in report['proposal_ids']:
        if get(c,'proposal',pid,True)['summary']['status'] in ('approved','applying','applied','apply_failed'):
            raise Problem(409,'REVIEW_LOCKED','승인·반영된 결과는 수정할 수 없습니다. 새 분석을 시작하세요.')
    return run,report

def validate_fields(c,event,status):
    if status!='confirmed':return
    if event.get('food_record'):validate_record(event['food_record'])
    if event['kind'] in ('food_profile','new_product'):
        if not event.get('food_record',{}).get('food_name'):raise Problem(422,'REVIEW_FIELDS','식품명을 확인해 주세요.')
        return
    if not event.get('product_name') or not event.get('spec'):raise Problem(422,'REVIEW_FIELDS','식품명과 규격을 확인해 주세요.')
    if not event.get('effective_from'):raise Problem(422,'REVIEW_FIELDS','적용 시작일을 확인해 주세요.')
    try:
        start=date.fromisoformat(event['effective_from']);end=date.fromisoformat(event['effective_to']) if event.get('effective_to') else None
        if end and start>=end:raise ValueError()
    except ValueError:raise Problem(422,'REVIEW_FIELDS','적용일과 종료일을 확인해 주세요.')
    if event['kind']=='substitution':raise Problem(422,'SUBSTITUTION_REVIEW','대체품 구성 관계는 아직 이 화면에서 확정할 수 없습니다. 제외 후 별도 관계 검토를 진행하세요.')
    if not event.get('supplier_id'):raise Problem(422,'REVIEW_FIELDS','업체를 입력하거나 선택해 주세요.')
    get(c,'supplier',event['supplier_id'])
    if event.get('product_id'):
        p=entity(c,event['product_id']);row=c.execute('SELECT kind FROM catalog_entities WHERE id=%s',(p['id'],)).fetchone()
        if row['kind']!='product':raise Problem(422,'REVIEW_FIELDS','기존 식품 연결이 올바르지 않습니다.')
    if event['kind']=='price':
        try:
            amount=Decimal(event.get('amount') or 'NaN');quantity=Decimal(event.get('quantity') or 'NaN')
            if not amount.is_finite() or amount<0 or amount>=Decimal('1e16') or amount.as_tuple().exponent < -4 or not quantity.is_finite() or quantity<=0 or quantity.as_tuple().exponent < -4:raise InvalidOperation()
            if event.get('unit') not in ('g','kg','ml','l','ea','bag','box','pack'):raise InvalidOperation()
        except (InvalidOperation,ValueError):raise Problem(422,'REVIEW_FIELDS','단가·기준 수량·단위를 확인해 주세요.')

def save_item(c,runid,eventid,payload,actor):
    errors=list(Draft202012Validator(INPUT_SCHEMA,format_checker=FormatChecker()).iter_errors(payload))
    if errors:raise Problem(422,'REVIEW_INPUT','검토 입력 형식을 확인해 주세요.')
    run,report=current(c,runid,payload['version']);event=next((e for e in report['events'] if e['id']==eventid),None)
    if not event:raise Problem(404,'NOT_FOUND','추출 항목을 찾을 수 없습니다.')
    event.setdefault('food_record',from_event(event))
    values={**{k:event.get(k) for k in FIELDS},**payload['fields']}
    if 'food_record' in payload['fields']:
        record=values['food_record'];validate_record(record);values['product_name']=record['food_name'];values['spec']=record['specification']['original_text']
    else:
        values['food_record']=deepcopy(event['food_record'])
        if 'product_name' in payload['fields']:values['food_record']['food_name']=values['product_name']
        if 'spec' in payload['fields']:values['food_record']['specification']['original_text']=values['spec']
    record=values['food_record'];spec=record['specification']
    recomputed=specification(spec['original_text'],spec['quantity'],spec['unit'],spec['sales_unit'])
    for key in ('normalized_quantity','normalized_unit'):spec[key]=recomputed[key]
    def cleared(old,new,prefix=''):
        result=[]
        for key,value in old.items():
            path=prefix+'/'+key;replacement=new.get(key)
            if replacement is None and value is not None:result.append(path)
            elif isinstance(value,dict) and isinstance(replacement,dict):result.extend(cleared(value,replacement,path))
        return result
    clear_fields=cleared(event['food_record'],record)

    if values['kind']!='price':values.update(amount=None,quantity=None,unit=None)
    for key in ('amount','quantity'):
        if values.get(key):
            try:
                raw=values[key].replace(',','').strip()
                if not re.fullmatch(r'\d{1,16}(?:\.\d{1,4})?',raw):raise InvalidOperation()
                values[key]=format(Decimal(raw),'f')
            except InvalidOperation:raise Problem(422,'REVIEW_FIELDS','금액과 수량은 숫자로 입력하세요.')
    # The public DTO has one company; supplier_id remains a legacy command adapter.
    if 'food_record' in payload['fields']:
        company_id=record.get('company_id');company_name=(record.get('company_name') or '').strip()
        if company_id:
            company=get(c,'supplier',company_id)
            if company_name and company['name']!=company_name:raise Problem(422,'COMPANY_MISMATCH','선택한 업체와 업체명이 다릅니다.')
            record['company_name']=company['name']
        elif company_name and payload['status']=='confirmed':
            found=c.execute("SELECT data FROM app_records WHERE kind='supplier' AND data->>'name'=%s LIMIT 1",(company_name,)).fetchone()
            company=found['data'] if found else put(c,'supplier',{'id':uid(),'name':company_name,'roles':['supplier'],'aliases':[],'verification_status':'reviewed'})
            record['company_id']=company['id']
        values['supplier_id']=record.get('company_id')
    elif values.get('supplier_id'):
        company=get(c,'supplier',values['supplier_id']);record.update(company_id=company['id'],company_name=company['name'])
    validate_fields(c,values,payload['status'])
    # Row edits invalidate every derived approval draft; stale values cannot be approved.
    for pid in report['proposal_ids']:
        proposal=get(c,'proposal',pid,True);proposal['summary']['status']='superseded';bump(proposal);put(c,'proposal',proposal)
    report.setdefault('previous_proposal_ids',[]).extend(report['proposal_ids']);report['proposal_ids']=[];report['review_prepared']=False
    run['proposal_ids']=[];run['proposal_id']=None;put(c,'analysis_run',run)
    before=deepcopy(event.get('review'))
    event['review']={'status':payload['status'],'fields':values,'reason':payload['reason'],'actor_id':actor,'updated_at':now(),'cleared_profile_fields':clear_fields}
    put(c,'agent_item_review',{'id':uid(),'analysis_run_id':runid,'event_id':eventid,'before':before,'after':deepcopy(event['review']),'source_document_revision_id':run['document_revision_id'],'created_at':now()})
    report['version']=report.get('version',1)+1;report['dto_schema']='food-change-dto-v1';put(c,'agent_report',report)
    if report.get('export_asset_id'):report.setdefault('previous_export_asset_ids',[]).append(report['export_asset_id'])
    report['export_asset_id']=None;put(c,'agent_report',report)
    from backend.app.domains.analysis.export import export_review
    export_review({'run_id':runid,'revision_id':run['document_revision_id'],'agent_report_id':report['id'],'review_mode':True},connection=c)
    if run.get('job_id'):
        from backend.app.domains.jobs.service import getjob; from backend.app.domains.jobs.service import savejob
        job=getjob(c,run['job_id'],True);job['result']={**(job.get('result') or {}),'proposal_ids':[],'export_asset_id':get(c,'agent_report',report['id'])['export_asset_id']};savejob(c,job)
    return get(c,'agent_report',report['id'])

def prepare(c,runid,payload,actor):
    run,report=current(c,runid,payload.get('version'))
    selected=[e for e in report['events'] if e.get('review',{}).get('status')=='confirmed']
    if not selected:raise Problem(422,'NOTHING_CONFIRMED','원문과 대조한 항목을 먼저 확인해 주세요.')
    # Snapshot retains the original AI extraction, row decisions, and earlier exports.
    put(c,'agent_review_snapshot',{'id':uid(),'report_id':report['id'],'analysis_run_id':runid,'report':deepcopy(report),'actor_id':actor,'created_at':now()})
    for pid in report['proposal_ids']:
        p=get(c,'proposal',pid,True);p['summary']['status']='superseded';bump(p);put(c,'proposal',p)
    for event in selected:
        event.setdefault('ai_original',{k:deepcopy(event.get(k)) for k in FIELDS})
        validate_fields(c,event['review']['fields'],'confirmed')
        event.update({k:v for k,v in event['review']['fields'].items() if k in FIELDS})
        event.pop('excluded_reason',None)
    report['proposal_ids']=[]
    if report.get('export_asset_id'):report.setdefault('previous_export_asset_ids',[]).append(report['export_asset_id'])
    report['export_asset_id']=None;put(c,'agent_report',report)
    state={'run_id':runid,'revision_id':run['document_revision_id'],'agent_report_id':report['id'],'review_mode':True}
    from backend.app.domains.analysis.agent import resolve_and_stage
    from backend.app.domains.analysis.export import export_review
    result=resolve_and_stage(state,connection=c)
    report=get(c,'agent_report',report['id'],True)
    if any(not event.get('proposal_id') for event in report['events'] if event.get('review',{}).get('status')=='confirmed'):raise Problem(422,'MATCH_UNRESOLVED','확인한 품목을 DB에 연결하지 못했습니다. 기존 식품 연결을 직접 선택해 주세요.')
    for pid in result['proposal_ids']:
        p=get(c,'proposal',pid,True)
        report.setdefault('confirmed_proposals',{})[pid]={'revision':p['summary']['revision'],'reason':'품목별 원문 대조 완료','actor_id':actor,'created_at':now()}
    put(c,'agent_report',report)
    for pid in result['proposal_ids']:
        p=get(c,'proposal',pid);validate(c,p);revision(c,p,actor,'품목별 원문 대조·수정 반영');put(c,'proposal',p)
    exported=export_review(state,connection=c);report=get(c,'agent_report',report['id']);report['version']=report.get('version',1)+1;report['review_prepared']=True;put(c,'agent_report',report)
    if run.get('job_id'):
        from backend.app.domains.jobs.service import getjob; from backend.app.domains.jobs.service import savejob
        job=getjob(c,run['job_id'],True);job['result']={**(job.get('result') or {}),**result,**exported};savejob(c,job)
    return {'proposal_ids':result['proposal_ids'],**exported,'report_version':report['version']}
