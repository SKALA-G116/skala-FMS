"""Permanent removal of discarded, unreferenced materials and derived artifacts."""
import re
import uuid
from backend.app.infrastructure.database import Problem
from backend.app.infrastructure.database import get
from backend.app.infrastructure.database import now
from backend.app.infrastructure.database import put
from backend.app.infrastructure.database import records
from backend.app.infrastructure.database import tx
from backend.app.infrastructure.database import uid
from backend.app.domains.ingestion.archives import state
from backend.app.domains.ingestion.archives import document_rows
from backend.app.domains.ingestion.archives import change

def selection(c,q):
    rows=document_rows(c,records(c,'document'),q);query=q.get('q','').casefold().strip()
    if query:rows=[r for r in rows if query in __import__('json').dumps(r,ensure_ascii=False).casefold()]
    return {'items':[{'id':r['id'],'title':r['title'],'archive_version':r['archive_version'],'archived':r['archived']} for r in rows],'total':len(rows)}

def purge_document(c,id,version,actor,reason):
    uuid.UUID(id)
    c.execute("SELECT pg_advisory_xact_lock(hashtext('food-catalog-apply'))")
    preview=get(c,'document',id)
    if preview.get('source_id') and preview.get('board_key') and preview.get('external_post_id'):
        identity=':'.join((str(preview['source_id']),preview['board_key'],str(preview['external_post_id'])))
        c.execute('SELECT pg_advisory_xact_lock(hashtext(%s))',(identity,))
    c.execute('SELECT pg_advisory_xact_lock(hashtext(%s))',('archive:document:'+id,))
    document=get(c,'document',id,True);status=state(c,'document',id)
    if not status['archived']:raise Problem(409,'NOT_ARCHIVED','먼저 자료를 삭제한 뒤 영구 삭제하세요.')
    if status['archive_version']!=version:raise Problem(409,'ARCHIVE_CHANGED','삭제·복구 상태가 변경되었습니다. 목록을 새로 조회하세요.')
    revisions=c.execute("SELECT id,data FROM app_records WHERE kind='revision' AND data->>'document_id'=%s FOR UPDATE",(id,)).fetchall();rids=[str(r['id']) for r in revisions]
    runs=c.execute("SELECT id,data FROM app_records WHERE kind='analysis_run' AND data->>'document_revision_id'=ANY(%s) FOR UPDATE",(rids,)).fetchall();runids=[str(r['id']) for r in runs]
    if c.execute("SELECT 1 FROM jobs WHERE status IN ('queued','running') AND (data->>'analysis_run_id'=ANY(%s) OR payload->>'document_revision_id'=ANY(%s)) LIMIT 1",(runids,rids)).fetchone():raise Problem(409,'DOCUMENT_BUSY','진행 중인 분석을 마치거나 취소한 뒤 영구 삭제하세요.')
    evidence=c.execute("SELECT id FROM app_records WHERE kind='evidence' AND data->>'document_revision_id'=ANY(%s)",(rids,)).fetchall();eids=[str(e['id']) for e in evidence]
    proposals=c.execute("SELECT id,data FROM app_records WHERE kind='proposal' AND data->'source_document_revision_ids' ?| %s::text[] FOR UPDATE",(rids,)).fetchall();pids=[str(p['id']) for p in proposals]
    for row in proposals:
        p=row['data']
        if p['summary']['status'] in ('approved','applying','applied','apply_failed') or c.execute('SELECT 1 FROM applications WHERE proposal_id=%s LIMIT 1',(row['id'],)).fetchone():raise Problem(409,'MATERIAL_IN_USE','승인·반영된 식품의 근거 자료입니다. 변경 이력 보호를 위해 영구 삭제할 수 없습니다.')
        if set(p['source_document_revision_ids'])-set(rids):raise Problem(409,'MATERIAL_SHARED','다른 자료와 함께 작성한 변경안이 있습니다. 연결을 정리한 뒤 영구 삭제하세요.')
    if eids and (c.execute("SELECT 1 FROM facts WHERE data->'evidence_ids' ?| %s::text[] LIMIT 1",(eids,)).fetchone() or c.execute("SELECT 1 FROM catalog_entities WHERE data->'evidence_ids' ?| %s::text[] LIMIT 1",(eids,)).fetchone() or c.execute("SELECT 1 FROM app_records WHERE kind='audit' AND data->>'product_id' IS NOT NULL AND data->'evidence_ids' ?| %s::text[] LIMIT 1",(eids,)).fetchone()):raise Problem(409,'MATERIAL_IN_USE','식품 정보·변경 이력에서 참조하는 원문은 영구 삭제할 수 없습니다.')
    reports=c.execute("SELECT data FROM app_records WHERE kind='agent_report' AND data->>'analysis_run_id'=ANY(%s)",(runids,)).fetchall()
    assets=set()
    for row in revisions:
        rev=row['data'];assets.add(rev['snapshot_asset_id']);assets.update(a['id'] for a in rev['assets'])
    for row in reports:
        report=row['data']
        if report.get('export_asset_id'):assets.add(report['export_asset_id'])
        assets.update(report.get('previous_export_asset_ids',[]))
    c.execute('DELETE FROM price_sheet_rows WHERE sheet_id IN (SELECT s.id FROM price_sheets s JOIN price_workbooks w ON w.id=s.workbook_id WHERE w.document_id=%s)',(id,))
    c.execute('DELETE FROM price_sheets WHERE workbook_id IN (SELECT id FROM price_workbooks WHERE document_id=%s)',(id,));c.execute('DELETE FROM price_workbooks WHERE document_id=%s',(id,))
    c.execute("DELETE FROM jobs WHERE data->>'analysis_run_id'=ANY(%s) OR payload->>'document_revision_id'=ANY(%s)",(runids,rids))
    for table in ('checkpoint_writes','checkpoint_blobs','checkpoints'):
        if c.execute('SELECT to_regclass(%s) name',(table,)).fetchone()['name']:c.execute(f'DELETE FROM {table} WHERE thread_id=ANY(%s)',(['analysis:'+runid for runid in runids],))
    c.execute("DELETE FROM app_records WHERE (kind='proposal_revision' AND data->>'proposal_id'=ANY(%s)) OR (kind='proposal' AND id=ANY(%s::uuid[])) OR (kind IN ('analysis_run','agent_report','agent_item_review','agent_review_snapshot') AND (id=ANY(%s::uuid[]) OR data->>'analysis_run_id'=ANY(%s))) OR (kind IN ('evidence','extraction') AND (data->>'document_revision_id'=ANY(%s) OR data->>'revision_id'=ANY(%s))) OR (kind='revision' AND id=ANY(%s::uuid[])) OR (kind='document' AND id=%s)",(pids,pids,runids,runids,rids,rids,rids,id))
    identities=[id,*rids,*runids,*pids,*assets]
    c.execute('DELETE FROM command_keys WHERE response::text LIKE ANY(%s)',(['%'+i+'%' for i in identities],))
    removed=0
    for aid in assets:
        # Shared references retain the asset; content hashes may also be shared by other asset IDs.
        if c.execute("SELECT 1 FROM app_records WHERE kind!='asset' AND data::text LIKE %s LIMIT 1",('%'+aid+'%',)).fetchone():continue
        row=c.execute("DELETE FROM app_records WHERE kind='asset' AND id=%s RETURNING data",(aid,)).fetchone()
        if row and re.fullmatch(r'[a-f0-9]{64}',row['data']['storage_key']):
            c.execute('INSERT INTO asset_cleanup(storage_key) VALUES(%s) ON CONFLICT DO NOTHING',(row['data']['storage_key'],));removed+=1
    if document.get('source_id') and document.get('board_key') and document.get('external_post_id'):
        c.execute('INSERT INTO purged_source_posts(source_id,board_key,external_post_id) VALUES(%s,%s,%s) ON CONFLICT DO NOTHING',(str(document['source_id']),document['board_key'],str(document['external_post_id'])))
    c.execute("DELETE FROM record_archives WHERE record_kind='document' AND record_id=%s",(id,))
    put(c,'audit',{'id':uid(),'kind':'document_purged','entity_id':id,'product_id':None,'document_id':id,'proposal_id':None,'application_id':None,'before':{'archived':True},'after':None,'evidence_ids':[],'actor':actor,'reason':reason,'recorded_at':now(),'period':None})
    return {'id':id,'purged':True,'removed_assets':removed,'file_cleanup':'queued'}

