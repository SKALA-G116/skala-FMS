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
