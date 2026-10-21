"""
==============================================================================
FMS_FILE_SPEC
database.py - PostgreSQL 연결·저장 공통 함수
==============================================================================
설명:
    - PostgreSQL 연결·저장 공통 함수
입력·출력 명세:
    - 입력: DATABASE_URL·connection·레코드 종류/ID·저장 객체
    - 출력: 트랜잭션·관계형/JSONB 레코드와 공통 오류
실행 가정:
    - 연결 풀을 제한하고 명시적 트랜잭션에서 데이터 접근
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

    상세 Git 이력: git log --follow -- backend/app/infrastructure/database.py
    공통 규칙: doc/file-header-policy.md
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
import uuid
from pathlib import Path
from datetime import datetime
from datetime import timezone
from zoneinfo import ZoneInfo
from contextlib import contextmanager
from psycopg_pool import ConnectionPool
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[3]

load_dotenv(ROOT/'.env.food',override=False)

DSN = os.getenv('DATABASE_URL', 'postgresql://localhost:55432/food_agent')

pool = ConnectionPool(DSN, min_size=1, max_size=6, open=False, kwargs={'row_factory':dict_row}, timeout=8)

def uid(): return str(uuid.uuid4())

def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')

def today(): return datetime.now(ZoneInfo('Asia/Seoul')).date().isoformat()

def init():
    pool.open(); pool.wait()
    with pool.connection() as c:
        for migration in sorted((ROOT/'migrations').glob('*.sql')):c.execute(migration.read_text())

@contextmanager
def tx():
    with pool.connection() as c:
        with c.transaction(): yield c

def get(c, kind, id, lock=False):
    r=c.execute('SELECT data FROM app_records WHERE kind=%s AND id=%s'+(' FOR UPDATE' if lock else ''),(kind,id)).fetchone()
    if not r: raise Problem(404,'NOT_FOUND','요청한 정보를 찾을 수 없습니다.')
    return r['data']

def put(c, kind, obj):
    c.execute('INSERT INTO app_records(kind,id,data) VALUES(%s,%s,%s) ON CONFLICT(kind,id) DO UPDATE SET data=excluded.data',(kind,obj.get('id') or obj['summary']['id'],Jsonb(obj)))
    return obj

def records(c,kind):
    rows=c.execute('SELECT data FROM app_records WHERE kind=%s ORDER BY created_at DESC,id DESC LIMIT 2001',(kind,)).fetchall()
    if len(rows)>2000:raise Problem(422,'DATASET_LIMIT','개발 버전의 조회 상한을 넘었습니다. 운영용 DB 검색·페이지 쿼리로 전환하세요.')
    return [r['data'] for r in rows]

def entity(c,id,lock=False):
    r=c.execute('SELECT * FROM catalog_entities WHERE id=%s'+(' FOR UPDATE' if lock else ''),(id,)).fetchone()
    if not r: raise Problem(422,'TARGET_NOT_FOUND','연결한 상품·규격이 없습니다.')
    return {**r['data'],'id':str(r['id']),'version':r['version']}

def entities(c,kind):
    rows=c.execute('SELECT data,id,version FROM catalog_entities WHERE kind=%s ORDER BY created_at DESC,id DESC LIMIT 2001',(kind,)).fetchall()
    if len(rows)>2000:raise Problem(422,'DATASET_LIMIT','개발 버전의 상품 조회 상한을 넘었습니다.')
    return [{**r['data'],'id':str(r['id']),'version':r['version']} for r in rows]

def save_entity(c,kind,obj,parent=None,supplier=None):
    c.execute('INSERT INTO catalog_entities(id,kind,parent_id,supplier_id,name,version,data) VALUES(%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(id) DO UPDATE SET version=excluded.version,data=excluded.data', (obj['id'],kind,parent,supplier,obj.get('name'),obj['version'],Jsonb(obj)))
    return obj

class Problem(Exception):
    def __init__(self,status,code,message,details=None): self.status=status; self.code=code; self.message=message; self.details=details