def batch(c,payload,actor):
    action=payload.get('action');items=payload.get('items');reason=payload.get('reason','자료함 일괄 작업')
    if action not in ('archive','restore','purge') or not isinstance(items,list) or not 1<=len(items)<=2000 or not isinstance(reason,str) or not 1<=len(reason.strip())<=500:raise Problem(422,'BATCH_INPUT','작업 종류와 선택한 자료를 확인하세요.')
    if action=='purge' and payload.get('confirmation')!='영구 삭제':raise Problem(422,'PURGE_CONFIRMATION','영구 삭제 확인 문구가 필요합니다.')
    seen=set()
    for item in items:
        if not isinstance(item,dict) or set(item)!= {'id','archive_version'} or type(item['archive_version']) is not int or item['archive_version']<0:raise Problem(422,'BATCH_INPUT','선택 자료의 버전 정보가 필요합니다.')
        try:uuid.UUID(item['id'])
        except (ValueError,TypeError,AttributeError):raise Problem(422,'BATCH_INPUT','자료 식별자가 올바르지 않습니다.')
        if item['id'] in seen:raise Problem(422,'BATCH_INPUT','같은 자료가 중복 선택됐습니다.')
        seen.add(item['id'])
    results=[];failures=[]
    for item in sorted(items,key=lambda x:x['id']):
        try:
            with c.transaction():
                value=purge_document(c,item['id'],item['archive_version'],actor,reason) if action=='purge' else change(c,'document',item['id'],action=='archive',{'archive_version':item['archive_version'],'reason':reason},actor)
                results.append(value)
        except Problem as ex:failures.append({'id':item['id'],'code':ex.code,'message':ex.message})
    return {'action':action,'succeeded':len(results),'failed':len(failures),'results':results,'failures':failures}

def cleanup_files():
    """Run after commit; serialized with uploads so a shared/new asset is never unlinked."""
    from backend.app.domains.ingestion.documents import DATA
    with tx() as c:
        for row in c.execute('SELECT storage_key FROM asset_cleanup ORDER BY created_at FOR UPDATE SKIP LOCKED LIMIT 20').fetchall():
            key=row['storage_key']
            if not re.fullmatch(r'[a-f0-9]{64}',key):continue
            c.execute('SELECT pg_advisory_xact_lock(hashtext(%s))',('asset:'+key,))
            if not c.execute("SELECT 1 FROM app_records WHERE kind='asset' AND data->>'storage_key'=%s LIMIT 1",(key,)).fetchone():
                try:(DATA/key).unlink(missing_ok=True)
                except OSError as ex:
                    c.execute('UPDATE asset_cleanup SET attempts=attempts+1,last_error=%s WHERE storage_key=%s',(type(ex).__name__,key));continue
            c.execute('DELETE FROM asset_cleanup WHERE storage_key=%s',(key,))
