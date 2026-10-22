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

    상세 Git 이력: git log --follow -- backend/app/infrastructure/contracts.py
    공통 규칙: doc/file-header-policy.md

기존 모듈 설명:
    Versioned JSON contracts shared by HTTP, MCP and application services.
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

import json
from itertools import islice
from jsonschema import Draft202012Validator
from jsonschema import FormatChecker
from backend.app.infrastructure.database import ROOT
from backend.app.infrastructure.database import Problem

SPEC=json.loads((ROOT/'doc/food-agent/openapi.json').read_text())

def schema_check(name,data):
    schema={'$ref':f'#/components/schemas/{name}','components':SPEC['components']}
    errors=list(islice(Draft202012Validator(schema,format_checker=FormatChecker()).iter_errors(data),10))
    messages={'maxItems':'항목 수가 허용 범위를 초과했습니다.','minItems':'필요한 항목이 비어 있습니다.',
        'maxLength':'입력 내용이 허용 길이를 초과했습니다.','required':'필수 항목이 빠졌습니다.',
        'uniqueItems':'중복된 항목이 있습니다.','format':'값의 형식을 확인해 주세요.',
        'type':'값의 자료형을 확인해 주세요.','enum':'허용된 값 중에서 선택해 주세요.',
        'additionalProperties':'지원하지 않는 항목이 있습니다.'}
    if errors: raise Problem(422,'INVALID_INPUT','입력값의 형식이 올바르지 않습니다.',[{'path':'/'.join(map(str,e.absolute_path))[:200], 'message':messages.get(e.validator,'입력 형식을 확인해 주세요.')} for e in errors])
