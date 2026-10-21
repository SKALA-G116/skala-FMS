"""Shared HTTP presentation helpers; no domain workflows live here."""
import base64
import json
from dataclasses import dataclass
from dataclasses import field
from fastapi.responses import JSONResponse
from backend.app.infrastructure.database import Problem
from backend.app.infrastructure.database import uid

def error(e):return JSONResponse({'error':{'code':e.code,'message':e.message,'request_id':uid(),'retryable':e.status>=500,'details':e.details}},status_code=e.status)

def etag(obj):return '"'+str(obj.get('summary',obj)['version'])+'"'

def match(req,obj):
    if not req.headers.get('if-match'):raise Problem(428,'PRECONDITION_REQUIRED','화면을 새로 조회한 뒤 다시 시도하세요.')
    if req.headers['if-match']!=etag(obj):raise Problem(412,'STALE_VERSION','다른 변경이 있습니다. 새로고침 후 검토하세요.')

def page(items,q,c):
    limit=min(max(int(q.get('limit','20')),1),100)
    ids=[x.get('id',x.get('summary',{}).get('id')) for x in items]
    stamps={}
    if ids:
        pc=c
        for table,timecol in [('app_records','created_at'),('catalog_entities','created_at'),('facts','recorded_at'),('jobs','created_at')]:
            for r in pc.execute(f'SELECT id,{timecol} stamp FROM {table} WHERE id=ANY(%s::uuid[])',(ids,)):stamps[str(r['id'])]=r['stamp'].isoformat()
    key=lambda x:(stamps.get(x.get('id',x.get('summary',{}).get('id')),''),x.get('id',x.get('summary',{}).get('id','')))
    items=sorted(items,key=key,reverse=True)
    cursor=q.get('cursor');last=None;watermark=list(key(items[0])) if items else ['','']
    if cursor:
        try:watermark,last=json.loads(base64.urlsafe_b64decode(cursor+'='*(-len(cursor)%4)))
        except Exception:raise Problem(422,'INVALID_CURSOR','조회 커서가 올바르지 않습니다.')
    items=[x for x in items if key(x)<=tuple(watermark) and (not last or key(x)<tuple(last))];more=len(items)>limit;items=items[:limit]
    nxt=base64.urlsafe_b64encode(json.dumps([watermark,list(key(items[-1]))]).encode()).decode().rstrip('=') if more else None
    return {'items':items,'next_cursor':nxt,'has_more':more}

def filtered(rows,q):
    query=q.get('q','').casefold()
    return [x for x in rows if (not query or query in json.dumps(x,ensure_ascii=False).casefold()) and (not q.get('status') or x.get('status',x.get('summary',{}).get('status'))==q['status'])]

@dataclass
class DomainResult:
    data: object
    status: int = 200
    headers: dict = field(default_factory=dict)

@dataclass
class RequestContext:
    connection: object
    request: object
    method: str
    query: dict
    payload: dict
    content: bytes | None
    actor: dict
    path: str
    extra_archive: bool = False

    @property
    def parts(self): return self.path.split('/')
    @property
    def root(self): return self.parts[0]
    @property
    def id(self): return self.parts[1] if len(self.parts)>1 else None
    @property
    def action(self): return self.parts[2] if len(self.parts)>2 else None
