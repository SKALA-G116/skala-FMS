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


def test_profile_extraction_avoids_redundant_business_verification():
    from backend.app.domains.analysis.agent import needs_verification
    assert not needs_verification([{'kind':'food_profile'},{'kind':'new_product'}])
    for kind in ('price','temporarily_unavailable','discontinued','available','substitution'):
        assert needs_verification([{'kind':'food_profile'},{'kind':kind}])


def test_report_memory_and_token_budgets_are_enforced(monkeypatch):
    from backend.app.runtime import execution
    from backend.app.infrastructure.database import Problem
    monkeypatch.setattr(execution,'RUN_INPUT_TOKENS',10)
    with pytest.raises(Problem) as exc:execution.report_metrics({'model_calls':[{'input_tokens':11}]})
    assert exc.value.code=='MODEL_RUN_TOKEN_BUDGET'
    monkeypatch.setattr(execution,'REPORT_BYTES',100)
    with pytest.raises(Problem) as exc:execution.report_metrics({'events':['x'*200]})
    assert exc.value.code=='REPORT_MEMORY_BUDGET'
