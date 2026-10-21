"""
==============================================================================
FMS_FILE_SPEC
limits.py - 실행 예산과 중단·메모리 제어
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

    상세 Git 이력: git log --follow -- backend/app/runtime/limits.py
    공통 규칙: doc/file-header-policy.md

기존 모듈 설명:
    Bounded resources shared by HTTP, inference and queue workers.
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

import os
import sys
import resource

def integer(name,default,minimum,maximum):
    try:return min(max(int(os.getenv(name,str(default))),minimum),maximum)
    except ValueError:return default

MODEL_CONCURRENCY=integer('FOOD_MODEL_CONCURRENCY',1,1,2)

MODEL_TIMEOUT=integer('FOOD_MODEL_TIMEOUT_SECONDS',240,10,600)

MODEL_INPUT_BYTES=integer('FOOD_MODEL_INPUT_BYTES',11000,4000,11000)

EXTRACTION_BYTES=integer('FOOD_EXTRACTION_MAX_BYTES',4*1024*1024,65536,8*1024*1024)

REPORT_BYTES=integer('FOOD_REPORT_MAX_BYTES',8*1024*1024,65536,16*1024*1024)

RUN_INPUT_TOKENS=integer('FOOD_RUN_INPUT_TOKENS',500000,1000,1000000)

RUN_OUTPUT_TOKENS=integer('FOOD_RUN_OUTPUT_TOKENS',200000,1000,400000)

ATTEMPT_SECONDS=integer('FOOD_ANALYSIS_SLICE_SECONDS',600,10,1800)

OCR_IDLE_SECONDS=integer('FOOD_OCR_IDLE_SECONDS',60,10,600)

OCR_MAX_REQUESTS=integer('FOOD_OCR_MAX_REQUESTS',20,1,100)

def peak_rss_bytes():
    value=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return value if sys.platform=='darwin' else value*1024
