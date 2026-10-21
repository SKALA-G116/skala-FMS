"""
==============================================================================
FMS_FILE_SPEC
test_agent.py - 기능·경계·회귀 검증
==============================================================================
설명:
    - 기능·경계·회귀 검증
입력·출력 명세:
    - 입력: 테스트 fixture·가상 입력·명시적 mock/테스트 대역
    - 출력: assert 결과와 실패 사유
실행 가정:
    - DB 통합 테스트는 별도 _test DB·임시 assets 사용; 대역과 실제 모델 검증을 구분
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

    상세 Git 이력: git log --follow -- backend/tests/test_agent.py
    공통 규칙: doc/file-header-policy.md

기존 모듈 설명:
    Deterministic integration tests use an explicit test double; live results are separate.
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

import io,json
import httpx,openpyxl,pytest
from backend.app.infrastructure.database import Problem, get, put, tx, uid; import json
from backend.app.domains.analysis import agent
from backend.app.domains.analysis.provider import LocalModel
from backend.app.domains.analysis.schemas import event_schema
from backend.app.domains.analysis.export import workbook_bytes
from backend.app.domains.jobs.worker import once

class TestModel:
    __test__=False
    def __init__(self):self.name='TEST_DOUBLE';self.calls=[]
    def generate(self,task,payload,schema):
        self.calls.append({'task':task,'model':self.name,'input_tokens':1,'output_tokens':1,'elapsed_seconds':0,'actual_model_call':False})
        if 'document_type' in schema['properties']:return {'document_type':'notice','summary':'검증용 단가 변경','tasks':['extract_prices','match_catalog','create_review_excel']}
        source=next(s['id'] for s in payload['segments'] if '72000' in s['text'])
        return {'events':[{'kind':'price','product_name':'AI 검증 전복','spec':'500g','amount':'72000','quantity':'1','unit':'g','effective_from':'2038-11-01','effective_to':None,'reason':'원물 상승','replacements':[],'price_basis':'공급 단가','uncertainties':[],'source_ids':[source]}]}

def agent_pipeline(client,monkeypatch):
    from test_workflow import login,post,approve,apply
    while once():pass
    monkeypatch.setenv('FOOD_ANALYSIS_MODE','agent');monkeypatch.setattr(agent,'LocalModel',TestModel)
    login(client)
    r=client.post('/api/v1/documents/import',headers={'Idempotency-Key':uid()},files={'file':('notice.txt','AI 검증 전복 500g 72000원\n2038년 11월 1일부터 적용\n사유: 원물 상승'.encode())},data={'title':'AI 자동 처리 검증'})
    assert r.status_code==201,r.text
    imported=r.json();jid=imported['analysis_job']['id']
    with tx() as c:
        d=get(c,'document',imported['document']['id']);d['author_display_name']='테스트 공급처';put(c,'document',d)
        before=c.execute('SELECT count(*) n FROM facts').fetchone()['n']
    once();job=client.get('/api/v1/jobs/'+jid).json();assert job['status']=='succeeded',job
    report=client.get('/api/v1/analysis-runs/'+job['analysis_run_id']+'/report').json();assert len(report['model_calls'])==3
    event=report['events'][0];assert (event['amount'],event['quantity'],event['unit'])==('72000','500','g')
    assert len(event['evidence_ids'])==3 # amount, date and reason all linked
    pid=job['result']['proposal_ids'][0];r=client.get('/api/v1/proposals/'+pid);p=r.json();tag=r.headers['etag']
    assert p['summary']['status']=='draft' and any(i['code']=='AI_CONFIRMATION_REQUIRED' for i in p['issues'])
    with tx() as c:
        assert c.execute('SELECT count(*) n FROM facts').fetchone()['n']==before
        a=get(c,'asset',report['export_asset_id'])
        from backend.app.domains.ingestion.documents import DATA
        wb=openpyxl.load_workbook(io.BytesIO((DATA/a['storage_key']).read_bytes()));assert wb['식품 변경안']['D2'].value=='72000';assert wb['식품 변경안']['E2'].value=='500'
    assert post(client,'/proposals/'+pid+'/decisions',{'action':'approve','revision':1},tag).status_code==409
    assert post(client,'/proposals/'+pid+'/confirm-ai',{'revision':99,'reason':'확인'},tag).status_code==409
    r=post(client,'/proposals/'+pid+'/confirm-ai',{'revision':1,'reason':'공급처 및 500g 판매 단위를 원문과 대조'},tag);assert r.status_code==200,r.text
    p,tag=approve(client,r.json(),r.headers['etag']);assert apply(client,p,tag)['status']=='succeeded'
    products=client.get('/api/v1/products?q=AI%20검증').json()['items'];assert len(products)==1
    price=client.get('/api/v1/prices?as_of=2038-11-01&product_id='+products[0]['id']).json()['items'][0]
    assert price['value']['quantity']=='500' and price['value']['amount']=='72000'
    assert client.get('/api/v1/products/'+products[0]['id']+'/history').json()['items']

def test_model_schema_invalid_has_no_regex_fallback(monkeypatch):
    original=httpx.Client
    def handler(req):return httpx.Response(200,json={'message':{'content':json.dumps({'events':[{'kind':'price','source_ids':['INVENTED']}]})}})
    monkeypatch.setattr(httpx,'Client',lambda **kw:original(transport=httpx.MockTransport(handler)))
    with pytest.raises(Problem) as e:LocalModel().generate('test',{},event_schema(['S1']))
    assert e.value.code=='MODEL_SCHEMA_INVALID'

def test_model_failure_explicit(monkeypatch):
    original=httpx.Client
    monkeypatch.setattr(httpx,'Client',lambda **kw:original(transport=httpx.MockTransport(lambda req:httpx.Response(503))))
    with pytest.raises(Problem) as e:LocalModel().generate('test',{},event_schema(['S1']))
    assert e.value.code=='MODEL_UNAVAILABLE'

def test_review_export_does_not_execute_source_formulas():
    report={'events':[],'model':'test','plan':{'summary':'=HYPERLINK("http://evil")'},'coverage':{'source_segments':1,'processed_segments':1},'model_calls':[],'analysis_run_id':uid()}
    evidence=[{'id':uid(),'quote':'=1+2','locator':{'kind':'html'},'source_url':None}]
    wb=openpyxl.load_workbook(io.BytesIO(workbook_bytes(report,evidence,None)))
    assert wb['원문 근거']['B2'].value=='=1+2' and wb['원문 근거']['B2'].data_type=='s'
    assert wb['AI 실행 정보']['B3'].data_type=='s'

def test_source_windows_preserve_text_and_evidence():
    segments=[{'text':'식품'*5000,'evidence_id':'E1','asset_id':'A','locator':{'kind':'html'}}]
    groups=list(agent.batches(segments));assert len(groups)>1
    assert ''.join(s['text'] for group in groups for s in group)==segments[0]['text']
    assert all(s['evidence_id']=='E1' for group in groups for s in group)

class HallucinatedModel(TestModel):
    def generate(self,task,payload,schema):
        result=super().generate(task,payload,schema)
        for event in result.get('events',[]):event.update(kind='discontinued',amount='146000')
        return result

def hallucination_guard(client,monkeypatch):
    from test_workflow import login
    monkeypatch.setenv('FOOD_ANALYSIS_MODE','agent');monkeypatch.setattr(agent,'LocalModel',HallucinatedModel);login(client)
    r=client.post('/api/v1/documents/import',headers={'Idempotency-Key':uid()},files={'file':('source.txt','AI 검증 전복 500g 72000원. 일시품절 안내입니다.'.encode())},data={'title':'근거 없는 단종·가격 차단 검증'})
    jid=r.json()['analysis_job']['id'];once();job=client.get('/api/v1/jobs/'+jid).json()
    assert job['status']=='succeeded',job
    assert job['result']['proposal_ids']==[]
    report=client.get('/api/v1/analysis-runs/'+job['analysis_run_id']+'/report').json();event=report['events'][0]
    assert event['amount'] is None and event['excluded_reason']
    assert event['match_status']=='unresolved'

class TwoItemModel(TestModel):
    def generate(self,task,payload,schema):
        result=super().generate(task,payload,schema)
        if result.get('events'):
            first=result['events'][0];first['product_name']='품목 검토 테스트 전복';first['effective_from']='2040-11-01'
            second={**first,'kind':'temporarily_unavailable','product_name':'품목 검토 테스트 생선','amount':None,'quantity':'22개','unit':'kg','spec':'1kg'}
            result['events'].append(second)
        return result

def editable_review_pipeline(client,monkeypatch):
    from test_workflow import login,post,approve,apply
    monkeypatch.setenv('FOOD_ANALYSIS_MODE','agent');monkeypatch.setattr(agent,'LocalModel',TwoItemModel);login(client)
    r=client.post('/api/v1/documents/import',headers={'Idempotency-Key':uid()},files={'file':('review.txt','품목 검토 테스트 전복 500g 72000원\n품목 검토 테스트 생선 1kg 일시품절\n2040년 11월 1일부터 원물 상승'.encode())},data={'title':'품목별 DTO 수정·제외 검증'})
    imported=r.json()
    with tx() as c:
        d=get(c,'document',imported['document']['id']);d['author_display_name']='품목 검토 공급처';put(c,'document',d)
    once();job=client.get('/api/v1/jobs/'+imported['analysis_job']['id']).json();assert job['status']=='succeeded',job
    runid=job['analysis_run_id'];report=client.get('/api/v1/analysis-runs/'+runid+'/report').json();assert report['dto_schema']=='food-change-dto-v1'
    old_ids=report['proposal_ids'];first,second=report['events'];version=report['version']
    supplier=next(s for s in client.get('/api/v1/suppliers?limit=100').json()['items'] if s['name']=='품목 검토 공급처')
    values={k:first.get(k) for k in ('kind','product_name','spec','amount','quantity','unit','effective_from','effective_to','reason','replacements','price_basis')}
    values.update(amount='71000',supplier_id=supplier['id'],product_id=None)
    endpoint='/api/v1/analysis-runs/'+runid+'/items/'+first['id']
    r=client.patch(endpoint,json={'version':version,'status':'confirmed','fields':values,'reason':'원본 대조 후 금액 정정'},headers={'Idempotency-Key':uid()});assert r.status_code==200,r.text
    report=r.json()
    stale=client.patch(endpoint,json={'version':version,'status':'skipped','fields':{},'reason':'제외'},headers={'Idempotency-Key':uid()});assert stale.status_code==409
    availability=client.patch('/api/v1/analysis-runs/'+runid+'/items/'+second['id'],json={'version':report['version'],'status':'confirmed','fields':{'supplier_id':supplier['id'],'product_id':None},'reason':'포장 수량이 22개인 공급 공지 확인'},headers={'Idempotency-Key':uid()});assert availability.status_code==200,availability.text
    report=availability.json();assert report['events'][1]['review']['fields']['quantity'] is None
    r=client.patch('/api/v1/analysis-runs/'+runid+'/items/'+second['id'],json={'version':report['version'],'status':'skipped','fields':{},'reason':'이번 반영에서 제외'},headers={'Idempotency-Key':uid()});assert r.status_code==200,r.text
    version=r.json()['version'];r=post(client,'/analysis-runs/'+runid+'/review-proposals',{'version':version});assert r.status_code==200,r.text
    assert len(r.json()['proposal_ids'])==1
    for pid in old_ids:assert client.get('/api/v1/proposals/'+pid).json()['summary']['status']=='superseded'
    p=client.get('/api/v1/proposals/'+r.json()['proposal_ids'][0]);body=p.json();assert body['summary']['status']=='ready',body['issues']
    assert all(ch['field_evidence'][0]['origin']=='reviewer' for ch in body['changes'])
    assert [ch['operation']['value']['amount'] for ch in body['changes'] if ch['operation']['kind']=='set_price']==['71000']
    assert not any('생선' in ch['operation'].get('name','') for ch in body['changes'])
    report=client.get('/api/v1/analysis-runs/'+runid+'/report').json();assert report['events'][0]['ai_original']['amount']=='72000'
    # A later row correction must invalidate the already prepared approval draft.
    prepared_id=body['summary']['id'];values['amount']='70000'
    edited=client.patch(endpoint,json={'version':report['version'],'status':'confirmed','fields':values,'reason':'재대조 후 금액 재정정'},headers={'Idempotency-Key':uid()});assert edited.status_code==200,edited.text
    assert client.get('/api/v1/proposals/'+prepared_id).json()['summary']['status']=='superseded'
    assert post(client,'/proposals/'+prepared_id+'/decisions',{'action':'approve','revision':1},client.get('/api/v1/proposals/'+prepared_id).headers['etag']).status_code==409
    rebuilt=post(client,'/analysis-runs/'+runid+'/review-proposals',{'version':edited.json()['version']});assert rebuilt.status_code==200,rebuilt.text
    p=client.get('/api/v1/proposals/'+rebuilt.json()['proposal_ids'][0]);body=p.json()
    p,tag=approve(client,body,p.headers['etag']);assert apply(client,p,tag)['status']=='succeeded'
    report=client.get('/api/v1/analysis-runs/'+runid+'/report').json()
    locked=client.patch(endpoint,json={'version':report['version'],'status':'confirmed','fields':values,'reason':'변경'},headers={'Idempotency-Key':uid()});assert locked.status_code==409
    assert client.get('/api/v1/products?q=품목%20검토%20테스트%20생선').json()['items']==[]
