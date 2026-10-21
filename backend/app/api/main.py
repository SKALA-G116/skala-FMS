"""
==============================================================================
FMS_FILE_SPEC
main.py - FastAPI 애플리케이션 조립
==============================================================================
설명:
    - FastAPI 애플리케이션 조립
입력·출력 명세:
    - 입력: 실행 환경·도메인 router·HTTP 요청
    - 출력: ASGI app·정적 화면·health·오류 응답
실행 가정:
    - 수명 관리·보안 미들웨어를 조합하고 업무 처리는 도메인에 위임
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

    상세 Git 이력: git log --follow -- backend/app/api/main.py
    공통 규칙: doc/file-header-policy.md

기존 모듈 설명:
    Application composition root. Domain routers own business endpoints.
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

import asyncio
import logging
from contextlib import asynccontextmanager
import anyio
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from backend.app.infrastructure.database import ROOT
from backend.app.infrastructure.database import Problem
from backend.app.infrastructure.database import init
from backend.app.infrastructure.database import pool
from .http import error
from .registry import DOMAINS

@asynccontextmanager
async def lifespan(app):
    anyio.to_thread.current_default_thread_limiter().total_tokens=8
    app.state.upload_gate=asyncio.Semaphore(2)
    init()
    try:yield
    finally:pool.close()

app=FastAPI(title='식품장부 API', lifespan=lifespan)

@app.exception_handler(Problem)
async def problem_handler(req,e):return error(e)

for domain in DOMAINS:
    app.include_router(domain.router)

@app.api_route('/api/v1/{path:path}',methods=['GET','POST','PATCH','DELETE'],include_in_schema=False)
async def unsupported_api(path:str):
    raise Problem(405,'METHOD_NOT_ALLOWED','지원하지 않는 요청 방식입니다.')

@app.middleware('http')
async def safe_errors(req,call_next):
    try:
        if req.method in ('POST','PATCH','DELETE') and req.headers.get('origin'):
            from urllib.parse import urlparse
            if urlparse(req.headers['origin']).netloc!=req.headers.get('host'):return error(Problem(403,'ORIGIN_INVALID','다른 사이트의 요청은 허용하지 않습니다.'))
        r=await call_next(req)
    except Problem as e:r=error(e)
    except (ValueError,KeyError) as e:r=error(Problem(422,'INVALID_INPUT','입력값을 확인하세요.'))
    except Exception:
        logging.exception('Request failed');r=error(Problem(500,'INTERNAL_ERROR','처리 중 오류가 발생했습니다. 작업 상태를 확인하세요.'))
    r.headers['X-Content-Type-Options']='nosniff';r.headers['Referrer-Policy']='same-origin';r.headers['Cache-Control']='no-store';return r

@app.get('/health')
async def health():return {'status':'ok'}

DIST=ROOT/'frontend/dist'

if DIST.exists():
    app.mount('/assets',StaticFiles(directory=DIST/'assets'),name='frontend-assets')
    @app.get('/{path:path}', include_in_schema=False)
    async def spa(path:str):return FileResponse(DIST/'index.html')
