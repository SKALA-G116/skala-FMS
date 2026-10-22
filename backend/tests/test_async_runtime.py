"""
==============================================================================
FMS_FILE_SPEC
test_async_runtime.py - 기능·경계·회귀 검증
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

    2026-10-21  김재현(Finn) v0.1.0   Agent 도구 선택 기반 리빌드·업무 경계 및 검증

    2026-10-22  김재현(Finn) v0.1.0   모델 생성 스키마·원본 검증·HTTP 오류 분류 회귀 검증

    2026-10-22  김재현(Finn) v0.1.0   OCR 정상 종료·native 충돌 격리 및 재시작 검증

    2026-10-22  김재현(Finn) v0.1.0   라벨 응답 축소·형식 오류 격리·안전한 진단 및 부분 완료 검수

    상세 Git 이력: git log --follow -- backend/tests/test_async_runtime.py
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
import asyncio,json,sys,time,threading
import httpx,pytest
from backend.app.domains.analysis import provider
from backend.app.parsers.ocr_pool import OCRProcess


def test_async_model_does_not_block_event_loop_and_reuses_client(monkeypatch):
    original=httpx.AsyncClient;active=0;peak=0;created=0
    async def handler(request):
        nonlocal active,peak
        active+=1;peak=max(peak,active)
        try:
            await asyncio.sleep(.1)
            return httpx.Response(200,json={'message':{'content':'{"value":1}'},'prompt_eval_count':2,'eval_count':3})
        finally:active-=1
    def factory(**kwargs):
        nonlocal created
        created+=1;return original(transport=httpx.MockTransport(handler),**kwargs)
    monkeypatch.setattr(httpx,'AsyncClient',factory);monkeypatch.setattr(provider,'_GATE',threading.BoundedSemaphore(1))
    async def run():
        ticks=0;model=provider.LocalModel();schema={'type':'object','properties':{'value':{'type':'integer'}},'required':['value']}
        async def tick():
            nonlocal ticks
            for _ in range(8):await asyncio.sleep(.02);ticks+=1
        try:
            result=await asyncio.gather(model.agenerate('test',{},schema),model.agenerate('test',{},schema),tick())
            assert result[:2]==[{'value':1},{'value':1}] and ticks==8
            assert len(model.calls)==2 and model.calls[1]['queue_seconds']>0
        finally:await model.aclose()
    asyncio.run(run());assert peak==1 and created==1


def test_async_model_can_run_bounded_parallel_requests(monkeypatch):
    original=httpx.AsyncClient;active=0;peak=0
    async def handler(request):
        nonlocal active,peak
        active+=1;peak=max(peak,active)
        try:
            await asyncio.sleep(.05);return httpx.Response(200,json={'message':{'content':'{}'}})
        finally:active-=1
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kwargs:original(transport=httpx.MockTransport(handler),**kwargs));monkeypatch.setattr(provider,'_GATE',threading.BoundedSemaphore(2))
    async def run():
        model=provider.LocalModel()
        try:await asyncio.gather(*(model.agenerate('test',{}, {'type':'object'}) for _ in range(3)))
        finally:await model.aclose()
    asyncio.run(run());assert peak==2


def test_ocr_process_reuses_model_process_and_releases_idle_memory(monkeypatch):
    script="import sys,json,os\nfor line in sys.stdin:\n print(json.dumps({'ok':True,'rows':[{'pid':os.getpid()}]}),flush=True)"
    worker=OCRProcess([sys.executable,'-u','-c',script])
    try:
        first=worker.request('fake')[0]['pid'];second=worker.request('fake')[0]['pid'];assert first==second
        worker.last_used=0;worker.expire_idle();assert worker.process is None
        assert worker.request('fake')[0]['pid']!=first
    finally:worker.close()


def test_ocr_timeout_stops_process_and_clears_resources():
    worker=OCRProcess([sys.executable,'-u','-c','import sys,time\nfor line in sys.stdin: time.sleep(5)'])
    from backend.app.infrastructure.database import Problem
    try:
        with pytest.raises(Problem) as exc:worker.request('fake',timeout=.05)
        assert exc.value.code=='OCR_TIMEOUT' and worker.process is None
    finally:worker.close()


def test_ocr_idle_close_uses_shutdown_protocol_without_sigterm():
    script="import sys,json,signal,os\nsignal.signal(signal.SIGTERM,lambda *_:os._exit(47))\nfor line in sys.stdin:\n if json.loads(line).get('shutdown'): sys.exit(0)\n print(json.dumps({'ok':True,'rows':[]}),flush=True)"
    worker=OCRProcess([sys.executable,'-u','-c',script])
    try:
        worker.request('fake');process=worker.process;worker.close()
        assert process.returncode==0 and worker.responses is None
    finally:worker.close()


def test_ocr_unexpected_exit_is_distinct_and_next_request_can_recover():
    from backend.app.infrastructure.database import Problem
    worker=OCRProcess([sys.executable,'-u','-c','import os;os._exit(23)'])
    try:
        with pytest.raises(Problem) as exc:worker.request('fake')
        assert exc.value.code=='OCR_PROCESS_EXIT' and exc.value.details==[{'exit_code':23}]
        assert worker.process is None and worker.responses is None
        worker.command=[sys.executable,'-u','-c',"import sys,json\nfor line in sys.stdin:\n if json.loads(line).get('shutdown'):break\n print(json.dumps({'ok':True,'rows':[]}),flush=True)"]
        assert worker.request('fake')==[]
    finally:worker.close()


def test_ocr_engine_owns_signal_handling_and_limits_cpu_threads(monkeypatch):
    import types
    from backend.app.parsers import ocr
    calls=[]
    monkeypatch.setitem(sys.modules,'paddle',types.SimpleNamespace(disable_signal_handler=lambda:calls.append('disable')))
    monkeypatch.setitem(sys.modules,'paddleocr',types.SimpleNamespace(PaddleOCR=lambda **kw:calls.append(kw)))
    ocr.engine()
    assert calls[0]=='disable'
    assert calls[1]['cpu_threads']==2 and calls[1]['device']=='cpu' and calls[1]['enable_mkldnn'] is False


def test_agent_does_not_have_a_redundant_verification_pass():
    from backend.app.domains.analysis import agent
    assert not hasattr(agent,'needs_verification')


def test_report_memory_and_token_budgets_are_enforced(monkeypatch):
    from backend.app.runtime import execution
    from backend.app.infrastructure.database import Problem
    monkeypatch.setattr(execution,'RUN_INPUT_TOKENS',10)
    with pytest.raises(Problem) as exc:execution.report_metrics({'model_calls':[{'input_tokens':11}]})
    assert exc.value.code=='MODEL_RUN_TOKEN_BUDGET'
    monkeypatch.setattr(execution,'REPORT_BYTES',100)
    with pytest.raises(Problem) as exc:execution.report_metrics({'events':['x'*200]})
    assert exc.value.code=='REPORT_MEMORY_BUDGET'


def test_planner_model_can_be_small_and_unloads_before_heavier_extraction(monkeypatch):
    from backend.app.domains.analysis.provider import LocalModel
    monkeypatch.setenv('FOOD_PLANNER_MODEL_NAME','small-planner')
    monkeypatch.setenv('FOOD_EXTRACTION_MODEL_NAME','larger-extractor')
    model=LocalModel();model.use_role('planner')
    planning=model.request('choose',{}, {'type':'object'})
    assert planning['model']=='small-planner' and planning['keep_alive']=='0'
    model.use_role('extractor');extraction=model.request('extract',{}, {'type':'object'})
    assert extraction['model']=='larger-extractor'
    assert planning['options']['num_ctx']<extraction['options']['num_ctx']


def test_generation_grammar_keeps_response_bounds_and_source_validation():
    from backend.app.domains.analysis.planning import layout_schema
    from backend.app.infrastructure.database import Problem
    from jsonschema import Draft202012Validator
    schema=layout_schema([str(i) for i in range(1,42)])
    model=provider.LocalModel();request=model.request('layout',{},schema)
    region=request['format']['properties']['regions']
    assert 'maxItems' not in region
    assert 'maxItems' not in region['items']['properties']['source_ids']
    assert region['items']['properties']['source_ids']['items']['enum']==[str(i) for i in range(1,42)]
    assert schema['properties']['regions']['maxItems']==40
    Draft202012Validator.check_schema(request['format'])
    bad={'regions':[{'label':'x','source_ids':['1'],'context_ids':[]}]*41,'unassigned_ids':[]}
    response=httpx.Response(200,json={'message':{'content':json.dumps(bad)}},request=httpx.Request('POST','http://model/api/chat'))
    with pytest.raises(Problem) as error:model.decode(response,'layout',schema,time.monotonic(),0)
    assert error.value.code=='MODEL_SCHEMA_INVALID'


@pytest.mark.parametrize('status,code',[(400,'MODEL_REQUEST_REJECTED'),(404,'MODEL_NOT_INSTALLED'),(503,'MODEL_UNAVAILABLE')])
@pytest.mark.parametrize('asynchronous',[False,True])
def test_provider_status_errors_are_not_reported_as_connection_failures(monkeypatch,status,code,asynchronous):
    from backend.app.infrastructure.database import Problem
    transport=httpx.MockTransport(lambda request:httpx.Response(status,json={'error':'private source content'}))
    sync=httpx.Client;async_client=httpx.AsyncClient
    monkeypatch.setattr(httpx,'Client',lambda **kwargs:sync(transport=transport,**kwargs))
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kwargs:async_client(transport=transport,**kwargs))
    model=provider.LocalModel()
    async def run():
        try:return await model.agenerate('test',{}, {'type':'object'})
        finally:await model.aclose()
    with pytest.raises(Problem) as error:
        asyncio.run(run()) if asynchronous else model.generate('test',{}, {'type':'object'})
    assert error.value.code==code
    assert error.value.details=={'provider_status':status}
    assert 'private' not in error.value.message


def test_provider_timeout_and_connection_error_are_distinct():
    request=httpx.Request('POST','http://model/api/chat')
    assert provider.model_error(httpx.ReadTimeout('private',request=request)).code=='MODEL_TIMEOUT'
    assert provider.model_error(httpx.ConnectError('private',request=request)).code=='MODEL_UNAVAILABLE'


@pytest.mark.parametrize('content,keyword',[
    ('{"values":["a","b"]}','maxItems'),
    ('{"values":["INVENTED_PRIVATE_VALUE"]}','enum'),
    ('not valid JSON PRIVATE_SOURCE_TEXT','json'),
])
def test_model_validation_diagnostics_do_not_expose_raw_output(content,keyword):
    schema={'type':'object','properties':{'values':{'type':'array','maxItems':1,'items':{'enum':['a','b']}}},'required':['values'],'additionalProperties':False}
    model=provider.LocalModel();request=model.request('bounded',{},schema)
    assert request['format']['properties']['values']['maxItems']==1
    response=httpx.Response(200,json={'message':{'content':content},'eval_count':9},request=httpx.Request('POST','http://model/api/chat'))
    with pytest.raises(provider.Problem) as error:model.decode(response,'bounded',schema,time.monotonic(),0)
    assert error.value.code=='MODEL_SCHEMA_INVALID' and error.value.details['validation']['keyword']==keyword
    assert model.calls[0]['outcome']=='invalid' and model.calls[0]['output_tokens']==9
    assert 'PRIVATE' not in json.dumps(error.value.details) and 'PRIVATE' not in json.dumps(model.calls)
    assert error.value.__suppress_context__
