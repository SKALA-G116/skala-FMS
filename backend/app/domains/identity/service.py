"""
==============================================================================
FMS_FILE_SPEC
service.py - 세션 인증·로그인과 역할 검사
==============================================================================
설명:
    - 세션 인증·로그인과 역할 검사
입력·출력 명세:
    - 입력: 요청 쿠키·CSRF·로그인 입력·역할 목록
    - 출력: 인증된 사용자·세션 응답 또는 인증 오류
실행 가정:
    - 비밀번호 해시를 검사하고 공개 사용자 정보에서 해시를 제거
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

    2026-10-22  김재현(Finn) v0.1.0   세션 복원·만료·로그아웃 경계와 접근 제어 검증

    상세 Git 이력: git log --follow -- backend/app/domains/identity/service.py
    공통 규칙: doc/file-header-policy.md

기존 모듈 설명:
    Session authentication and role checks shared by domain endpoints.
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

import hashlib
import secrets
from datetime import datetime
from datetime import timezone
from datetime import timedelta
from fastapi import Request
from fastapi.responses import JSONResponse
from argon2 import PasswordHasher
from backend.app.infrastructure.database import Problem
from backend.app.infrastructure.database import get
from backend.app.infrastructure.database import now
import os
from backend.app.infrastructure.database import put
from backend.app.infrastructure.database import records
from backend.app.infrastructure.database import tx
from backend.app.infrastructure.database import uid
from backend.app.infrastructure.contracts import schema_check
from backend.app.api.http import error

PH = PasswordHasher()

SECURE = os.getenv('FOOD_SESSION_SECURE','false').lower() == 'true'

def user(c,req):
    token=req.cookies.get('food_session','');r=c.execute('SELECT user_id,csrf FROM sessions WHERE token_hash=%s AND expires_at>now()',(hashlib.sha256(token.encode()).hexdigest(),)).fetchone()
    if not r:raise Problem(401,'UNAUTHENTICATED','로그인이 필요합니다.')
    return get(c,'user',str(r['user_id'])),r['csrf']

def permit(u,roles):
    if not set(u['roles'])&set(roles):raise Problem(403,'FORBIDDEN','이 작업을 수행할 권한이 없습니다.')

def public_user(u):return {k:v for k,v in u.items() if k!='password_hash'}

def csrf(req:Request):
    token=secrets.token_urlsafe(32)
    with tx() as c:
        try:_,token=user(c,req)
        except Problem:pass
    response=JSONResponse({'csrf_token':token});response.set_cookie('food_csrf',token,httponly=True,secure=SECURE,samesite='lax');return response

def create_session(c, req, payload):
    schema_check('LoginInput',payload)
    c.execute("SELECT pg_advisory_xact_lock(hashtext(%s))",('login:'+payload['username'],))
    lockkey=hashlib.sha256(payload['username'].encode()).hexdigest()
    attempts=c.execute("SELECT data FROM app_records WHERE kind='login_limit' AND data->>'key'=%s",(lockkey,)).fetchone()
    a=attempts['data'] if attempts else {'id':uid(),'key':lockkey,'count':0,'start':now()}
    if (datetime.now(timezone.utc)-datetime.fromisoformat(a['start'].replace('Z','+00:00'))).total_seconds()>300:a['count']=0;a['start']=now()
    if a['count']>=10:raise Problem(429,'LOGIN_RATE_LIMIT','잠시 후 다시 시도하세요.')
    users=records(c,'user');u=next((x for x in users if x['username']==payload['username']),None)
    try:valid=u and PH.verify(u['password_hash'],payload['password'])
    except Exception:valid=False
    if not valid:
        a['count']+=1;put(c,'login_limit',a)
        return error(Problem(401,'LOGIN_FAILED','아이디 또는 비밀번호를 확인하세요.'))
    token=secrets.token_urlsafe(48);cs=secrets.token_urlsafe(32);exp=datetime.now(timezone.utc)+timedelta(hours=8)
    previous=req.cookies.get('food_session')
    if previous:c.execute('DELETE FROM sessions WHERE token_hash=%s',(hashlib.sha256(previous.encode()).hexdigest(),))
    c.execute('INSERT INTO sessions VALUES(%s,%s,%s,%s)',(hashlib.sha256(token.encode()).hexdigest(),u['id'],cs,exp))
    res=JSONResponse({'user':public_user(u),'expires_at':exp.isoformat(),'csrf_token':cs});res.set_cookie('food_session',token,httponly=True,secure=SECURE,samesite='lax');res.set_cookie('food_csrf',cs,httponly=True,secure=SECURE,samesite='lax');return res
