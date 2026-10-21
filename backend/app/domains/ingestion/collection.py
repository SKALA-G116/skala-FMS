"""Resumable incremental collection with short DB transactions, per-post commit,
revisit of recent known posts, immutable revisions and durable analysis handoff."""
import hashlib
import json
from datetime import datetime
from datetime import timezone
from backend.app.infrastructure.database import Problem
from backend.app.infrastructure.database import get
from backend.app.infrastructure.database import now
from backend.app.infrastructure.database import put
from backend.app.infrastructure.database import records
from backend.app.infrastructure.database import tx
from backend.app.infrastructure.database import uid
from backend.app.connectors.school062 import SiteClient
from backend.app.domains.ingestion.connections import config
from backend.app.domains.ingestion.connections import write
from backend.app.domains.ingestion.documents import DATA
from backend.app.domains.jobs.service import enqueue
from backend.app.domains.analysis.service import queue_analysis

BOARDS=['product_01','product_02','product_del']

def store_asset(c,content,name,mime=None,url=None):
    import mimetypes
    digest=hashlib.sha256(content).hexdigest();c.execute('SELECT pg_advisory_xact_lock(hashtext(%s))',('asset:'+digest,));path=DATA/digest
    if not path.exists():path.write_bytes(content)
    a={'id':uid(),'filename':name,'content_type':mime or mimetypes.guess_type(name)[0] or 'application/octet-stream','size_bytes':len(content),'sha256':digest,'access_status':'available','source_url':url}
    put(c,'asset',{**a,'storage_key':digest});return a

