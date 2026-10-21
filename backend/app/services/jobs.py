"""
==============================================================================
FMS_FILE_SPEC
jobs.py - 기존 모듈 경로 호환 진입점
==============================================================================
설명:
    - 기존 모듈 경로 호환 진입점
입력·출력 명세:
    - 입력: 이전 import 경로 또는 공개 호출
    - 출력: canonical 도메인 모듈과 공개 인터페이스
실행 가정:
    - 새 업무 로직을 이 호환 계층에 추가하지 않음
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

    상세 Git 이력: git log --follow -- backend/app/services/jobs.py
    공통 규칙: doc/file-header-policy.md

기존 모듈 설명:
    Compatibility entry point; new code uses domains.jobs.service.
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

import importlib
import sys
module = importlib.import_module("backend.app.domains.jobs.service")
sys.modules[__name__] = module
