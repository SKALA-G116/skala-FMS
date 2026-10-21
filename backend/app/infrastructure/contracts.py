"""
==============================================================================
FMS_FILE_SPEC
contracts.py - 프로젝트 설정 contracts.py
==============================================================================
설명:
    - 프로젝트 설정 contracts.py
입력·출력 명세:
    - 입력: 도구별 설정·실행 환경
    - 출력: 해당 도구의 구성 또는 실행 결과
실행 가정:
    - 실제 비밀값과 로컬 실행 데이터는 Git에서 제외
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

    상세 Git 이력: git log --follow -- backend/app/infrastructure/contracts.py
    공통 규칙: doc/file-header-policy.md

기존 모듈 설명:
    Versioned JSON contracts shared by HTTP, MCP and application services.
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

import json
from jsonschema import Draft202012Validator
from jsonschema import FormatChecker
from backend.app.infrastructure.database import ROOT
from backend.app.infrastructure.database import Problem

SPEC=json.loads((ROOT/'doc/food-agent/openapi.json').read_text())

def schema_check(name,data):
    schema={'$ref':f'#/components/schemas/{name}','components':SPEC['components']}
    errors=list(Draft202012Validator(schema,format_checker=FormatChecker()).iter_errors(data))
    if errors: raise Problem(422,'INVALID_INPUT','입력값의 형식이 올바르지 않습니다.',[{'path':'/'.join(map(str,e.absolute_path)), 'message':e.message} for e in errors[:10]])