def ingest(c,source_id,post):
    identity=(str(source_id),post['board'],post['post'])
    c.execute('SELECT pg_advisory_xact_lock(hashtext(%s))',(':'.join(identity),))
    if c.execute('SELECT 1 FROM purged_source_posts WHERE source_id=%s AND board_key=%s AND external_post_id=%s',identity).fetchone():return None,'deleted'
    previous=c.execute("SELECT data FROM app_records WHERE kind='document' AND data->>'source_id'=%s AND data->>'board_key'=%s AND data->>'external_post_id'=%s",identity).fetchone()
    old=previous['data'] if previous else None
    fingerprint=hashlib.sha256(json.dumps({'title':post['title'],'body':post['body'],'assets':[(a['filename'],hashlib.sha256(a['content']).hexdigest()) for a in post['assets']],'issues':[(e['code'],e.get('url')) for e in post['issues']]},sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    if old:
        prev=get(c,'revision',old['latest_revision_id'])
        if prev['content_sha256']==fingerprint:
            old['last_checked_at']=now();put(c,'document',old);return old,'unchanged'
        prev['is_latest']=False;put(c,'revision',prev)
    stamp=now();did=old['id'] if old else uid();rid=uid();snapshot=store_asset(c,post['body'].encode(),f"{post['board']}-{post['post']}.txt",'text/plain',post['url'])
    assets=[snapshot]+[store_asset(c,a['content'],a['filename'],a['content_type'],a['source_url']) for a in post['assets']]
    status='login_required' if any(e['code']=='SOURCE_LOGIN_REQUIRED' for e in post['issues']) else 'incomplete' if post['issues'] else 'complete' if len(assets)>1 else 'none'
    doc={'id':did,'source_id':str(source_id),'board_key':post['board'],'external_post_id':post['post'],'title':post['title'],'author_display_name':post['author'],'source_url':post['url'],'published_at':post['published_at'],'collected_at':stamp,'latest_revision_id':rid,'analysis_status':'not_analyzed','attachment_status':status,'proposal_count':old.get('proposal_count',0) if old else 0,'first_seen_at':old['first_seen_at'] if old else stamp,'last_checked_at':stamp}
    rev={'id':rid,'document_id':did,'revision_number':prev['revision_number']+1 if old else 1,'title':post['title'],'content_sha256':fingerprint,'collected_at':stamp,'published_at':post['published_at'],'snapshot_asset_id':snapshot['id'],'body_text':post['body'][:8192],'assets':assets,'extraction_ids':[],'is_latest':True,'body_truncated':len(post['body'])>8192,'segment_manifest_id':None,'collection_issues':post['issues']}
    put(c,'document',doc);put(c,'revision',rev)
    from backend.app.domains.pricing.workbooks import register
    for asset in assets:
        if asset['filename'].lower().endswith('.xlsx'):
            try:
                with c.transaction():register(c,rid,asset['id'])
            except Problem:pass # Source remains preserved; parser job reports any extraction issue.
    return doc,'updated' if old else 'new'

def collect_source(source_id,payload,progress=None,site=None):
    site=site or SiteClient();results=[];issues=[];counts={'new':0,'updated':0,'unchanged':0};analysis_jobs=[];boards=payload.get('board_keys') or BOARDS;limit=min(max(int(payload.get('max_posts_per_board',30)),1),100)
    with tx() as c:cfg=config(c,source_id)
    try:
        if cfg:
            try:
                site.login(cfg);cfg['cookies']=site.cookies()
                with tx() as c:write(c,source_id,cfg,'connected');c.execute('UPDATE source_connections SET last_checked_at=now() WHERE source_id=%s',(source_id,))
            except Problem as e:
                with tx() as c:c.execute("UPDATE source_connections SET state='login_failed',last_checked_at=now() WHERE source_id=%s",(source_id,))
                raise e
        if payload.get('login_only'):
            if not cfg:raise Problem(422,'SOURCE_ACCOUNT_REQUIRED','사이트 회원 정보를 먼저 저장하세요.')
            return {'document_ids':[],'counts':counts,'analysis_job_ids':[],'issues':[],'connected':True}
        for board in boards:
            if board not in BOARDS:raise Problem(422,'BOARD_INVALID','등록된 게시판을 선택하세요.')
            with tx() as c:
                c.execute('INSERT INTO collection_cursors(source_id,board_key) VALUES(%s,%s) ON CONFLICT DO NOTHING',(source_id,board));cursor=c.execute('SELECT * FROM collection_cursors WHERE source_id=%s AND board_key=%s',(source_id,board)).fetchone()
            high=cursor['high_water'];cycle_max=cursor['cycle_max'];next_page=cursor['continuation_page'];pages=[1]+([next_page] if next_page and next_page!=1 else []);seen=set();processed=0;scan_complete=False;last_page=1;had_error=False
            while pages and processed<limit:
                page=pages.pop(0);last_page=page
                if progress:progress(f'{board} · {page}페이지 확인',len(results))
                posts=site.list_posts(board,page)
                if page==1 and posts:cycle_max=max(cycle_max,max(map(int,posts)))
                if not posts:scan_complete=True;break
                encountered_old=any(int(p)<=high for p in posts)
                eligible=[p for p in posts if p not in seen]
                if next_page and page==1:eligible=eligible[:5]
                consumed=0
                for post_id in eligible:
                    if post_id in seen:continue
                    # Recent pages are revisited even when known, so edits/deletions are not hidden by high water.
                    if processed>=limit:break
                    seen.add(post_id);processed+=1;consumed+=1
                    if progress:progress(f'{board} · 게시글 {post_id} 가져오는 중',len(results))
                    try:
                        post=site.post(board,post_id)
                        if progress:progress(f'{board} · 게시글 {post_id} 저장',len(results))
                        with tx() as c:
                            doc,kind=ingest(c,source_id,post);counts[kind]=counts.get(kind,0)+1
                            if doc is None:continue
                            results.append(doc['id'])
                            if payload.get('auto_analyze',True):
                                run,job=queue_analysis(c,doc['latest_revision_id'])
                                if job:analysis_jobs.append(job['id'])
                        issues.extend([dict(e,document_id=doc['id']) for e in post['issues']])
                    except Problem as e:
                        if e.code in ('CANCELLED','LEASE_LOST'):raise
                        had_error=True;issues.append({'code':e.code,'message':e.message,'board':board,'post':post_id})
                page_complete=consumed==len(eligible)
                if page_complete and (encountered_old or len(posts)<15):scan_complete=True
                if high==0 and processed>=limit:scan_complete=True
                if scan_complete:break
                if not pages:pages.append(page+1)
            # Advance only on a completed scan; continuations survive page/operation caps.
            with tx() as c:
                if scan_complete and not had_error:c.execute('UPDATE collection_cursors SET high_water=GREATEST(high_water,%s),cycle_max=0,continuation_page=NULL,last_success_at=now() WHERE source_id=%s AND board_key=%s',(cycle_max,source_id,board))
                else:
                    continuation=last_page if had_error or not page_complete else last_page+1
                    c.execute('UPDATE collection_cursors SET cycle_max=%s,continuation_page=%s WHERE source_id=%s AND board_key=%s',(cycle_max,continuation,source_id,board))
                    issues.append({'code':'SCAN_CONTINUES','message':'이번 수집 범위를 초과한 글은 다음 실행에서 이어서 확인합니다.','board':board})
            if int(payload.get('revisit_days',14))>0:
                with tx() as c:
                    recent=c.execute("SELECT data FROM app_records WHERE kind='document' AND data->>'source_id'=%s AND data->>'board_key'=%s AND (data->>'collected_at')::timestamptz>now()-(%s*interval '1 day') ORDER BY COALESCE(data->>'last_checked_at',data->>'collected_at') LIMIT 10",(source_id,board,int(payload.get('revisit_days',14)))).fetchall()
                for record in recent:
                    pid=record['data']['external_post_id']
                    if pid in seen:continue
                    if progress:progress(f'{board} · 기존 게시글 {pid} 변경 확인',len(results))
                    try:
                        post=site.post(board,pid)
                        with tx() as c:
                            doc,kind=ingest(c,source_id,post);counts[kind]=counts.get(kind,0)+1
                            if doc is None:continue
                            results.append(doc['id'])
                            if kind!='unchanged' and payload.get('auto_analyze',True):
                                _,job=queue_analysis(c,doc['latest_revision_id'])
                                if job:analysis_jobs.append(job['id'])
                        issues.extend(post['issues'])
                    except Problem as e:
                        if e.code in ('CANCELLED','LEASE_LOST'):raise
                        issues.append({'code':e.code,'message':e.message,'post':pid})
        with tx() as c:
            s=get(c,'source',source_id,True);s['last_collected_at']=now();s['last_collection_counts']=counts;put(c,'source',s)
        return {'document_ids':list(dict.fromkeys(results)),'counts':counts,'analysis_job_ids':analysis_jobs,'issues':issues}
    finally:site.close()

def schedule_tick():
    with tx() as c:
        c.execute("SELECT pg_advisory_xact_lock(hashtext('food-scheduler'))")
        for source in records(c,'source'):
            if not source.get('schedule_enabled') or not source.get('enabled'):continue
            connection=c.execute('SELECT state FROM source_connections WHERE source_id=%s',(source['id'],)).fetchone()
            if connection and connection['state']=='login_failed':continue
            c.execute('SELECT pg_advisory_xact_lock(hashtext(%s))',('collect:'+source['id'],))
            interval=int(source.get('poll_interval_minutes',30));last=source.get('last_enqueued_at')
            if last and (datetime.now(timezone.utc)-datetime.fromisoformat(last.replace('Z','+00:00'))).total_seconds()<interval*60:continue
            active=c.execute("SELECT 1 FROM jobs WHERE type='collect' AND status IN ('queued','running') AND payload->>'source_id'=%s",(source['id'],)).fetchone()
            if active:continue
            enqueue(c,'collect',{'source_id':source['id'],'board_keys':BOARDS,'max_posts_per_board':30,'auto_analyze':True});source['last_enqueued_at']=now();put(c,'source',source)
