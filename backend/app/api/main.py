"""Application composition root. Domain routers own business endpoints."""
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
