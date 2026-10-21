"""
==============================================================================
FMS_FILE_SPEC
execution.py - 실행 예산과 중단·메모리 제어
==============================================================================
설명:
    - 실행 예산과 중단·메모리 제어
입력·출력 명세:
    - 입력: 환경 설정·분석 실행 상태·모델 호출 기록
    - 출력: 제한값·실행 경계·재개 신호·메모리/토큰 지표
실행 가정:
    - worker RSS와 별도 Ollama/OCR 메모리를 구분
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

    상세 Git 이력: git log --follow -- backend/app/runtime/execution.py
    공통 규칙: doc/file-header-policy.md
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
