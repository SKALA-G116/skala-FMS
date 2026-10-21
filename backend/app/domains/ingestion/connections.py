"""
==============================================================================
FMS_FILE_SPEC
connections.py - 사이트 연결 정보의 암호화 보관
==============================================================================
설명:
    - 사이트 연결 정보의 암호화 보관
입력·출력 명세:
    - 입력: source ID·사용자가 입력한 회원 연결 설정
    - 출력: 암호화 저장 정보 또는 비밀을 제거한 공개 상태
실행 가정:
    - 실제 계정과 암호화 키를 Git·응답·로그에 노출하지 않음
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

    상세 Git 이력: git log --follow -- backend/app/domains/ingestion/connections.py
    공통 규칙: doc/file-header-policy.md

기존 모듈 설명:
    Source credentials/cookies encrypted at rest; API never returns secrets.
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
import json
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.fernet import InvalidToken
from backend.app.infrastructure.database import Problem
from backend.app.infrastructure.database import ROOT

def key_material():
    key=os.getenv('FOOD_CREDENTIAL_KEY')
    if not key:
        path=Path(os.getenv('FOOD_CREDENTIAL_KEY_FILE',str(ROOT/'.local/credential.key')))
        path.parent.mkdir(parents=True,exist_ok=True)
        try:
            fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
            with os.fdopen(fd,'wb') as f:f.write(Fernet.generate_key())
        except FileExistsError:pass
        if path.stat().st_mode & 0o077:raise Problem(503,'KEY_PERMISSIONS','연결 정보 암호화 키의 접근 권한을 확인하세요.')
        key=path.read_bytes()
    return key.encode() if isinstance(key,str) else key

def cipher():
    try:return Fernet(key_material())
    except Exception:raise Problem(503,'KEY_INVALID','연결 정보 암호화 키를 확인하세요.')

def config(c,source_id):
    r=c.execute('SELECT encrypted_config FROM source_connections WHERE source_id=%s',(source_id,)).fetchone()
    if not r:return None
    try:return json.loads(cipher().decrypt(r['encrypted_config'].encode()))
    except (InvalidToken,ValueError):raise Problem(503,'KEY_UNAVAILABLE','연결 정보를 복호화할 수 없습니다. 이전 키를 복원하거나 연결을 다시 설정하세요.')

def write(c,source_id,value,state='saved'):
    encrypted=cipher().encrypt(json.dumps(value).encode()).decode()
    c.execute('INSERT INTO source_connections(source_id,encrypted_config,state) VALUES(%s,%s,%s) ON CONFLICT(source_id) DO UPDATE SET encrypted_config=excluded.encrypted_config,state=excluded.state,updated_at=now()',(source_id,encrypted,state))

def public(c,source_id):
    r=c.execute('SELECT state,last_checked_at,updated_at FROM source_connections WHERE source_id=%s',(source_id,)).fetchone()
    cfg=config(c,source_id) if r else None
    return {'configured':bool(cfg),'username':cfg.get('username') if cfg else None,'auto_login':cfg.get('auto_login',True) if cfg else True,'state':r['state'] if r else 'not_configured','last_checked_at':r['last_checked_at'].isoformat() if r and r['last_checked_at'] else None,'password_stored':bool(cfg and cfg.get('password'))}

def save(c,source_id,payload):
    username=payload.get('username','');password=payload.get('password','')
    if not isinstance(username,str):raise Problem(422,'ACCOUNT_INPUT','회원 아이디를 확인하세요.')
    username=username.strip()
    if not isinstance(username,str) or not 1<=len(username)<=100 or not isinstance(password,str) or len(password)>500:raise Problem(422,'ACCOUNT_INPUT','회원 아이디와 비밀번호를 확인하세요.')
    old=config(c,source_id)
    if not password and old and old['username']==username:password=old['password']
    if not password:raise Problem(422,'PASSWORD_REQUIRED','처음 연결할 때 비밀번호를 입력하세요.')
    write(c,source_id,{'username':username,'password':password,'auto_login':bool(payload.get('auto_login',True)),'cookies':[]})
    return public(c,source_id)

def command_fingerprint(payload):
    import hmac,hashlib
    return hmac.new(key_material(),json.dumps(payload,sort_keys=True).encode(),hashlib.sha256).hexdigest()
