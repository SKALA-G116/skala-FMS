"""
==============================================================================
FMS_FILE_SPEC
api.py - identity 도메인 HTTP 유스케이스
==============================================================================
설명:
    - identity 도메인 HTTP 유스케이스
입력·출력 명세:
    - 입력: 인증·권한·CSRF를 확인한 RequestContext와 경로/조회/본문
    - 출력: DomainResult 또는 HTTP Response
실행 가정:
    - 공통 transport가 소유한 같은 DB 트랜잭션을 사용
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

    상세 Git 이력: git log --follow -- backend/app/domains/identity/api.py
    공통 규칙: doc/file-header-policy.md

기존 모듈 설명:
    Authenticated session reads and logout; login/CSRF are pre-auth transport hooks.
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

import hashlib
from fastapi.responses import Response
from backend.app.api.http import DomainResult
from backend.app.domains.identity.service import public_user
from backend.app.api.routing import domain_router

def handle(ctx):
    if ctx.path == 'auth/me':
        return DomainResult(public_user(ctx.actor))
    ctx.connection.execute('DELETE FROM sessions WHERE token_hash=%s', (hashlib.sha256(ctx.request.cookies['food_session'].encode()).hexdigest(),))
    response = Response(status_code=204)
    response.delete_cookie('food_session')
    response.delete_cookie('food_csrf')
    return response

ROUTES = (('auth/csrf', ('GET',)), ('auth/session', ('DELETE', 'POST')), ('auth/me', ('GET',)))

router = domain_router('identity', ROUTES)
