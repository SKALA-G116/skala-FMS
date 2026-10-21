"""
==============================================================================
FMS_FILE_SPEC
routing.py - 명시적 FastAPI 도메인 라우터 생성
==============================================================================
설명:
    - 명시적 FastAPI 도메인 라우터 생성
입력·출력 명세:
    - 입력: 도메인명·경로·HTTP method 목록
    - 출력: 고유 operation ID와 path parameter를 갖는 APIRouter
실행 가정:
    - 실제 요청 처리는 공통 transport에 위임
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

    상세 Git 이력: git log --follow -- backend/app/api/routing.py
    공통 규칙: doc/file-header-policy.md

기존 모듈 설명:
    Create explicit domain paths with unique operations and documented path parameters.
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

import re
from fastapi import APIRouter, Request


def domain_router(domain, routes):
    router = APIRouter(prefix='/api/v1', tags=[domain])
    for path, methods in routes:
        parameters = [
            {'name': name, 'in': 'path', 'required': True, 'schema': {'type': 'string'}}
            for name in re.findall(r'\{([^}]+)\}', path)
        ]
        for method in methods:
            async def endpoint(req: Request):
                from .transport import process_request
                return await process_request(req.url.path.removeprefix('/api/v1/'), req)

            operation = domain + '_' + method.lower() + '_' + re.sub(r'[^a-zA-Z0-9_]', '_', path)
            endpoint.__name__ = operation
            router.add_api_route(
                '/' + path, endpoint, methods=[method], operation_id=operation,
                openapi_extra={'parameters': parameters},
            )
    return router
