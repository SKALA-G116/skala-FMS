"""
==============================================================================
FMS_FILE_SPEC
test_workflow.py - 기능·경계·회귀 검증
==============================================================================
설명:
    - 기능·경계·회귀 검증
입력·출력 명세:
    - 입력: 테스트 fixture·가상 입력·명시적 mock/테스트 대역
    - 출력: assert 결과와 실패 사유
실행 가정:
    - DB 통합 테스트는 별도 _test DB·임시 assets 사용; 대역과 실제 모델 검증을 구분
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

    2026-10-21  미지정      v0.1.0   첨부 진행·취소와 완료 건수 회귀 검증 추가

    2026-10-21  미지정      v0.1.0   업체 표 직접 정규화·중복 통합·원문 이력 보존

    2026-10-21  미지정      v0.1.0   검수함을 내부 변경 묶음에서 자료별 분석 결과로 전환

    2026-10-21  미지정      v0.1.0   원본 속성 누락 복구·재정리 API·검토 동선 개선

    2026-10-21  김재현(Finn) v0.1.0   Agent 도구 선택 기반 리빌드·업무 경계 및 검증

    2026-10-22  김재현(Finn) v0.1.0   세션 복원·만료·로그아웃 경계와 접근 제어 검증

    2026-10-22  김재현(Finn) v0.1.0   이미지 예산 초과 자료 격리·나머지 결과 및 Excel 보존 검증

    2026-10-22  김재현(Finn) v0.1.0   자료·Agent·검수 승인·식품 DB 중심 흐름 및 알레르기 표기 정리

    상세 Git 이력: git log --follow -- backend/tests/test_workflow.py
    공통 규칙: doc/file-header-policy.md

기존 모듈 설명:
    Integration tests require a disposable PostgreSQL database ending in _test.
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

import os,uuid,copy
import pytest
from fastapi.testclient import TestClient
from backend.app.api.main import app
from backend.app.infrastructure.database import DSN, entity, get, init, now, put, records, tx, uid; from datetime import date; import json; import os; import uuid
from backend.app.seed import seed
from backend.app.domains.jobs.worker import once
from langgraph.checkpoint.postgres import PostgresSaver
from jsonschema import Draft202012Validator,FormatChecker
from backend.app.infrastructure.contracts import SPEC

@pytest.fixture(scope='module')
def client():
    assert DSN.rstrip('/').endswith('_test'),'Refusing to reset a non-test database'
    init()
    with tx() as c:
        c.execute('TRUNCATE app_records,catalog_entities,facts,sessions,command_keys,jobs,applications,record_archives,asset_cleanup,purged_source_posts CASCADE')
    seed()
    with PostgresSaver.from_conn_string(DSN) as cp:cp.setup()
    while once():pass
    with TestClient(app) as client:yield client

def login(c,username='admin'):
    csrf=c.get('/api/v1/auth/csrf').json()['csrf_token']
    r=c.post('/api/v1/auth/session',headers={'X-CSRF-Token':csrf},json={'username':username,'password':'local-food-2026'});assert r.status_code==200,r.text
    c.headers['X-CSRF-Token']=r.json()['csrf_token']
def post(c,path,body=None,etag=None,key=None):
    h={'Idempotency-Key':key or str(uuid.uuid4())}
    if etag:h['If-Match']=etag
    return c.post('/api/v1'+path,json=body or {},headers=h)
def proposal(c,code='DEMO-002',date='2026-11-01'):
    login(c)
    r=c.post('/api/v1/documents/import',headers={'Idempotency-Key':str(uuid.uuid4())},files={'file':('notice.txt',f'item {code} | 공급 일시중단 | {date} | 테스트 사유'.encode())},data={'title':'통합 테스트 공지'});assert r.status_code==201,r.text
    rid=r.json()['revision']['id'];j=post(c,'/analysis-runs',{'document_revision_id':rid,'workflow_profile':'notice'});assert j.status_code==202,j.text
    once();job=c.get('/api/v1/jobs/'+j.json()['id']).json();assert job['status']=='succeeded',job
    pid=job['result']['proposal_ids'][0];r=c.get('/api/v1/proposals/'+pid);return r.json(),r.headers['etag']
def approve(c,p,tag):
    r=post(c,'/proposals/'+p['summary']['id']+'/decisions',{'action':'approve','revision':p['summary']['revision']},tag);assert r.status_code==200,r.text
    return r.json(),r.headers['etag']
def apply(c,p,tag):
    r=post(c,'/proposals/'+p['summary']['id']+'/applications',{'approved_revision':p['summary']['approved_revision']},tag);assert r.status_code==202,r.text
    once();return c.get('/api/v1/jobs/'+r.json()['job']['id']).json()

def test_auth_roles_csrf(client):
    client.cookies.clear();client.headers.pop('X-CSRF-Token',None)
    assert client.get('/api/v1/products').status_code==401
    login(client,'reader');assert client.get('/api/v1/products').status_code==200
    assert post(client,'/analysis-runs',{}).status_code==403
    login(client);csrf=client.headers.pop('X-CSRF-Token');assert post(client,'/analysis-runs',{}).status_code==403;client.headers['X-CSRF-Token']=csrf

def test_approval_separation_temporal_history(client):
    p,tag=proposal(client)
    target=p['changes'][0]['operation']['supplier_item_ref']['id']
    with tx() as c:before=c.execute('SELECT count(*) n FROM facts WHERE target_id=%s',(target,)).fetchone()['n'];productid=entity(c,entity(c,target)['variant_id'])['product_id']
    p,tag=approve(client,p,tag)
    with tx() as c:assert c.execute('SELECT count(*) n FROM facts WHERE target_id=%s',(target,)).fetchone()['n']==before
    j=apply(client,p,tag);assert j['status']=='succeeded',j
    with tx() as c:
        from backend.app.domains.catalog.queries import active_facts
        assert active_facts(c,target,'set_availability','2026-10-31')==[]
        assert active_facts(c,target,'set_availability','2026-11-01')[0]['status']=='temporarily_unavailable'
    h=client.get('/api/v1/products/'+productid+'/history').json()['items'];assert any(x['kind']=='set_availability' and x['evidence_ids'] for x in h)

def test_idempotency_before_etag_and_immutable_approval(client):
    p,tag=proposal(client,'DEMO-003');path='/proposals/'+p['summary']['id']+'/decisions';key=str(uuid.uuid4());body={'action':'approve','revision':p['summary']['revision']}
    first=post(client,path,body,tag,key);second=post(client,path,body,tag,key);assert first.status_code==200;assert second.json()==first.json()
    assert post(client,path,{**body,'reason':'different'},tag,key).status_code==409
    r=client.patch('/api/v1/proposals/'+p['summary']['id'],headers={'Idempotency-Key':str(uuid.uuid4()),'If-Match':first.headers['etag']},json={'changes':p['changes'],'edit_reason':'changed'});assert r.status_code==409
    assert post(client,'/proposals/'+p['summary']['id']+'/withdraw-approval',{'reason':'재검토'},tag).status_code==412

def test_stale_target_rolls_back_entire_bundle(client):
    p,tag=proposal(client,'DEMO-001');p,tag=approve(client,p,tag)
    target=p['target_versions'][0]['entity_id']
    with tx() as c:
        before=c.execute('SELECT count(*) n FROM facts').fetchone()['n'];c.execute('UPDATE catalog_entities SET version=version+1 WHERE id=%s',(target,))
    j=apply(client,p,tag);assert j['status']=='failed';assert j['issues'][0]['code']=='TARGET_CHANGED'
    with tx() as c:assert c.execute('SELECT count(*) n FROM facts').fetchone()['n']==before
    assert client.get('/api/v1/proposals/'+p['summary']['id']).json()['summary']['status']=='conflict'

def test_partial_period_correction_and_atomic_rollback(client):
    p,tag=proposal(client,'DEMO-003','2027-01-01');p['changes'][0]['operation']['kind']='set_price'
    op=p['changes'][0]['operation'];op.pop('status');op['value']={'amount':'20000','currency':'KRW','quantity':'1','unit':'kg','tax':'unknown','price_kind':'regular','condition_key':'public'}
    op['period']['effective_to']='2027-02-01';target=op['supplier_item_ref']['id']
    with tx() as c:old=str(c.execute("SELECT id FROM facts WHERE target_id=%s AND kind='set_price'",(target,)).fetchone()['id'])
    op['supersedes_fact_id']=old
    eid=p['changes'][0]['field_evidence'][0]['evidence_ids'];p['changes'][0]['field_evidence']=[{'field_path':'/'+k,'evidence_ids':eid,'origin':'reviewer','reviewer_justification':'테스트용 수정'} for k in op if k not in ('kind','supersedes_fact_id')]
    r=client.patch('/api/v1/proposals/'+p['summary']['id'],headers={'Idempotency-Key':str(uuid.uuid4()),'If-Match':tag},json={'changes':p['changes'],'edit_reason':'부분 기간 가격 정정'});assert r.status_code==200,r.text
    p,tag=approve(client,r.json(),r.headers['etag']);assert apply(client,p,tag)['status']=='succeeded'
    with tx() as c:
        from backend.app.domains.catalog.queries import active_facts
        assert active_facts(c,target,'set_price','2026-12-31')[0]['value']['amount']=='18900'
        assert active_facts(c,target,'set_price','2027-01-15')[0]['value']['amount']=='20000'
        assert active_facts(c,target,'set_price','2027-02-01')[0]['value']['amount']=='18900'

def test_schema_and_invalid_evidence(client):
    p,tag=proposal(client,'DEMO-002','2028-01-01')
    validator=Draft202012Validator({'$ref':'#/components/schemas/Proposal','components':SPEC['components']},format_checker=FormatChecker());assert not list(validator.iter_errors(p))
    p['changes'][0]['field_evidence'][0]['evidence_ids']=[str(uuid.uuid4())]
    r=client.patch('/api/v1/proposals/'+p['summary']['id'],headers={'Idempotency-Key':str(uuid.uuid4()),'If-Match':tag},json={'changes':p['changes'],'edit_reason':'없는 근거 검사'});assert r.status_code==200;assert r.json()['summary']['status']=='draft'
    assert post(client,'/proposals/'+p['summary']['id']+'/decisions',{'action':'approve','revision':r.json()['summary']['revision']},r.headers['etag']).status_code==409

def test_new_product_bundle_and_duplicate_application(client):
    p,tag=proposal(client,'DEMO-002','2030-01-01');eid=p['changes'][0]['field_evidence'][0]['evidence_ids']
    supplier=client.get('/api/v1/suppliers').json()['items'][0]['id']
    ops=[{'kind':'create_product','local_ref':'p','name':'신규 묶음 테스트','manufacturer_id':None,'brand_id':None},{'kind':'create_variant','local_ref':'v','product_ref':{'local_ref':'p'},'spec_original':'1kg','spec_normalized':'1kg','barcode':None},{'kind':'create_supplier_item','local_ref':'i','variant_ref':{'local_ref':'v'},'supplier_id':supplier,'supplier_code':'TEST-NEW','sales_unit':'kg'},{'kind':'set_availability','supplier_item_ref':{'local_ref':'i'},'status':'available','period':{'effective_from':'2030-01-01','effective_to':None},'reason':{'original_text':None,'summary':None,'code':None},'supersedes_fact_id':None}]
    changes=[{'id':uid(),'operation':op,'field_evidence':[{'field_path':'/'+k,'evidence_ids':eid,'origin':'reviewer','reviewer_justification':'신규 묶음 통합 테스트'} for k in op if k not in ('kind','local_ref','manufacturer_id','brand_id','barcode','supplier_code','supersedes_fact_id')]} for op in ops]
    r=post(client,'/proposals',{'title':'신규 묶음','source_document_revision_ids':p['source_document_revision_ids'],'changes':changes});assert r.status_code==201,r.text
    p,tag=approve(client,r.json(),client.get('/api/v1/proposals/'+r.json()['summary']['id']).headers['etag'])
    a=post(client,'/proposals/'+p['summary']['id']+'/applications',{'approved_revision':p['summary']['approved_revision']},tag);assert a.status_code==202
    current=client.get('/api/v1/proposals/'+p['summary']['id']);b=post(client,'/proposals/'+p['summary']['id']+'/applications',{'approved_revision':p['summary']['approved_revision']},current.headers['etag']);assert b.json()['application']['id']==a.json()['application']['id']
    once();j=client.get('/api/v1/jobs/'+a.json()['job']['id']).json();assert j['status']=='succeeded',j
    assert len(client.get('/api/v1/products?q=신규%20묶음').json()['items'])==1

def test_conflicting_bundle_creates_nothing(client):
    p,tag=proposal(client,'DEMO-002','2026-11-01');eid=p['changes'][0]['field_evidence'][0]['evidence_ids'];op={'kind':'create_product','local_ref':'rollback','name':'롤백되어야 하는 상품','manufacturer_id':None,'brand_id':None}
    p['changes'].insert(0,{'id':uid(),'operation':op,'field_evidence':[{'field_path':'/name','evidence_ids':eid,'origin':'reviewer','reviewer_justification':'원자적 롤백 테스트'}]})
    r=client.patch('/api/v1/proposals/'+p['summary']['id'],headers={'Idempotency-Key':uid(),'If-Match':tag},json={'changes':p['changes'],'edit_reason':'원자성 확인'});assert r.status_code==200
    p,tag=approve(client,r.json(),r.headers['etag']);j=apply(client,p,tag);assert j['status']=='failed';assert j['issues'][0]['code']=='PERIOD_CONFLICT'
    assert client.get('/api/v1/products?q=롤백되어야').json()['items']==[]

def test_source_revision_changed_and_cancel(client):
    p,tag=proposal(client,'DEMO-002','2032-01-01');p,tag=approve(client,p,tag)
    with tx() as c:
        rev=get(c,'revision',p['source_document_revision_ids'][0]);doc=get(c,'document',rev['document_id']);newrev={**rev,'id':uid(),'revision_number':rev['revision_number']+1};put(c,'revision',newrev);doc['latest_revision_id']=newrev['id'];put(c,'document',doc)
    j=apply(client,p,tag);assert j['issues'][0]['code']=='SOURCE_CHANGED'
    rid=p['source_document_revision_ids'][0]
    j=post(client,'/analysis-runs',{'document_revision_id':rid}).json();r=post(client,'/jobs/'+j['id']+'/cancel');assert r.status_code==200
    assert client.get('/api/v1/jobs/'+j['id']).json()['status']=='cancelled'

def test_method_and_pagination_guard(client):
    login(client);assert client.get('/api/v1/proposals/'+uid()+'/decisions').status_code==405
    a=client.get('/api/v1/products?limit=1').json();assert len(a['items'])==1 and a['next_cursor']
    b=client.get('/api/v1/products?limit=1&cursor='+a['next_cursor']).json();assert a['items'][0]['id']!=b['items'][0]['id']
    assert client.get('/api/v1/products?cursor=bad').status_code==422

def test_signed_asset_access(client):
    login(client);doc=client.get('/api/v1/documents').json()['items'][0];rev=client.get('/api/v1/document-revisions/'+doc['latest_revision_id']).json();asset=rev['assets'][0]['id']
    assert client.get('/api/v1/assets/'+asset+'/content').status_code==403
    url=client.get('/api/v1/assets/'+asset+'/access').json()['url'];r=client.get(url);assert r.status_code==200 and r.content
    assert client.get(url.replace('sig=','sig=bad')).status_code==403

def test_status_and_substitution(client):
    p,tag=proposal(client,'DEMO-002','2035-01-01');ev=p['changes'][0]['field_evidence'][0]['evidence_ids'];items=client.get('/api/v1/supplier-items').json()['items'];target=items[0];other=items[1]
    with tx() as c:productid=entity(c,target['variant_id'])['product_id']
    period={'effective_from':'2035-01-01','effective_to':None};reason={'original_text':'테스트 공지','summary':'테스트 공지','code':None}
    ops=[{'kind':'set_product_status','product_ref':{'id':productid},'status':'discontinued','period':period,'reason':reason,'supersedes_fact_id':None},{'kind':'set_substitution','original_supplier_item_ref':{'id':target['id']},'mapping_status':'confirmed','groups':[{'selection':'one','members':[{'supplier_item_ref':{'id':other['id']},'quantity':'1','unit':'kg'}]}],'description_original':'다른 상품으로 대체','period':period,'reason':reason,'supersedes_fact_id':None}]
    changes=[{'id':uid(),'operation':op,'field_evidence':[{'field_path':'/'+k,'evidence_ids':ev,'origin':'reviewer','reviewer_justification':'제품 단종과 대체 연결 검토'} for k in op if k not in ('kind','supersedes_fact_id')]} for op in ops]
    r=post(client,'/proposals',{'title':'단종과 대체','source_document_revision_ids':p['source_document_revision_ids'],'changes':changes});assert r.status_code==201
    p,tag=approve(client,r.json(),client.get('/api/v1/proposals/'+r.json()['summary']['id']).headers['etag']);assert apply(client,p,tag)['status']=='succeeded'
    assert client.get('/api/v1/products/'+productid+'?as_of=2035-01-01').json()['status']=='discontinued'
    subs=client.get('/api/v1/supplier-items/'+target['id']+'/substitutions?as_of=2035-01-01').json()['items'];assert subs[0]['groups'][0]['members'][0]['supplier_item_ref']['id']==other['id']

@pytest.fixture
def workbook(client):
    import io,openpyxl
    login(client);wb=openpyxl.Workbook();s=wb.active;s.title='원본';s.append(['공통식품코드','공통식품명','조사가1','업체군',None]);s.append(['00123','두부',0,'농산물','없애기']);s.append(['00456','간장',18000,'공산품',None]);s.append(['00789','검은콩 두부',22000,'농산물','변경']);s.append(['00000','미입력',None,None,None]);s2=wb.create_sheet('메모');s2.append(['공통식품명','조사가1']);s2.append(['두부',14000]);s2.append(['재계산 필요','=1+2']);b=io.BytesIO();wb.save(b)
    r=client.post('/api/v1/price-workbooks/import',headers={'Idempotency-Key':uid()},files={'file':('prices.xlsx',b.getvalue())},data={'title':'원본 단가표 테스트'});assert r.status_code==201,r.text
    return r.json()

def test_workbook_values_and_provenance(client,workbook):
    assert [s['row_count'] for s in workbook['sheets']]==[4,2]
    s=workbook['sheets'][0];assert s['columns'][4]['label']=='제목 없는 열 (E)'
    data=client.get('/api/v1/price-sheets/'+s['id']+'/rows').json()
    assert data['items'][0]['cells']['A']=='00123';assert data['items'][0]['cells']['C']=='0';assert data['items'][0]['cells']['E']=='없애기'
    assert data['items'][0]['cell_range']=='A2:E2'
    assert 'C' not in data['items'][3]['cells']
    meta=client.get('/api/v1/price-workbooks/'+workbook['id']).json();assert meta['document_revision_id']==workbook['document_revision_id']
    other=client.get('/api/v1/price-sheets/'+workbook['sheets'][1]['id']+'/rows').json()['items'];assert other[0]['cells']['B']=='14000';assert '저장된 결과 없음' in other[1]['cells']['B']
    # Source browsing never creates authoritative business products.
    assert client.get('/api/v1/products?q=검은콩').json()['items']==[]

def test_workbook_compound_filters_numeric_sort_and_paging(client,workbook):
    s=workbook['sheets'][0]['id'];url='/api/v1/price-sheets/'+s+'/rows'
    import json
    fs=[{'column':'B','op':'contains','value':'두부'},{'column':'C','op':'gte','value':'1'}]
    r=client.get(url,params={'filters':json.dumps(fs)});assert r.status_code==200;assert r.json()['total']==1;assert r.json()['items'][0]['row_number']==4
    r=client.get(url,params={'filters':json.dumps([{'column':'C','op':'eq_number','value':'0'}])});assert r.json()['total']==1
    r=client.get(url,params={'filters':json.dumps([{'column':'C','op':'empty'}])});assert r.json()['total']==1;assert r.json()['items'][0]['cells']['B']=='미입력'
    a=client.get(url,params={'sort':'C','direction':'desc','limit':1}).json();b=client.get(url,params={'sort':'C','direction':'desc','limit':1,'offset':1}).json();assert a['items'][0]['cells']['C']=='22000';assert b['items'][0]['cells']['C']=='18000';assert a['has_more']
    assert client.get(url,params={'q':'18000'}).json()['total']==1
    assert client.get(url,params={'sort':"C');DROP TABLE facts;--"}).status_code==422
    assert client.get(url,params={'filters':json.dumps([{'column':'C','op':'gte','value':'NaN'}])}).status_code==422
    assert client.get(url,params={'filters':json.dumps([{'column':'B','op':'gte','value':'1'}])}).status_code==422
    assert client.get(url,params={'filters':json.dumps([{'column':'E','op':'contains','value':"%' OR TRUE --"}])}).json()['total']==0

def test_workbook_registration_replay_and_reader_permissions(client,workbook):
    key=uid();body={'document_revision_id':workbook['document_revision_id']}
    r=post(client,'/price-workbooks',body,key=key);again=post(client,'/price-workbooks',body,key=key);assert r.json()==again.json();assert r.json()['id']==workbook['id']
    login(client,'reader');assert client.get('/api/v1/price-workbooks').status_code==200;assert client.get('/api/v1/price-sheets/'+workbook['sheets'][0]['id']+'/rows').status_code==200
    assert post(client,'/price-workbooks',body).status_code==403
    login(client)

def test_table_mapping_full_approval_flow(client,workbook):
    login(client);supplier=post(client,'/suppliers',{'name':'실제 테스트 공급처'}).json()
    body={'supplier_id':supplier['id'],'name_column':'B','price_column':'C','unit_column':'D','spec_columns':['E'],'effective_from':'2038-01-01','tax':'unknown'}
    # Purpose-built table keeps commercial unit explicit and includes source memo text.
    import io,openpyxl
    w=openpyxl.Workbook();s=w.active;s.append(['코드','식품명','조사가','단위','규격']);s.append(['0001','테스트 두부','12000','봉','1kg']);s.append(['0002','테스트 간장','9000','병','500ml']);b=io.BytesIO();w.save(b)
    imported=client.post('/api/v1/price-workbooks/import',headers={'Idempotency-Key':uid()},files={'file':('mapping.xlsx',b.getvalue())}).json()
    r=post(client,'/price-sheets/'+imported['sheets'][0]['id']+'/proposals',body);assert r.status_code==201,r.text;assert r.json()['prepared_count']==2;assert len(r.json()['proposals'])==1
    pid=r.json()['proposals'][0]['id'];r=client.get('/api/v1/proposals/'+pid);assert r.json()['summary']['status']=='ready',r.text
    assert not client.get('/api/v1/products?q=테스트%20두부').json()['items']
    p,tag=approve(client,r.json(),r.headers['etag']);assert apply(client,p,tag)['status']=='succeeded'
    out=client.get('/api/v1/prices?as_of=2038-01-01&q=테스트').json()['items'];assert len(out)==2;assert {p['value']['amount'] for p in out}=={'12000','9000'}

def test_incremental_collection_and_revision_integrity(client):
    from backend.app.domains.ingestion.collection import collect_source
    login(client)
    with tx() as c:source=put(c,'source',{'id':uid(),'name':'수집 테스트','version':1})
    class Fake:
        def __init__(self,ids,edited=False):self.ids=ids;self.edited=edited
        def list_posts(self,board,page):return self.ids if page==1 else []
        def post(self,board,id):return {'url':f'https://school062.com/bbs/board.php?bo_table={board}&wr_id={id}','board':board,'post':id,'title':'제목','body':'수정' if self.edited and id=='100' else '원문','author':'업체','published_at':None,'assets':[],'issues':[]}
        def close(self):pass
    payload={'board_keys':['product_01'],'max_posts_per_board':5,'revisit_days':14,'auto_analyze':False}
    first=collect_source(source['id'],payload,site=Fake(['101','100']));assert first['counts']['new']==2
    again=collect_source(source['id'],payload,site=Fake(['101','100']));assert again['counts']['unchanged']==2
    with tx() as c:
        old=c.execute("SELECT data FROM app_records WHERE kind='document' AND data->>'source_id'=%s AND data->>'external_post_id'='100'",(source['id'],)).fetchone()['data']
    changed=collect_source(source['id'],payload,site=Fake(['102','101','100'],True));assert changed['counts']=={'new':1,'updated':1,'unchanged':1}
    with tx() as c:
        doc=get(c,'document',old['id']);assert doc['first_seen_at']==old['first_seen_at'];assert doc['latest_revision_id']!=old['latest_revision_id'];assert get(c,'revision',old['latest_revision_id'])['is_latest'] is False;assert get(c,'revision',doc['latest_revision_id'])['revision_number']==2
        assert c.execute('SELECT high_water FROM collection_cursors WHERE source_id=%s',(source['id'],)).fetchone()['high_water']==102

def test_source_credentials_encryption_and_roles(client):
    from backend.app.domains.ingestion.connections import config
    login(client);sid=client.get('/api/v1/sources').json()['items'][0]['id'];secret='not-a-real-account-password'
    r=post(client,'/sources/'+sid+'/connection',{'username':'test-source-user','password':secret,'auto_login':True});assert r.status_code==200,r.text;assert secret not in r.text;assert r.json()['password_stored']
    with tx() as c:
        encrypted=c.execute('SELECT encrypted_config FROM source_connections WHERE source_id=%s',(sid,)).fetchone()['encrypted_config'];assert secret not in encrypted;assert config(c,sid)['password']==secret
    login(client,'reader');assert client.get('/api/v1/sources/'+sid+'/connection').status_code==403
    assert post(client,'/sources/'+sid+'/connection',{'username':'test-source-user','password':secret}).status_code==403
    login(client)

def test_private_asset_recovery_is_new_revision(client):
    from backend.app.domains.ingestion.collection import ingest
    login(client)
    with tx() as c:
        source=put(c,'source',{'id':uid(),'name':'권한 복구 테스트','version':1})
        p={'url':'https://school062.com/bbs/board.php?bo_table=product_01&wr_id=999999','board':'product_01','post':'999999','title':'권한 확인','body':'같은 본문','author':None,'published_at':None,'assets':[],'issues':[{'code':'SOURCE_LOGIN_REQUIRED','url':'https://school062.com/bbs/download.php','message':'로그인 필요'}]}
        first,kind=ingest(c,source['id'],p);assert first['attachment_status']=='login_required';oldrid=first['latest_revision_id']
        p['issues']=[];p['assets']=[{'filename':'reference.txt','content':b'authorized data','source_url':'https://school062.com/bbs/download.php','content_type':'text/plain'}]
        second,kind=ingest(c,source['id'],p);assert second['id']==first['id'];assert kind=='updated';assert second['attachment_status']=='complete';assert second['latest_revision_id']!=oldrid
        assert len(get(c,'revision',second['latest_revision_id'])['assets'])==2

def test_scheduler_dedup_and_login_failure_pause(client):
    from backend.app.domains.ingestion.collection import schedule_tick
    from backend.app.domains.ingestion.connections import write
    with tx() as c:
        s=put(c,'source',{'id':uid(),'name':'스케줄 테스트','version':1,'enabled':True,'schedule_enabled':True,'poll_interval_minutes':30})
        write(c,s['id'],{'username':'dummy','password':'dummy','cookies':[]},'login_failed')
    schedule_tick()
    with tx() as c:assert not c.execute("SELECT 1 FROM jobs WHERE type='collect' AND payload->>'source_id'=%s",(s['id'],)).fetchone()
    with tx() as c:c.execute("UPDATE source_connections SET state='connected' WHERE source_id=%s",(s['id'],))
    schedule_tick();schedule_tick()
    with tx() as c:assert c.execute("SELECT count(*) n FROM jobs WHERE type='collect' AND payload->>'source_id'=%s",(s['id'],)).fetchone()['n']==1

def test_price_filters(client):
    login(client)
    r=client.get('/api/v1/prices?as_of=2038-01-01&supplier=실제%20테스트&amount_min=10000&amount_max=13000&unit=bag')
    assert r.status_code==200,r.text;assert len(r.json()['items'])==1;assert r.json()['items'][0]['value']['amount']=='12000'
    assert client.get('/api/v1/prices?amount_min=NaN').status_code==422

def test_worker_interrupt_requeues_own_lease(client,monkeypatch):
    from backend.app.domains.jobs.service import enqueue
    from backend.app.domains.jobs import worker as worker
    with tx() as c:
        rid=records(c,'revision')[0]['id'];run=put(c,'analysis_run',{'id':uid(),'document_revision_id':rid,'mode':'rules','status':'queued','workflow_profile':'auto','created_at':now()})
        job=enqueue(c,'analyze',{'document_revision_id':rid},run['id']);c.execute("UPDATE jobs SET created_at='1970-01-01' WHERE id=%s",(job['id'],))
    def interrupted(*args):raise KeyboardInterrupt()
    monkeypatch.setattr(worker,'run_analysis',interrupted)
    with pytest.raises(KeyboardInterrupt):worker.once()
    with tx() as c:
        row=c.execute('SELECT status,data,lease_until FROM jobs WHERE id=%s',(job['id'],)).fetchone();assert row['status']=='queued';assert row['data']['status']=='queued';assert row['lease_until'] is None

def test_nonfirst_header_detection_and_override(client):
    import io,openpyxl
    login(client);w=openpyxl.Workbook();s=w.active;s.append(['업체 단가표']);s.append(['문의 연락처']);s.append(['상품명','규격','단위','학교가']);s.append(['테스트 식품','1kg','봉',12000]);b=io.BytesIO();w.save(b)
    r=client.post('/api/v1/price-workbooks/import',headers={'Idempotency-Key':uid()},files={'file':('headers.xlsx',b.getvalue())});assert r.status_code==201,r.text
    sheet=r.json()['sheets'][0];assert sheet['header_row']==3;assert sheet['row_count']==1;assert sheet['columns'][0]['label']=='상품명';assert sheet['columns'][3]['numeric']
    rows=client.get('/api/v1/price-sheets/'+sheet['id']+'/rows').json();assert rows['items'][0]['row_number']==4;assert rows['total']==1
    changed=post(client,'/price-sheets/'+sheet['id']+'/header',{'header_row':1});assert changed.status_code==200;assert changed.json()['sheets'][0]['row_count']==3
    assert post(client,'/price-sheets/'+sheet['id']+'/header',{'header_row':99}).status_code==422


def test_agent_auto_extract_stage_excel_review_apply(client,monkeypatch):
    from test_agent import agent_pipeline
    agent_pipeline(client,monkeypatch)

def test_ai_unsupported_discontinuation_and_amount_are_excluded(client,monkeypatch):
    from test_agent import hallucination_guard
    hallucination_guard(client,monkeypatch)


def test_source_dto_review_edit_skip_and_apply(client,monkeypatch):
    from test_agent import editable_review_pipeline
    editable_review_pipeline(client,monkeypatch)


@pytest.mark.parametrize('input_format',['xlsx','txt'])
def test_structured_food_dto_review_and_catalog(client,monkeypatch,input_format):
    import io,openpyxl
    from test_food_record import milk
    from backend.app.domains.analysis import agent
    class PlanningOnly:
        def __init__(self):self.name='PLANNING_TEST';self.calls=[]
        def generate(self,task,payload,schema):
            assert 'routes' in schema['properties'],'Structured rows must not require semantic extraction'
            self.calls.append({'task':task,'model':self.name,'input_tokens':1,'output_tokens':1,'elapsed_seconds':0,'actual_model_call':False})
            return {'document_type':'price_table','summary':'Agent가 표 매핑 도구 선택','tasks':['match_catalog'],'routes':[{'source_id':s['id'],'tool':'normalize_table','reason':'표준 열이 충분함'} for s in payload['sources']]}
    monkeypatch.setenv('FOOD_ANALYSIS_MODE','agent');monkeypatch.setattr(agent,'LocalModel',PlanningOnly);login(client)
    header,row=milk();wb=openpyxl.Workbook();wb.active.append(header);wb.active.append(row);second=wb.create_sheet('중복 시트');second.append(header);second.append(row);stream=io.BytesIO();wb.save(stream)
    r=client.post('/api/v1/documents/import',headers={'Idempotency-Key':uid()},files={'file':('structured.xlsx',stream.getvalue()) if input_format=='xlsx' else ('structured.txt',('\t'.join(header)+'\n'+'\t'.join('' if v is None else str(v) for v in row)+'\n'+'\t'.join('' if v is None else str(v) for v in row)).encode())},data={'title':'표준 기준정보 검증'})
    assert r.status_code==201,r.text
    once();job=client.get('/api/v1/jobs/'+r.json()['analysis_job']['id']).json();assert job['status']=='succeeded',job
    runid=job['analysis_run_id'];report=client.get('/api/v1/analysis-runs/'+runid+'/report').json();assert len(report['model_calls'])==1 and report['tool_executions'][0]['tool']=='normalize_table'
    assert len(report['events'])==1 and len(report['events'][0]['evidence_ids'])==2
    event=report['events'][0];record=event['food_record'];record['company_name']='통합 업체 테스트'
    endpoint='/api/v1/analysis-runs/'+runid+'/items/'+event['id']
    edited=client.patch(endpoint,json={'version':report['version'],'status':'confirmed','fields':{'food_record':record},'reason':'원본 열과 업체 정보 대조'},headers={'Idempotency-Key':uid()});assert edited.status_code==200,edited.text
    prepared=post(client,'/analysis-runs/'+runid+'/review-proposals',{'version':edited.json()['version']});assert prepared.status_code==200,prepared.text
    p=client.get('/api/v1/proposals/'+prepared.json()['proposal_ids'][0]);body=p.json();assert body['summary']['status']=='ready',body['issues']
    assert not any(ch['operation']['kind']=='set_price' for ch in body['changes'])
    body,tag=approve(client,body,p.headers['etag']);assert apply(client,body,tag)['status']=='succeeded'
    result=client.get('/api/v1/foods?q=4150250003');assert result.status_code==200,result.text
    record=result.json()['items'][0]['food_record'];assert record['company_name']=='통합 업체 테스트' and record['company_id']
    assert record['prices']['source_applied']=='0' and record['prices']['survey_1']=='1'
    assert record['allergens']['contains'] is None and record['allergens']['review_status']=='unknown'
    detail=client.get('/api/v1/products/'+result.json()['items'][0]['product_id']).json()
    assert detail['variants'][0]['food_record']==record
    exported=post(client,'/analysis-runs/'+runid+'/review-export',{});assert exported.status_code==200,exported.text
    assert client.get('/api/v1/products/'+detail['id']+'/history').json()['items']
    assert client.get('/api/v1/foods?cursor=invalid').status_code==422


def test_food_delete_restore_preserves_facts_and_audit(client):
    login(client);rows=client.get('/api/v1/foods?limit=100').json()['items'];assert rows
    food=rows[0];id=food['id'];version=food['archive_version'];key=uid()
    with tx() as c:before=c.execute('SELECT count(*) n FROM facts').fetchone()['n']
    body={'archive_version':version,'reason':'삭제·복구 통합 검증'}
    r=client.request('DELETE','/api/v1/foods/'+id,json=body,headers={'Idempotency-Key':key});assert r.status_code==200,r.text
    assert r.json()['archived'] is True
    repeated=client.request('DELETE','/api/v1/foods/'+id,json=body,headers={'Idempotency-Key':key});assert repeated.status_code==200 and repeated.json()==r.json()
    assert id not in [row['id'] for row in client.get('/api/v1/foods?limit=100').json()['items']]
    assert id in [row['id'] for row in client.get('/api/v1/foods?archived=true&limit=100').json()['items']]
    assert not any(p['variant_id']==id for p in client.get('/api/v1/prices?include_scheduled=true&limit=100').json()['items'])
    stale=post(client,'/foods/'+id+'/restore',body);assert stale.status_code==409
    login(client,'reader');denied=post(client,'/foods/'+id+'/restore',{'archive_version':r.json()['archive_version'],'reason':'권한 검증'});assert denied.status_code==403
    login(client);restored=post(client,'/foods/'+id+'/restore',{'archive_version':r.json()['archive_version'],'reason':'검증 후 복구'});assert restored.status_code==200,restored.text
    assert id in [row['id'] for row in client.get('/api/v1/foods?limit=100').json()['items']]
    with tx() as c:
        assert c.execute('SELECT count(*) n FROM facts').fetchone()['n']==before
        kinds={a['data']['kind'] for a in c.execute("SELECT data FROM app_records WHERE kind='audit' AND data->>'entity_id'=%s",(id,))}
        assert {'food_archived','food_restored'}<=kinds


def test_material_delete_hides_workbook_and_can_restore(client):
    login(client);w=client.get('/api/v1/price-workbooks').json()['items'][0];id=w['document_id'];doc=client.get('/api/v1/documents/'+id).json()
    removed=client.request('DELETE','/api/v1/documents/'+id,json={'archive_version':doc['archive_version'],'reason':'원본 자료 삭제 검증'},headers={'Idempotency-Key':uid()});assert removed.status_code==200,removed.text
    assert removed.json()['archived']
    assert id not in [d['id'] for d in client.get('/api/v1/documents?limit=100').json()['items']]
    assert id in [d['id'] for d in client.get('/api/v1/documents?archived=true&limit=100').json()['items']]
    assert w['id'] not in [x['id'] for x in client.get('/api/v1/price-workbooks').json()['items']]
    # Evidence remains readable and the material cannot silently launch a new analysis.
    assert client.get('/api/v1/document-revisions/'+doc['latest_revision_id']).status_code==200
    blocked=post(client,'/analysis-runs',{'document_revision_id':doc['latest_revision_id'],'workflow_profile':'auto'});assert blocked.status_code==409
    restored=post(client,'/documents/'+id+'/restore',{'archive_version':removed.json()['archive_version'],'reason':'자료 복구 검증'});assert restored.status_code==200,restored.text
    assert w['id'] in [x['id'] for x in client.get('/api/v1/price-workbooks').json()['items']]


def test_running_material_cannot_be_removed_mid_analysis(client):
    login(client)
    r=client.post('/api/v1/documents/import',headers={'Idempotency-Key':uid()},files={'file':('busy.txt','식품 정보'.encode())},data={'title':'작업 중 삭제 경합 검증'})
    doc=r.json()['document'];jid=r.json()['analysis_job']['id']
    blocked=client.request('DELETE','/api/v1/documents/'+doc['id'],json={'archive_version':0,'reason':'분석 중 삭제 경합 검증'},headers={'Idempotency-Key':uid()});assert blocked.status_code==409,blocked.text
    cancelled=post(client,'/jobs/'+jid+'/cancel');assert cancelled.status_code==200,cancelled.text
    removed=client.request('DELETE','/api/v1/documents/'+doc['id'],json={'archive_version':0,'reason':'작업 취소 후 삭제'},headers={'Idempotency-Key':uid()});assert removed.status_code==200,removed.text


def discard_material(client,title,content):
    login(client)
    imported=client.post('/api/v1/documents/import',headers={'Idempotency-Key':uid()},files={'file':('purge-test.txt',content)},data={'title':title}).json()
    if imported.get('analysis_job'):assert post(client,'/jobs/'+imported['analysis_job']['id']+'/cancel').status_code==200
    id=imported['document']['id'];removed=client.request('DELETE','/api/v1/documents/'+id,json={'archive_version':0,'reason':'영구 삭제 기능 검증용 자료'},headers={'Idempotency-Key':uid()});assert removed.status_code==200,removed.text
    return {'id':id,'archive_version':removed.json()['archive_version']},imported


def test_bulk_selection_permanent_purge_and_shared_file_cleanup(client):
    from backend.app.domains.ingestion.purge import cleanup_files
    from backend.app.domains.ingestion.documents import DATA
    assert 'food-agent-test-assets-' in str(DATA),'Refusing to unlink production assets in tests'
    body=('공유 파일 영구 삭제 검증 '+uid()).encode()
    one,first=discard_material(client,'일괄선택검증 첫 자료',body);two,second=discard_material(client,'일괄선택검증 둘째 자료',body)
    selected=client.get('/api/v1/document-selections?q=일괄선택검증&archived=true').json()
    assert selected['total']==2 and {d['id'] for d in selected['items']}=={one['id'],two['id']}
    with tx() as c:asset=get(c,'asset',first['revision']['snapshot_asset_id']);path=DATA/asset['storage_key']
    assert path.exists()
    missing=post(client,'/document-actions',{'action':'purge','items':[one]});assert missing.status_code==422
    login(client,'reader');denied=post(client,'/document-actions',{'action':'purge','items':[one],'confirmation':'영구 삭제'});assert denied.status_code==403
    login(client)
    purged=post(client,'/document-actions',{'action':'purge','items':[one],'confirmation':'영구 삭제'});assert purged.status_code==200,purged.text
    assert purged.json()['succeeded']==1 and purged.json()['failed']==0
    assert client.get('/api/v1/documents/'+one['id']).status_code==404
    assert client.get('/api/v1/document-revisions/'+first['revision']['id']).status_code==404
    assert client.get('/api/v1/assets/'+asset['id']+'/access').status_code==404
    cleanup_files();assert path.exists() # second material still owns the same hash
    purged=post(client,'/document-actions',{'action':'purge','items':[two],'confirmation':'영구 삭제'});assert purged.json()['succeeded']==1,purged.text
    cleanup_files();assert not path.exists()
    assert client.get('/api/v1/document-selections?q=일괄선택검증&archived=true').json()['total']==0


def test_bulk_purge_protects_approved_evidence_and_reports_partial_results(client):
    login(client)
    with tx() as c:
        # Existing initial facts reference this material; deleting it would break provenance.
        fact=c.execute('SELECT data FROM facts LIMIT 1').fetchone()['data'];ev=get(c,'evidence',fact['evidence_ids'][0]);rev=get(c,'revision',ev['document_revision_id']);document=get(c,'document',rev['document_id'])
    archived=client.request('DELETE','/api/v1/documents/'+document['id'],json={'archive_version':0,'reason':'참조 보호 검증'},headers={'Idempotency-Key':uid()});assert archived.status_code==200,archived.text
    item={'id':document['id'],'archive_version':archived.json()['archive_version']}
    disposable,_=discard_material(client,'참조 없는 영구삭제 검증',('검증 '+uid()).encode())
    result=post(client,'/document-actions',{'action':'purge','items':[item,disposable],'confirmation':'영구 삭제'});assert result.status_code==200,result.text
    assert result.json()['succeeded']==1 and result.json()['failed']==1
    assert result.json()['failures'][0]['code']=='MATERIAL_IN_USE'
    assert client.get('/api/v1/documents/'+item['id']).status_code==200
    assert client.get('/api/v1/documents/'+disposable['id']).status_code==404
    restored=post(client,'/document-actions',{'action':'restore','items':[item]});assert restored.json()['succeeded']==1


def test_permanent_purge_removes_analysis_drafts_and_checkpoints(client):
    login(client)
    imported=client.post('/api/v1/documents/import',headers={'Idempotency-Key':uid()},files={'file':('notice.txt','item DEMO-001 | 공급 일시중단 | 2045-01-01 | test'.encode())},data={'title':'분석 파생자료 영구 삭제 검증'}).json()
    once();job=client.get('/api/v1/jobs/'+imported['analysis_job']['id']).json();assert job['status']=='succeeded',job
    runid=job['analysis_run_id'];pid=job['result']['proposal_ids'][0];id=imported['document']['id']
    archived=client.request('DELETE','/api/v1/documents/'+id,json={'archive_version':0,'reason':'파생 자료 정리 검증'},headers={'Idempotency-Key':uid()});assert archived.status_code==200
    purged=post(client,'/document-actions',{'action':'purge','items':[{'id':id,'archive_version':archived.json()['archive_version']}],'confirmation':'영구 삭제'});assert purged.json()['succeeded']==1,purged.text
    assert client.get('/api/v1/analysis-runs/'+runid).status_code==404
    assert client.get('/api/v1/proposals/'+pid).status_code==404
    with tx() as c:
        assert not c.execute('SELECT 1 FROM checkpoints WHERE thread_id=%s',('analysis:'+runid,)).fetchone()
        assert not c.execute('SELECT 1 FROM checkpoint_blobs WHERE thread_id=%s',('analysis:'+runid,)).fetchone()
        assert not c.execute('SELECT 1 FROM checkpoint_writes WHERE thread_id=%s',('analysis:'+runid,)).fetchone()


def test_select_all_matching_includes_other_pages_and_bulk_archive_restore(client):
    from backend.app.domains.ingestion.documents import import_document
    login(client);prefix='전체선택검증-'+uid()
    with tx() as c:
        for i in range(22):import_document(c,prefix+' '+str(i),('선택 검증 '+str(i)).encode(),'selection.txt')
    page=client.get('/api/v1/documents?q='+prefix).json();assert len(page['items'])==20 and page['total']==22
    allrows=client.get('/api/v1/document-selections?q='+prefix).json();assert allrows['total']==22
    items=[{'id':d['id'],'archive_version':d['archive_version']} for d in allrows['items']]
    archived=post(client,'/document-actions',{'action':'archive','items':items});assert archived.json()['succeeded']==22,archived.text
    assert client.get('/api/v1/document-selections?q='+prefix).json()['total']==0
    removed=client.get('/api/v1/document-selections?q='+prefix+'&archived=true').json();assert removed['total']==22
    stale=post(client,'/document-actions',{'action':'restore','items':[items[0]]});assert stale.json()['failed']==1 and stale.json()['failures'][0]['code']=='ARCHIVE_CHANGED'
    restored=post(client,'/document-actions',{'action':'restore','items':[{'id':d['id'],'archive_version':d['archive_version']} for d in removed['items']]});assert restored.json()['succeeded']==22


def test_permanent_purge_removes_workbook_rows(client):
    import io,openpyxl
    login(client);book=openpyxl.Workbook();book.active.append(['식품명','규격']);book.active.append(['영구삭제 검증 식품','1kg']);stream=io.BytesIO();book.save(stream)
    uploaded=client.post('/api/v1/price-workbooks/import',headers={'Idempotency-Key':uid()},files={'file':('purge-sheet.xlsx',stream.getvalue())});assert uploaded.status_code==201,uploaded.text
    w=uploaded.json();id=w['document_id'];sid=w['sheets'][0]['id']
    removed=client.request('DELETE','/api/v1/documents/'+id,json={'archive_version':0,'reason':'표 원본 정리 검증'},headers={'Idempotency-Key':uid()});assert removed.status_code==200,removed.text
    purged=post(client,'/document-actions',{'action':'purge','items':[{'id':id,'archive_version':removed.json()['archive_version']}],'confirmation':'영구 삭제'});assert purged.json()['succeeded']==1,purged.text
    assert client.get('/api/v1/price-workbooks/'+w['id']).status_code==404
    with tx() as c:assert not c.execute('SELECT 1 FROM price_sheet_rows WHERE sheet_id=%s',(sid,)).fetchone()


def test_permanently_deleted_site_post_is_not_recollected(client):
    from backend.app.domains.ingestion.collection import ingest
    item,imported=discard_material(client,'재수집 방지 검증',('게시글 '+uid()).encode());source_id=uid()
    with tx() as c:
        d=get(c,'document',item['id']);d.update(source_id=source_id,board_key='product_01',external_post_id='777');put(c,'document',d)
    purged=post(client,'/document-actions',{'action':'purge','items':[item],'confirmation':'영구 삭제'});assert purged.json()['succeeded']==1,purged.text
    with tx() as c:
        doc,kind=ingest(c,source_id,{'board':'product_01','post':'777'})
        assert doc is None and kind=='deleted'


def test_slow_database_dispatch_does_not_block_health_requests(client,monkeypatch):
    import asyncio,httpx,threading,time,importlib
    main=importlib.import_module('backend.app.api.transport');original=main.dispatch_request;started=threading.Event();release=threading.Event()
    login(client)
    def slow(*args):
        if args[0]=='foods':started.set();release.wait(2)
        return original(*args)
    monkeypatch.setattr(main,'dispatch_request',slow)
    async def scenario():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://testserver',cookies=dict(client.cookies)) as api:
            pending=asyncio.create_task(api.get('/api/v1/foods'))
            try:
                assert await asyncio.to_thread(started.wait,1)
                tick=time.monotonic();health=await api.get('/health');elapsed=time.monotonic()-tick
                assert health.status_code==200 and elapsed<.3 and not pending.done()
            finally:release.set();await pending
    asyncio.run(scenario())


def test_queue_lanes_can_run_collection_while_analysis_is_waiting(client,monkeypatch):
    import threading
    from backend.app.domains.jobs import worker as worker
    from backend.app.domains.jobs.service import enqueue
    while once():pass
    with tx() as c:
        source=put(c,'source',{'id':uid(),'name':'lane-test','version':1})
        # A controlled analysis failure is held off the DB while collection proceeds.
        from backend.app.domains.ingestion.documents import import_document
        doc=import_document(c,'lane analysis',b'waiting','lane.txt');run=put(c,'analysis_run',{'id':uid(),'document_revision_id':doc['revision']['id'],'mode':'rules','status':'queued'})
        analyze=enqueue(c,'analyze',{'document_revision_id':doc['revision']['id']},run['id']);run['job_id']=analyze['id'];put(c,'analysis_run',run)
        collect=enqueue(c,'collect',{'source_id':source['id']})
    started=threading.Event();release=threading.Event()
    def delayed(*args):
        started.set();release.wait(3);return {'proposal_ids':[]}
    monkeypatch.setattr(worker,'run_analysis',delayed);monkeypatch.setattr(worker,'collect_source',lambda *args:{'issues':[],'document_ids':[]})
    thread=threading.Thread(target=lambda:worker.once(['analyze']));thread.start()
    try:
        assert started.wait(1);assert worker.once(['collect'])
        assert client.get('/api/v1/jobs/'+collect['id']).json()['status']=='succeeded' and thread.is_alive()
    finally:release.set();thread.join(3)


def test_long_analysis_yields_and_resumes_without_repeating_completed_batches(client,monkeypatch):
    from backend.app.domains.analysis import agent
    from backend.app.runtime.execution import AnalysisYield
    from test_agent import TestModel
    class ProfileModel(TestModel):
        def generate(self,task,payload,schema):
            result=super().generate(task,payload,schema)
            if 'document_type' in result:result.update(document_type='notice',tasks=['extract_food_profiles'])
            else:result['events'][0]['kind']='food_profile'
            return result
    calls=0
    def boundary():
        nonlocal calls
        calls+=1
        if calls==2:raise AnalysisYield()
    monkeypatch.setattr(agent,'LocalModel',ProfileModel);monkeypatch.setattr(agent,'boundary',boundary);monkeypatch.setenv('FOOD_ANALYSIS_MODE','agent');login(client)
    source='\n'.join('AI 검증 전복 500g 72000원 '+('설명'*100) for _ in range(20))
    imported=client.post('/api/v1/documents/import',headers={'Idempotency-Key':uid()},files={'file':('continuation.txt',source.encode())},data={'title':'분석 구간 이어하기 검증'}).json();jid=imported['analysis_job']['id']
    once(['analyze']);job=client.get('/api/v1/jobs/'+jid).json();assert job['status']=='queued' and job['continuations']==1,job
    report=client.get('/api/v1/analysis-runs/'+job['analysis_run_id']+'/report').json();assert report['batches_completed']==1 and len(report['model_calls'])==2
    original_event_id=report['events'][0]['id'];monkeypatch.setattr(agent,'boundary',lambda:None)
    once(['analyze']);done=client.get('/api/v1/jobs/'+jid).json();assert done['status']=='succeeded',done
    report=client.get('/api/v1/analysis-runs/'+done['analysis_run_id']+'/report').json()
    assert report['events'][0]['id']==original_event_id
    assert len(report['model_calls'])==1+report['coverage']['total_batches']
    assert report['verification_calls_skipped']==report['coverage']['total_batches']
    assert done['performance']['model_calls']==len(report['model_calls'])
    assert done['processed_count']==done['total_count']


def test_cancel_closes_inflight_async_inference(client,monkeypatch):
    import asyncio,threading
    from backend.app.domains.analysis import agent
    started=threading.Event();closed=threading.Event()
    class WaitingModel:
        def __init__(self):self.name='WAITING_TEST';self.calls=[]
        async def agenerate(self,*args):
            started.set()
            try:await asyncio.Event().wait()
            finally:closed.set()
        async def aclose(self):closed.set()
    monkeypatch.setattr(agent,'LocalModel',WaitingModel);monkeypatch.setenv('FOOD_ANALYSIS_MODE','agent');login(client)
    imported=client.post('/api/v1/documents/import',headers={'Idempotency-Key':uid()},files={'file':('cancel.txt','식품 안내'.encode())},data={'title':'비동기 모델 취소 검증'}).json();jid=imported['analysis_job']['id']
    thread=threading.Thread(target=lambda:once(['analyze']));thread.start()
    try:
        assert started.wait(2)
        cancelled=post(client,'/jobs/'+jid+'/cancel');assert cancelled.status_code==200,cancelled.text
        thread.join(3);assert not thread.is_alive() and closed.is_set()
        assert client.get('/api/v1/jobs/'+jid).json()['status']=='cancelled'
    finally:
        if thread.is_alive():
            with tx() as c:c.execute("UPDATE jobs SET status='cancelled' WHERE id=%s",(jid,))
            thread.join(3)


def test_worker_restart_recovers_dead_same_host_owner_only(client):
    import os,socket
    from backend.app.domains.jobs.worker import recover_abandoned_jobs
    from backend.app.domains.jobs.service import enqueue; from backend.app.domains.jobs.service import savejob
    with tx() as c:
        dead=enqueue(c,'collect',{'source_id':uid()});dead.update(status='running',worker_pid=99999999,worker_host=socket.gethostname());savejob(c,dead)
        live=enqueue(c,'collect',{'source_id':uid()});live.update(status='running',worker_pid=os.getpid(),worker_host=socket.gethostname());savejob(c,live)
        unknown=enqueue(c,'collect',{'source_id':uid()});unknown.update(status='running');savejob(c,unknown)
    assert recover_abandoned_jobs()==1
    assert client.get('/api/v1/jobs/'+dead['id']).json()['status']=='queued'
    assert client.get('/api/v1/jobs/'+live['id']).json()['status']=='running'
    assert client.get('/api/v1/jobs/'+unknown['id']).json()['status']=='running'
    with tx() as c:
        for job in (dead,live,unknown):job['status']='cancelled';savejob(c,job)


def test_reader_can_logout_without_business_mutation_permissions_or_idempotency_key(client):
    login(client, 'reader')
    response = client.delete('/api/v1/auth/session')
    assert response.status_code == 204
    assert client.get('/api/v1/auth/me').status_code == 401


@pytest.mark.parametrize('count',[0,3])
def test_collection_completion_uses_actual_document_count(client,monkeypatch,count):
    from backend.app.domains.jobs import worker
    from backend.app.domains.jobs.service import enqueue,getjob
    while once():pass
    with tx() as c:
        source=put(c,'source',{'id':uid(),'name':'count-test','version':1})
        job=enqueue(c,'collect',{'source_id':source['id']})
    monkeypatch.setattr(worker,'collect_source',lambda *args:{'issues':[],'document_ids':[uid() for _ in range(count)]})
    assert worker.once(['collect'])
    with tx() as c:result=getjob(c,job['id'])
    assert result['status']=='succeeded'
    assert result['processed_count']==result['total_count']==count


def test_reconciliation_creates_new_pending_report_preserving_decisions(client):
    from backend.app.domains.analysis.reconciliation import rebuild
    from backend.app.domains.ingestion.documents import import_document
    from backend.app.domains.catalog.record import from_event
    from test_consolidation import segments
    with tx() as c:
        doc=import_document(c,'vendor normalization',b'table','vendor.txt')
        revision=doc['revision'];source_id=uid();report_id=uid();extraction_id=uid()
        source_segments=segments()
        for segment in source_segments:
            segment['evidence_id']=uid()
            put(c,'evidence',{'id':segment['evidence_id'],'document_revision_id':revision['id'],'extraction_id':extraction_id,'quote':segment['text'],'locator':segment['locator'],'source_url':None,'ocr_confidence':None})
        put(c,'extraction',{'id':extraction_id,'revision_id':revision['id'],'segments':source_segments})
        old_event={'id':uid(),'kind':'food_profile','product_name':'찰보리빵','spec':None,'company_name':'더자람','evidence_ids':[source_segments[2]['evidence_id']],'review':{'status':'skipped','reason':'사용자 제외'}}
        old_event['food_record']=from_event(old_event)
        original={'id':report_id,'analysis_run_id':source_id,'document_revision_id':revision['id'],'events':[old_event],'status':'completed','version':4,'proposal_ids':[],'plan':{'document_type':'notice'},'coverage':{'source_segments':4,'processed_segments':4},'model_calls':[]}
        put(c,'agent_report',original)
        put(c,'analysis_run',{'id':source_id,'status':'succeeded','document_revision_id':revision['id'],'extraction_id':extraction_id,'agent_report_id':report_id,'mode':'agent','created_at':now()})
        admin=next(u for u in records(c,'user') if u['username']=='admin')
        result=rebuild(c,source_id,admin['id']);second=rebuild(c,source_id,admin['id'])
        assert result['id']==second['id'] and result['id']!=source_id
        assert get(c,'agent_report',report_id)==original
        rebuilt=get(c,'agent_report',result['agent_report_id'])
        assert len(rebuilt['events'])==2 and rebuilt['model_calls']==[]
        assert all(not e.get('review') for e in rebuilt['events'])
        assert {e['amount'] for e in rebuilt['events']}=={'720','1600'}
        assert rebuilt['consolidation']['source_report_version']==4
        assert get(c,'asset',result['export_asset_id'])['filename'].endswith('.xlsx')
    login(client)
    response=post(client,f'/analysis-runs/{source_id}/normalize')
    assert response.status_code==201,response.text
    assert response.json()['id']==result['id']


def test_inbox_groups_internal_bundles_and_uses_latest_report_before_paging(client):
    from backend.app.domains.ingestion.documents import import_document
    login(client)
    with tx() as c:
        doc=import_document(c,'inbox grouping',b'group','inbox.txt');revision=doc['revision'];run_id=uid();report_id=uid()
        events=[{'id':uid(),'review':{'status':status}} for status in ['pending','confirmed','skipped','pending']]
        proposal_ids=[]
        for i in range(3):
            pid=uid();proposal_ids.append(pid)
            put(c,'proposal',{'id':pid,'analysis_run_id':run_id,'summary':{'id':pid,'title':f'inbox grouping AI 변경안 {i+1}','status':'draft','change_count':45,'blocking_count':9,'created_at':now()},'changes':[]})
        put(c,'agent_report',{'id':report_id,'status':'completed','events':events,'proposal_ids':proposal_ids})
        put(c,'analysis_run',{'id':run_id,'document_revision_id':revision['id'],'agent_report_id':report_id,'status':'succeeded','mode':'agent','created_at':now()})
    response=client.get('/api/v1/review-inbox?q=inbox%20grouping&limit=1');assert response.status_code==200,response.text
    inbox=response.json();assert len(inbox['items'])==1 and not inbox['has_more']
    row=inbox['items'][0]
    assert row['item_count']==4 and row['pending_count']==2 and row['confirmed_count']==1 and row['skipped_count']==1
    assert row['href']==f'/analysis-runs/{run_id}/review'
    with tx() as c:
        newer=uid();new_report=uid()
        put(c,'agent_report',{'id':new_report,'status':'completed','events':[{'id':uid()}],'proposal_ids':[]})
        put(c,'analysis_run',{'id':newer,'document_revision_id':revision['id'],'agent_report_id':new_report,'status':'succeeded','mode':'agent','created_at':now()})
    items=client.get('/api/v1/review-inbox?q=inbox%20grouping').json()['items']
    assert len(items)==1 and items[0]['id']==newer and items[0]['item_count']==1
    with tx() as c:
        assert all(get(c,'proposal',pid)['summary']['status']=='draft' for pid in proposal_ids)
        c.execute("INSERT INTO record_archives(record_kind,record_id,archived,version,actor_id,reason) VALUES('document',%s,true,1,'test','hide')",(revision['document_id'],))
    assert client.get('/api/v1/review-inbox?q=inbox%20grouping').json()['items']==[]


@pytest.mark.parametrize('states,expected',[
    (['approved','ready'],'ready'),(['approved','applied'],'approved'),
    (['rejected','approved'],'conflict'),(['rejected'],'rejected'),
    (['applied','applied'],'applied'),
])
def test_inbox_does_not_claim_whole_approval_for_mixed_batches(states,expected):
    from backend.app.domains.review.inbox import aggregate_status
    assert aggregate_status(states,4)==expected


def test_normalization_does_not_restore_stale_parser_attributes(client):
    from backend.app.domains.analysis.reconciliation import preview
    from backend.app.domains.analysis.consolidation import enrich_tables,table_event
    from test_consolidation import segments
    with tx() as c:
        source=segments();row=next(s for s in enrich_tables(source) if s.get('food_record'))
        stale=table_event(row);stale['food_record']['attributes']['other']=['25g','개','잘못된 이전 값']
        run_id,report_id,ex_id=uid(),uid(),uid()
        put(c,'extraction',{'id':ex_id,'revision_id':'revision','segments':source})
        put(c,'agent_report',{'id':report_id,'events':[stale]})
        put(c,'analysis_run',{'id':run_id,'status':'succeeded','agent_report_id':report_id,'extraction_id':ex_id,'document_revision_id':'revision'})
        _,_,events,_=preview(c,run_id)
        first=next(e for e in events if e['product_name']=='팥 찰보리빵')
        assert first['food_record']['attributes']['other']==['간편한 한 끼']
        assert '잘못된 이전 값' not in str(events)


def test_agent_review_route_does_not_call_extractor_or_catalog_or_stage(client,monkeypatch):
    from backend.app.domains.analysis import agent
    class ReviewModel:
        def __init__(self):self.name='REVIEW_ROUTE_TEST';self.calls=[]
        def generate(self,task,payload,schema):
            assert 'routes' in schema['properties'],'Agent review route must not invoke semantic extraction'
            self.calls.append({'task':task,'model':self.name,'input_tokens':1,'output_tokens':1,'elapsed_seconds':0,'actual_model_call':False})
            return {'document_type':'other','summary':'직접 확인 필요','tasks':['no_business_change'],'routes':[{'source_id':s['id'],'tool':'request_review','reason':'자료만으로 품목 확정 불가'} for s in payload['sources']]}
    monkeypatch.setenv('FOOD_ANALYSIS_MODE','agent');monkeypatch.setattr(agent,'LocalModel',ReviewModel);login(client)
    imported=client.post('/api/v1/documents/import',headers={'Idempotency-Key':uid()},files={'file':('review-source.txt','읽기 어려운 자료입니다.'.encode())},data={'title':'직접 검토 경로 테스트'}).json()
    once(['analyze']);job=client.get('/api/v1/jobs/'+imported['analysis_job']['id']).json();assert job['status']=='succeeded',job
    report=client.get('/api/v1/analysis-runs/'+job['analysis_run_id']+'/report').json()
    assert report['events']==[] and job['result']['proposal_ids']==[]
    assert len(report['model_calls'])==1 and len(report['manual_evidence_ids'])==1
    assert report['coverage']['processed_segments']==0 and report['coverage']['manual_segments']==1
    assert [t['tool'] for t in report['tool_executions']]==['request_review']
    assert client.get('/api/v1/documents/'+imported['document']['id']).json()['analysis_status']=='partial'


def test_browser_session_cookie_rotation_expiry_and_logout(client):
    login(client)
    old=client.cookies.get('food_session')
    response=post(client,'/auth/session',{'username':'admin','password':'local-food-2026'})
    assert response.status_code==200,response.text
    client.headers['X-CSRF-Token']=response.json()['csrf_token']
    assert 'max-age' not in response.headers['set-cookie'].lower()
    assert client.get('/api/v1/auth/me',headers={'Cookie':'food_session='+old}).status_code==401
    assert client.get('/api/v1/products',headers={'Cookie':'food_session=invalid'}).status_code==401
    assert client.get('/api/v1/products').status_code==200
    assert client.delete('/api/v1/auth/session').status_code==204
    assert client.get('/api/v1/auth/me').status_code==401
    login(client)
    with tx() as c:c.execute("UPDATE sessions SET expires_at=now()-interval '1 second'")
    assert client.get('/api/v1/auth/me').status_code==401
    assert client.get('/api/v1/products').status_code==401


@pytest.mark.parametrize('budget_code',['IMAGE_LAYOUT_BUDGET','IMAGE_REGION_BUDGET','MODEL_INPUT_BUDGET','IMAGE_REGION_SOURCE','IMAGE_REGION_COVERAGE','MODEL_SCHEMA_INVALID','MODEL_OUTPUT_LIMIT'])
def test_image_budget_failure_preserves_other_source_results(client,monkeypatch,budget_code):
    from backend.app.domains.analysis import agent,planning,workflow
    from backend.app.infrastructure.database import Problem
    from test_agent import TestModel
    class Model(TestModel):
        def generate(self,task,payload,schema):
            if 'routes' in schema['properties']:
                return {'document_type':'mixed','summary':'이미지와 공지','tasks':['extract_prices'],
                        'routes':[{'source_id':s['id'],'tool':'extract_image_regions' if s['location']['kind']=='image' else 'extract_text','reason':'내용별 도구'} for s in payload['sources']]}
            return super().generate(task,payload,schema)
    async def oversized(*args):raise Problem(422,budget_code,'이미지 예산 초과')
    monkeypatch.setattr(planning,'image_regions',oversized)
    monkeypatch.setattr(agent,'LocalModel',Model);monkeypatch.setenv('FOOD_ANALYSIS_MODE','agent')
    monkeypatch.setattr(workflow,'parse',lambda *args:[
        {'text':'이미지 상품 원문','confidence':.9,'locator':{'kind':'image','page_number':1,'bbox':[0,0,1,1]}},
        {'text':'AI 검증 전복 500g 72000원 2038-11-01 원물 상승','confidence':1,'locator':{'kind':'html','block_id':'notice'}}])
    login(client)
    response=client.post('/api/v1/documents/import',headers={'Idempotency-Key':uid()},files={'file':('budget.txt',b'test')},data={'title':'부분 원문 확인'})
    assert response.status_code==201,response.text
    jobid=response.json()['analysis_job']['id'];assert once()
    job=client.get('/api/v1/jobs/'+jobid).json();assert job['status']=='succeeded',job
    report=client.get('/api/v1/analysis-runs/'+job['analysis_run_id']+'/report').json()
    assert len(report['manual_evidence_ids'])==1
    assert report['tool_executions'][0]['review_required']['code']==budget_code
    assert len(report['events'])==1 and report['events'][0]['amount']=='72000'
    assert report['export_asset_id'] and report['proposal_ids']==[]


def test_food_catalog_edit_is_versioned_audited_and_role_checked(client):
    login(client)
    row=client.get('/api/v1/foods').json()['items'][0]
    record=copy.deepcopy(row['food_record']);record['food_name']='수정 검증 식품';record['attributes']['origin_country']='KR'
    body={'food_record':record,'reason':'원문 표기 정정'};path='/api/v1/foods/'+row['id'];key=uid()
    with tx() as c:before=c.execute('SELECT count(*) n FROM facts').fetchone()['n']
    r=client.patch(path,json=body,headers={'If-Match':'"'+str(row['version'])+'"','Idempotency-Key':key});assert r.status_code==200,r.text
    edited=r.json();assert edited['version']>row['version'] and edited['food_record']['food_name']=='수정 검증 식품'
    assert client.patch(path,json=body,headers={'If-Match':'"'+str(row['version'])+'"','Idempotency-Key':key}).json()==edited
    audit=client.get('/api/v1/audit-events/'+edited['audit_event_id']).json()
    assert audit['before']['food_name']==row['food_record']['food_name'] and audit['after']['food_name']=='수정 검증 식품'
    assert audit['reason']=='원문 표기 정정' and audit['actor']
    assert audit['evidence_ids']==row['evidence_ids']
    assert client.patch(path,json=body,headers={'If-Match':'"'+str(row['version'])+'"','Idempotency-Key':uid()}).status_code==412
    bad=copy.deepcopy(body);bad['food_record']['specification']['quantity']='-2'
    assert client.patch(path,json=bad,headers={'If-Match':'"'+str(edited['version'])+'"','Idempotency-Key':uid()}).status_code==422
    login(client,'operator')
    assert client.patch(path,json=body,headers={'If-Match':'"'+str(edited['version'])+'"','Idempotency-Key':uid()}).status_code==403
    login(client,'reviewer')
    newer=client.patch(path,json=body,headers={'If-Match':'"'+str(edited['version'])+'"','Idempotency-Key':uid()});assert newer.status_code==200,newer.text
    with tx() as c:assert c.execute('SELECT count(*) n FROM facts').fetchone()['n']==before
    login(client)


def test_single_review_approval_requires_confirmation_and_reuses_jobs(client,monkeypatch):
    from backend.app.domains.analysis import agent
    from test_agent import TestModel
    name='승인 통합 검증 '+uid()
    class ProfileModel(TestModel):
        def generate(self,task,payload,schema):
            if 'routes' in schema['properties']:
                return {'document_type':'notice','summary':'식품 정보','tasks':['extract_food_profiles'],
                    'routes':[{'source_id':s['id'],'tool':'extract_text','reason':'식품 본문'} for s in payload['sources']]}
            event={k:None for k in ['company_name','food_code','attributes_text','allergen_text','spec','amount','quantity','unit','effective_from','effective_to','reason','price_basis']}
            return {'events':[{**event,'kind':'food_profile','product_name':name,'replacements':[],'uncertainties':[],'source_ids':[payload['segments'][0]['id']]}]}
    monkeypatch.setattr(agent,'LocalModel',ProfileModel);monkeypatch.setenv('FOOD_ANALYSIS_MODE','agent');login(client)
    imported=client.post('/api/v1/documents/import',headers={'Idempotency-Key':uid()},files={'file':('approval.txt',name.encode())},data={'title':name});assert imported.status_code==201,imported.text
    once();runid=imported.json()['analysis_job']['analysis_run_id'];report=client.get('/api/v1/analysis-runs/'+runid+'/report').json();path='/api/v1/analysis-runs/'+runid+'/approve'
    assert post(client,path.removeprefix('/api/v1'),{'version':report['version']}).status_code==422
    item=report['events'][0]
    reviewed=client.patch('/api/v1/analysis-runs/'+runid+'/items/'+item['id'],json={'version':report['version'],'status':'confirmed','fields':{},'reason':'원문과 대조'},headers={'Idempotency-Key':uid()});assert reviewed.status_code==200,reviewed.text
    assert post(client,path.removeprefix('/api/v1'),{'version':report['version']}).status_code==409
    with tx() as c:assert not c.execute('SELECT 1 FROM food_profiles WHERE data->>\'food_name\'=%s',(name,)).fetchone()
    key=uid();body={'version':reviewed.json()['version']}
    approved=post(client,path.removeprefix('/api/v1'),body,key=key);assert approved.status_code==202,approved.text
    assert len(approved.json()['jobs'])==1
    assert post(client,path.removeprefix('/api/v1'),body,key=key).json()==approved.json()
    assert once()
    with tx() as c:assert c.execute('SELECT 1 FROM food_profiles WHERE data->>\'food_name\'=%s',(name,)).fetchone()
    login(client,'operator')
    assert post(client,path.removeprefix('/api/v1'),{'version':approved.json()['report']['version']}).status_code==403
    login(client)


def test_truncated_model_output_splits_source_rows_and_preserves_review_boundary(client,monkeypatch):
    from backend.app.domains.analysis import agent,workflow
    from backend.app.infrastructure.database import Problem
    from test_agent import TestModel
    calls=[]
    class Model(TestModel):
        def generate(self,task,payload,schema):
            if 'routes' in schema['properties']:return {'document_type':'notice','summary':'원문 행','tasks':['extract_food_profiles'],'routes':[{'source_id':s['id'],'tool':'extract_text','reason':'본문'} for s in payload['sources']]}
            calls.append(len(payload['segments']))
            if len(payload['segments'])>1:raise Problem(422,'MODEL_OUTPUT_LIMIT','출력 상한')
            source=payload['segments'][0];event={k:None for k in ['company_name','food_code','attributes_text','allergen_text','spec','amount','quantity','unit','effective_from','effective_to','reason','price_basis']}
            return {'events':[{**event,'kind':'food_profile','product_name':source['text'],'replacements':[],'uncertainties':[],'source_ids':[source['id']]}]}
    monkeypatch.setattr(agent,'LocalModel',Model);monkeypatch.setenv('FOOD_ANALYSIS_MODE','agent')
    monkeypatch.setattr(workflow,'parse',lambda *args:[{'text':name,'confidence':1,'locator':{'kind':'html','block_id':name}} for name in ['분할 검증 식품 가','분할 검증 식품 나','분할 검증 식품 다']])
    login(client);r=client.post('/api/v1/documents/import',headers={'Idempotency-Key':uid()},files={'file':('split.txt',b'test')},data={'title':'출력 제한 복구'})
    assert r.status_code==201,r.text
    assert once();job=client.get('/api/v1/jobs/'+r.json()['analysis_job']['id']).json();assert job['status']=='succeeded',job
    report=client.get('/api/v1/analysis-runs/'+job['analysis_run_id']+'/report').json()
    assert len(report['events'])==3 and calls==[3,1,2,1,1]
    assert len(set(e['evidence_ids'][0] for e in report['events']))==3
    assert report['proposal_ids']==[] and not report.get('manual_evidence_ids')


def test_image_region_dto_keeps_all_line_references(client,monkeypatch):
    from backend.app.domains.analysis import agent,workflow
    from test_agent import TestModel
    class Model(TestModel):
        def generate(self,task,payload,schema):
            if 'routes' in schema['properties']:return {'document_type':'marketing','summary':'상품 이미지','tasks':['extract_food_profiles'],'routes':[{'source_id':s['id'],'tool':'extract_image_regions','reason':'상품 배치'} for s in payload['sources']]}
            if 'regions' in schema['properties']:return {'regions':[{'label':'압축 검증 식품','source_ids':[line[0] for line in payload['lines']],'context_ids':[]}],'unassigned_ids':[]}
            assert len(payload['segments'])==1
            event={k:None for k in ['company_name','food_code','attributes_text','spec','amount','quantity','unit','effective_from','effective_to','reason','price_basis']}
            return {'events':[{**event,'allergen_text':'(5,6,12)','kind':'food_profile','product_name':'압축 검증 식품','replacements':[],'uncertainties':[],'source_ids':['S1']}]}
    monkeypatch.setattr(agent,'LocalModel',Model);monkeypatch.setenv('FOOD_ANALYSIS_MODE','agent')
    monkeypatch.setattr(workflow,'parse',lambda *args:[{'text':('압축 검증 식품 (5,6,12)' if i==0 else '원재료 설명 '+str(i)),'confidence':1,'locator':{'kind':'image','page_number':1,'bbox':[0,0,1,1]}} for i in range(41)])
    login(client);r=client.post('/api/v1/documents/import',headers={'Idempotency-Key':uid()},files={'file':('image.txt',b'test')},data={'title':'상품 영역 압축'})
    assert once();job=client.get('/api/v1/jobs/'+r.json()['analysis_job']['id']).json();assert job['status']=='succeeded',job
    report=client.get('/api/v1/analysis-runs/'+job['analysis_run_id']+'/report').json();event=report['events'][0]
    assert len(event['evidence_ids'])==41
    assert event['food_record']['allergens']['contains']==['soy','wheat','tomato']
    assert report['proposal_ids']==[]


@pytest.mark.parametrize('code,expected',[('SCAN_CONTINUES','succeeded'),('SOURCE_SIZE','partial')])
def test_collection_continuation_notice_is_not_a_failure(client,monkeypatch,code,expected):
    import backend.app.domains.jobs.worker as worker
    source=client.get('/api/v1/sources').json()['items'][0]
    monkeypatch.setattr(worker,'collect_source',lambda *args,**kwargs:{'document_ids':[],'counts':{'new':0,'updated':0,'unchanged':0},'analysis_job_ids':[],'issues':[{'code':code,'message':'검증','board':'product_del'}]})
    login(client)
    result=post(client,'/collection-runs',{'source_id':source['id'],'board_keys':['product_del'],'max_posts_per_board':1,'revisit_days':0,'auto_analyze':False})
    assert result.status_code==202,result.text
    assert once();job=client.get('/api/v1/jobs/'+result.json()['id']).json()
    assert job['status']==expected and job['issues'][0]['code']==code
    filtered=client.get('/api/v1/jobs?type=collect').json()
    assert filtered['items'] and all(row['type']=='collect' for row in filtered['items'])
    assert client.get('/api/v1/jobs?type=invalid').status_code==422


def test_vendor_workbook_registers_and_normalizes_without_row_llm(client,monkeypatch):
    import io,openpyxl
    from backend.app.domains.analysis import agent
    wb=openpyxl.Workbook();ws=wb.active;ws.title='단가표'
    ws.append(['2026년 신제품 가격표']);ws.append(['품 목','개별중량','학교가(vat포함)개당가격','성분 및 함량','알러지 유발물질 NO.'])
    ws.append(['닭다리 꼬치','50g',1900,'닭고기 100%','5,6,15,18']);ws.append([None,'70g',2130,None,None]);ws.merge_cells('A3:A4');ws.merge_cells('D3:D4');ws.merge_cells('E3:E4')
    output=io.BytesIO();wb.save(output);wb.close()
    class TableModel:
        def __init__(self):self.name='TEST';self.calls=[]
        def generate(self,task,payload,schema):
            assert 'routes' in schema['properties'],'표 행을 LLM으로 해석하면 안 됩니다.'
            assert payload['sources'][0]['structured_rows']==2
            self.calls.append({'task':task,'model':'TEST','input_tokens':1,'output_tokens':1,'elapsed_seconds':0,'actual_model_call':False})
            return {'document_type':'price_table','summary':'명확한 단가표','tasks':['extract_food_profiles'],'routes':[{'source_id':s['id'],'tool':'normalize_table','reason':'식품명·규격·가격 열 인식'} for s in payload['sources']]}
    monkeypatch.setattr(agent,'LocalModel',TableModel);monkeypatch.setenv('FOOD_ANALYSIS_MODE','agent');login(client)
    response=client.post('/api/v1/documents/import',headers={'Idempotency-Key':uid()},files={'file':('vendor.xlsx',output.getvalue())},data={'title':'표 직접 등록'})
    assert response.status_code==201,response.text
    imported=response.json();assert once();job=client.get('/api/v1/jobs/'+imported['analysis_job']['id']).json();assert job['status']=='succeeded',job
    report=client.get('/api/v1/analysis-runs/'+job['analysis_run_id']+'/report').json()
    assert len(report['events'])==2 and len(report['model_calls'])==1
    records=[e['food_record'] for e in report['events']]
    assert {r['specification']['quantity'] for r in records}=={'50','70'}
    assert {r['prices']['source_columns'][0]['amount'] for r in records}=={'1900','2130'}
    assert all(r['food_name']=='닭다리 꼬치' and r['allergens']['contains']==['soy','wheat','chicken','shellfish'] for r in records)
    assert len(report['events'][1]['evidence_ids'])==2
    tables=client.get('/api/v1/price-workbooks?limit=100').json()
    assert any(w['document_id']==imported['document']['id'] for w in tables['items'])
    matching=next(w for w in tables['items'] if w['document_id']==imported['document']['id'])
    registered=client.get('/api/v1/price-workbooks/'+matching['id']).json()
    assert registered['sheets'][0]['header_row']==2
    assert report['proposal_ids']==[]


def test_approved_same_size_flavors_keep_separate_catalog_variants(client,monkeypatch):
    from backend.app.domains.analysis import agent,workflow
    from backend.app.domains.catalog.record import empty_record,specification
    class TableModel:
        def __init__(self):self.name='TEST';self.calls=[]
        def generate(self,task,payload,schema):return {'document_type':'price_table','summary':'맛별 품목','tasks':['extract_food_profiles'],'routes':[{'source_id':s['id'],'tool':'normalize_table','reason':'표 행'} for s in payload['sources']]}
    name='맛 구분 검증 '+uid();records=[]
    for flavor in ['오리지널','매콤']:
        record=empty_record();record.update(food_name=name,raw_food_name=name);record['attributes']['flavor']=flavor;record['specification']=specification('50g');records.append(record)
    monkeypatch.setenv('FOOD_ANALYSIS_MODE','agent');monkeypatch.setattr(agent,'LocalModel',TableModel)
    monkeypatch.setattr(workflow,'parse',lambda *args:[{'text':name+' '+r['attributes']['flavor'],'confidence':1,'locator':{'kind':'html','block_id':str(i)},'food_record':r} for i,r in enumerate(records)])
    login(client);r=client.post('/api/v1/documents/import',headers={'Idempotency-Key':uid()},files={'file':('flavor.txt',b'test')},data={'title':'맛별 SKU'})
    assert once();runid=r.json()['analysis_job']['analysis_run_id'];report=client.get('/api/v1/analysis-runs/'+runid+'/report').json();assert len(report['events'])==2
    for item in list(report['events']):
        checked=client.patch('/api/v1/analysis-runs/'+runid+'/items/'+item['id'],json={'version':report['version'],'status':'confirmed','fields':{},'reason':'맛 구분 확인'},headers={'Idempotency-Key':uid()});assert checked.status_code==200,checked.text;report=checked.json()
    approved=post(client,'/analysis-runs/'+runid+'/approve',{'version':report['version']});assert approved.status_code==202,approved.text
    assert once()
    with tx() as c:
        rows=c.execute("SELECT fp.variant_id,fp.data#>>'{attributes,flavor}' flavor FROM food_profiles fp WHERE fp.data->>'food_name'=%s",(name,)).fetchall()
        assert len(rows)==2 and {row['flavor'] for row in rows}=={'오리지널','매콤'}
