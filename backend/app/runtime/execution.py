import time
import json
import threading
from contextvars import ContextVar
from backend.app.infrastructure.database import Problem
from backend.app.runtime.limits import ATTEMPT_SECONDS
from backend.app.runtime.limits import REPORT_BYTES
from backend.app.runtime.limits import RUN_INPUT_TOKENS
from backend.app.runtime.limits import RUN_OUTPUT_TOKENS
from backend.app.runtime.limits import peak_rss_bytes

STOP_REQUESTED=threading.Event()

ATTEMPT_START=ContextVar('analysis_attempt_start',default=None)

class AnalysisYield(Exception):
    """Yield a long document at a persisted batch boundary; queued continuation resumes it."""

def boundary():
    start=ATTEMPT_START.get()
    if STOP_REQUESTED.is_set():raise AnalysisYield()
    if start is not None and time.monotonic()-start>=ATTEMPT_SECONDS:raise AnalysisYield()

def report_metrics(report):
    calls=report.get('model_calls',[])
    metrics={'input_tokens':sum(c.get('input_tokens',0) for c in calls),'output_tokens':sum(c.get('output_tokens',0) for c in calls),'model_seconds':round(sum(c.get('elapsed_seconds',0) for c in calls),3),'peak_worker_rss_bytes':peak_rss_bytes(),'execution':'async_http_bounded','model_calls':len(calls)}
    if metrics['input_tokens']>RUN_INPUT_TOKENS or metrics['output_tokens']>RUN_OUTPUT_TOKENS:raise Problem(422,'MODEL_RUN_TOKEN_BUDGET','이 자료의 전체 AI 처리 예산을 초과했습니다. 자료를 나눠 분석해 주세요.')
    report['performance']=metrics
    if len(json.dumps(report,ensure_ascii=False).encode())>REPORT_BYTES:raise Problem(422,'REPORT_MEMORY_BUDGET','분석 결과의 메모리 예산을 초과했습니다. 자료를 나눠 주세요.')
    return metrics
