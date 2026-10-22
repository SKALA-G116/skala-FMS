"""
==============================================================================
FMS_FILE_SPEC
proposals.py - 변경안 검증과 승인 상태 전이
==============================================================================
설명:
    - 변경안 검증과 승인 상태 전이
입력·출력 명세:
    - 입력: 원문 revision·변경 연산·근거·현재 변경안
    - 출력: 확인 사항·허용 동작·버전·revision 이력
실행 가정:
    - 근거와 대상 관계·적용 기간을 확인한 뒤 허용된 전이만 수행
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

    2026-10-22  김재현(Finn) v0.1.0   다중 원문 근거 승인·검증 오류 표시·조회 재사용 개선

    2026-10-22  김재현(Finn) v0.1.0   25MB·표 삽입 이미지 근거 보완 및 검수 오류 개선

    상세 Git 이력: git log --follow -- backend/app/domains/review/proposals.py
    공통 규칙: doc/file-header-policy.md
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
from decimal import Decimal
from backend.app.infrastructure.database import Problem
from backend.app.infrastructure.database import entity
from backend.app.infrastructure.database import get
from backend.app.infrastructure.database import now
from backend.app.infrastructure.database import put
from backend.app.infrastructure.database import uid
from backend.app.infrastructure.contracts import SPEC
from backend.app.infrastructure.contracts import schema_check

def actions(p):
    s=p['summary']; status=s['status']
    s['allowed_actions']= {'draft':['edit','validate','hold','reject'],'ready':['edit','validate','approve','hold','reject'],'on_hold':['edit','validate'],'approved':['withdraw_approval','apply'],'conflict':['edit','validate'],'apply_failed':['apply']}.get(status,[])
    return p

def bump(p):
    p['summary']['version']+=1;p['summary']['updated_at']=now();return actions(p)

def validate(c,p):
    issues=[];targets={};locals={};diffs=[];evidence_cache={}
    def issue(message,change=None): issues.append({'code':'REVIEW_REQUIRED','severity':'blocking','message':message,'change_item_id':change})
    if p.get('analysis_run_id'):
        run=get(c,'analysis_run',p['analysis_run_id'])
        if run.get('agent_report_id'):
            report=get(c,'agent_report',run['agent_report_id']);confirmed=report.get('confirmed_proposals',{}).get(p['summary']['id'])
            if not confirmed or confirmed['revision']!=p['summary']['revision']:
                reasons=list(dict.fromkeys(reason for e in report['events'] if e.get('proposal_id')==p['summary']['id'] for reason in e.get('review_reasons',[])))
                for reason in reasons:issues.append({'code':'AI_CONFIRMATION_REQUIRED','severity':'blocking','message':reason,'change_item_id':None})
    for rid in p['source_document_revision_ids']:

        rev=get(c,'revision',rid)
        if rev.get('parse_issues'):issue('일부 첨부의 내용을 추출하지 못했습니다. 누락된 내용을 확인한 뒤 재분석하세요.')
        if get(c,'document',rev['document_id'])['attachment_status'] in ('incomplete','login_required'): issue('원문 이미지·첨부가 누락되었습니다. 원본 파일을 등록하고 다시 검토하세요.')
        if get(c,'document',rev['document_id'])['latest_revision_id']!=rid: issue('원문이 수정되었습니다. 새 원문으로 다시 분석하세요.')
    for ch in p['changes']:
        op=ch['operation'];cid=ch['id'];kind=op['kind']
        if 'local_ref' in op:
            if op['local_ref'] in locals: issue('묶음 내 참조 이름이 중복됩니다.',cid)
            locals[op['local_ref']]=kind.removeprefix('create_')
        for key,ref in op.items():
            if key.endswith('_ref') and isinstance(ref,dict):
                expected={'product_ref':'product','variant_ref':'variant','supplier_item_ref':'supplier_item','original_supplier_item_ref':'supplier_item'}.get(key)
                if 'local_ref' in ref:
                    if locals.get(ref['local_ref'])!=expected:issue('앞서 생성한 동일 종류의 참조가 필요합니다.',cid)
                else:
                    try:
                        e=entity(c,ref['id']);r=c.execute('SELECT kind FROM catalog_entities WHERE id=%s',(ref['id'],)).fetchone()
                        if r['kind']!=expected:issue('연결 대상 종류가 다릅니다.',cid)
                        targets[ref['id']]={'entity_type':r['kind'],'entity_id':ref['id'],'version':e['version']}
                    except Problem:issue('대상 상품을 찾을 수 없습니다.',cid)
        if kind in ('create_product','create_supplier_item'):
            for key in ('supplier_id','manufacturer_id','brand_id'):
                if op.get(key):
                    try:get(c,'supplier',op[key])
                    except Problem:issue('등록된 업체를 선택하세요.',cid)
        if 'period' in op:
            start,end=op['period']['effective_from'],op['period']['effective_to']
            if end and start>=end:issue('종료일은 시작일보다 뒤여야 합니다.',cid)
        if kind=='set_food_profile':
            from backend.app.domains.catalog.record import validate_record
            try:validate_record(op['profile'])
            except Problem as ex:issue(ex.message,cid)
        if kind=='set_price' and (Decimal(op['value']['quantity'])<=0 or op['value']['condition_key']!='public'):issue('수량은 0보다 커야 하며 공개 조건(public)만 지원합니다.',cid)
        if kind=='set_substitution':
            if op['mapping_status']!='confirmed' or not op['groups']:issue('대체품의 연결과 구성 관계를 확정하세요.',cid)
            for group in op['groups']:
                for member in group.get('members',[]):
                    ref=member.get('supplier_item_ref',{})
                    if Decimal(member['quantity'])<=0:issue('대체품 수량은 0보다 커야 합니다.',cid)
                    if 'local_ref' in ref and locals.get(ref['local_ref'])!='supplier_item':issue('대체품 참조가 올바르지 않습니다.',cid)
                    if 'id' in ref:
                        try: e=entity(c,ref['id']);targets[e['id']]={'entity_type':'supplier_item','entity_id':e['id'],'version':e['version']}
                        except Problem:issue('대체 상품을 찾을 수 없습니다.',cid)
        for fe in ch['field_evidence']:
            if fe['origin']=='reviewer' and not fe.get('reviewer_justification','').strip():issue('검토자 수정에는 사유가 필요합니다.',cid)
            try:
                value=op
                for part in fe['field_path'].strip('/').split('/'): value=value[int(part)] if isinstance(value,list) else value[part.replace('~1','/').replace('~0','~')]
            except (KeyError,IndexError,ValueError,TypeError):issue('근거의 필드 경로가 실제 변경 필드와 다릅니다.',cid)
            for eid in fe['evidence_ids']:
                try:
                    if eid not in evidence_cache:evidence_cache[eid]=get(c,'evidence',eid)
                    ev=evidence_cache[eid]
                    if ev['document_revision_id'] not in p['source_document_revision_ids']:issue('근거가 다른 원문에 속합니다.',cid)
                except Problem:issue('존재하지 않는 근거입니다.',cid)
        fields=set(op)-{'kind','local_ref','supersedes_fact_id','manufacturer_id','brand_id','barcode','supplier_code'}
        covered={fe['field_path'].split('/')[1] for fe in ch['field_evidence']}
        if fields-covered:issue('모든 핵심 필드에 근거를 연결하세요: '+', '.join(fields-covered),cid)
        if kind.startswith('set_'):
            ref=op.get('supplier_item_ref') or op.get('product_ref') or op.get('variant_ref') or op.get('original_supplier_item_ref')
            before=entity(c,ref['id']) if ref and 'id' in ref and ref['id'] in targets else None
            diffs.append({'change_item_id':cid,'field_path':'/','before':before,'after':op,'evidence_ids':list({e for f in ch['field_evidence'] for e in f['evidence_ids']})})
    p['issues']=issues;p['target_versions']=list(targets.values());p['diffs']=diffs
    p['summary']['blocking_count']=len(issues);p['summary']['change_count']=len(p['changes'])
    p['summary']['status']='draft' if issues else 'ready'
    return actions(p)

def revision(c,p,actor='system',reason='초안 생성'):
    put(c,'proposal_revision',{'id':uid(),'proposal_id':p['summary']['id'],'revision':p['summary']['revision'],'changes':p['changes'],'target_versions':p['target_versions'],'created_at':now(),'actor':actor,'reason':reason})

def create(c,title,rids,changes,run=None):
    p={'summary':{'id':uid(),'title':title,'status':'draft','version':1,'revision':1,'approved_revision':None,'change_count':len(changes),'blocking_count':0,'created_at':now(),'updated_at':now(),'source_document_ids':[get(c,'revision',r)['document_id'] for r in rids],'allowed_actions':[]},'source_document_revision_ids':rids,'changes':changes,'target_versions':[],'diffs':[],'issues':[],'decisions':[],'application_id':None,'duplicate_of_proposal_id':None,'analysis_run_id':run}
    validate(c,p);put(c,'proposal',p);revision(c,p);return p
