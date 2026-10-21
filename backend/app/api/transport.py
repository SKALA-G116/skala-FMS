"""
==============================================================================
FMS_FILE_SPEC
transport.py - 공통 HTTP 보안·트랜잭션 경계
==============================================================================
설명:
    - 공통 HTTP 보안·트랜잭션 경계
입력·출력 명세:
    - 입력: Request·파일 또는 JSON payload
    - 출력: 인증/권한 검사 후 도메인 응답과 중복 요청 결과
실행 가정:
    - 업로드 크기·동시성·CSRF·Idempotency-Key를 검사
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

    2026-10-21  미지정      v0.1.0   원본 속성 누락 복구·재정리 API·검토 동선 개선

    2026-10-21  김재현(Finn) v0.1.0   Agent 도구 선택 기반 리빌드·업무 경계 및 검증

    상세 Git 이력: git log --follow -- backend/app/api/transport.py
    공통 규칙: doc/file-header-policy.md

기존 모듈 설명:
    HTTP guards, bounded body ingestion and transaction/idempotency boundary.
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

import re
import json
import hashlib
import hmac
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.responses import Response
from starlette.background import BackgroundTask
from starlette.concurrency import run_in_threadpool
from psycopg.types.json import Jsonb
from backend.app.infrastructure.database import Problem
from backend.app.infrastructure.database import tx
from backend.app.domains.identity.service import user
from backend.app.domains.identity.service import permit
from backend.app.domains.identity.service import csrf
from backend.app.domains.identity.service import create_session
from backend.app.api.http import RequestContext

async def process_request(path:str,req:Request):
    if path=='auth/csrf':return await run_in_threadpool(csrf,req)
    method=req.method;mutating=method!='GET';q=dict(req.query_params);payload={};status=200;headers={}
    extra_archive=bool(re.fullmatch(r'(foods|documents)/[^/]+(?:/restore)?',path)) and ((method=='DELETE' and not path.endswith('/restore')) or (method=='POST' and path.endswith('/restore')))
    if mutating and int(req.headers.get('content-length','0'))>21*1024*1024:raise Problem(413,'REQUEST_TOO_LARGE','요청 크기가 너무 큽니다.')
    if mutating:
        token=req.headers.get('x-csrf-token','')
        if not token or not hmac.compare_digest(token,req.cookies.get('food_csrf','')):raise Problem(403,'CSRF_INVALID','보안 토큰이 만료되었습니다. 새로고침해 주세요.')
        if 'multipart/form-data' not in req.headers.get('content-type',''):
            try:payload=await req.json() if await req.body() else {}
            except ValueError:raise Problem(422,'INVALID_JSON','JSON 형식이 올바르지 않습니다.')
    if mutating and 'multipart/form-data' in req.headers.get('content-type',''):
        async with req.app.state.upload_gate:
            async with req.form() as form:
                upload=form.get('file')
                if not upload:raise Problem(422,'FILE_REQUIRED','파일을 선택하세요.')
                content=await upload.read(20*1024*1024+1)
                if len(content)>20*1024*1024:raise Problem(413,'FILE_TOO_LARGE','파일은 20MB까지 지원합니다.')
                payload={'title':str(form.get('title') or upload.filename),'filename':upload.filename,'sha256':hashlib.sha256(content).hexdigest()}
            return await run_in_threadpool(dispatch_request,path,req,method,mutating,q,payload,content,extra_archive)
    return await run_in_threadpool(dispatch_request,path,req,method,mutating,q,payload,None,extra_archive)

def dispatch_request(path,req,method,mutating,q,payload,content,extra_archive):
    with tx() as c:
        if path=='auth/session' and method=='POST':
            return create_session(c,req,payload)
        u,cs=user(c,req)
        if mutating and not hmac.compare_digest(req.headers['x-csrf-token'],cs):raise Problem(403,'CSRF_INVALID','보안 토큰을 갱신하세요.')
        if path=='auth/session' and method=='DELETE':
            from backend.app.domains.identity.api import handle
            return handle(RequestContext(c,req,method,q,payload,content,u,path))
        if mutating:
            roles=['admin','reviewer'] if path.startswith('proposals') or path.endswith('/proposals') or path.endswith('/header') else ['admin','operator']
            if path.startswith('analysis-runs/') and ('/items/' in path or path.endswith('/review-proposals') or path.endswith('/review-export') or path.endswith('/normalize')):roles=['admin','reviewer']
            if extra_archive:roles=['admin','reviewer'] if path.startswith('foods/') else ['admin','operator']
            if path=='suppliers':roles=['admin','operator','reviewer']
            if path.startswith('sources'):roles=['admin']
            permit(u,roles)
            key=req.headers.get('idempotency-key')
            if not key or len(key)>200:raise Problem(428,'IDEMPOTENCY_REQUIRED','요청 식별 키가 필요합니다.')
            scope=f"{u['id']}:{method}:{path}:{key}"
            digest=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()
            if '/connection' in path:
                from backend.app.domains.ingestion.connections import command_fingerprint
                digest=command_fingerprint(payload)
            c.execute('SELECT pg_advisory_xact_lock(hashtext(%s))',(scope,))
            old=c.execute('SELECT * FROM command_keys WHERE scope=%s',(scope,)).fetchone()
            if old:
                if old['body_hash']!=digest:raise Problem(409,'IDEMPOTENCY_CONFLICT','같은 키로 다른 요청을 보낼 수 없습니다.')
                return JSONResponse(old['response']['body'],status_code=old['status'],headers=old['response'].get('headers',{}))

        from backend.app.api.registry import handler_for
        ctx = RequestContext(c, req, method, q, payload, content, u, path, extra_archive)
        result = handler_for(ctx.root)(ctx)
        if isinstance(result, Response):
            return result
        out, status, headers = result.data, result.status, result.headers
        if mutating:
            c.execute('INSERT INTO command_keys(scope,body_hash,status,response) VALUES(%s,%s,%s,%s)', (scope,digest,status,Jsonb({'body':out,'headers':headers})))
        response=JSONResponse(out,status_code=status,headers=headers)
        if path=='document-actions' and payload.get('action')=='purge' and out.get('succeeded'):
            from backend.app.domains.ingestion.purge import cleanup_files
            response.background=BackgroundTask(cleanup_files)
        return response
