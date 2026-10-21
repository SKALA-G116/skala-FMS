"""Register an authorized local source for viewing; never applies business prices."""
import argparse,sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.app.infrastructure.database import init,tx,pool
from backend.app.domains.pricing.workbooks import import_workbook,metadata
import hashlib

def main():
    parser=argparse.ArgumentParser();parser.add_argument('path');a=parser.parse_args();p=Path(a.path)
    if p.stat().st_size>20*1024*1024:raise SystemExit('파일은 20MB까지 지원합니다.')
    content=p.read_bytes();digest=hashlib.sha256(content).hexdigest();init()
    try:
        with tx() as c:
            old=c.execute('SELECT id FROM price_workbooks WHERE content_sha256=%s ORDER BY created_at LIMIT 1',(digest,)).fetchone()
            result=metadata(c,str(old['id'])) if old else import_workbook(c,p.stem,content,p.name)
            print(json.dumps({'id':result['id'],'sheets':[{'name':s['name'],'row_count':s['row_count'],'columns':len(s['columns'])} for s in result['sheets']]},ensure_ascii=False))
    finally:pool.close()
if __name__=='__main__':main()
