"""
==============================================================================
FMS_FILE_SPEC
archives.py - 자료·식품의 삭제 보관과 복구
==============================================================================
설명:
    - 자료·식품의 삭제 보관과 복구
입력·출력 명세:
    - 입력: 대상 종류/ID·보관 버전·행위자·사유
    - 출력: 갱신된 보관 상태와 버전
실행 가정:
    - 활성 작업과 승인 근거의 일관성을 유지
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

    상세 Git 이력: git log --follow -- backend/app/domains/ingestion/archives.py
    공통 규칙: doc/file-header-policy.md

기존 모듈 설명:
    Recoverable catalog/material removal. Original evidence and facts are retained.
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

from backend.app.infrastructure.database import Problem
from backend.app.infrastructure.database import entity
from backend.app.infrastructure.database import get
from backend.app.infrastructure.database import now
from backend.app.infrastructure.database import put
from backend.app.infrastructure.database import uid
import uuid

def state(c,kind,id):
    row=c.execute('SELECT archived,version FROM record_archives WHERE record_kind=%s AND record_id=%s',(kind,id)).fetchone()
    return {'archived':row['archived'] if row else False,'archive_version':row['version'] if row else 0}

def document_rows(c,rows,q):
    deleted={str(r['record_id']):r for r in c.execute("SELECT record_id,archived,version FROM record_archives WHERE record_kind='document'")}
    archived=q.get('archived')=='true';out=[]
    for row in rows:
        status=deleted.get(row['id']);is_deleted=bool(status and status['archived'])
        if is_deleted!=archived:continue
        out.append({**row,'archived':is_deleted,'archive_version':status['version'] if status else 0})
    return out

def change(c,kind,id,archived,payload,actor):
    import uuid
    try:uuid.UUID(id)
    except (ValueError,TypeError):raise Problem(422,'ARCHIVE_TARGET','삭제·복구 대상을 확인하세요.')
    if set(payload)-{'archive_version','reason'} or type(payload.get('archive_version')) is not int or payload['archive_version']<0 or not isinstance(payload.get('reason'),str) or not 1<=len(payload['reason'].strip())<=500:raise Problem(422,'ARCHIVE_INPUT','삭제·복구 사유와 최신 조회 버전이 필요합니다.')
    if kind=='food':c.execute("SELECT pg_advisory_xact_lock(hashtext('food-catalog-apply'))")
    c.execute('SELECT pg_advisory_xact_lock(hashtext(%s))',(f'archive:{kind}:{id}',))
    if kind=='food':
        obj=entity(c,id,True)
        row=c.execute('SELECT kind FROM catalog_entities WHERE id=%s',(id,)).fetchone()
        if row['kind']!='variant':raise Problem(422,'ARCHIVE_TARGET','목록의 식품 규격을 선택하세요.')
        product_id=obj['product_id'];evidence=obj.get('evidence_ids',[])
    else:
        obj=get(c,'document',id,True);product_id=None;evidence=[]
        active=c.execute("SELECT 1 FROM jobs j JOIN app_records ar ON ar.kind='analysis_run' AND ar.id::text=j.data->>'analysis_run_id' JOIN app_records rev ON rev.kind='revision' AND rev.id::text=ar.data->>'document_revision_id' WHERE j.status IN ('running','queued') AND rev.data->>'document_id'=%s LIMIT 1",(id,)).fetchone()
        if archived and active:raise Problem(409,'DOCUMENT_BUSY','이 자료를 분석 중입니다. 작업을 마치거나 취소한 뒤 삭제해 주세요.')
    before=state(c,kind,id)
    if payload['archive_version']!=before['archive_version']:raise Problem(409,'ARCHIVE_CHANGED','다른 사용자가 삭제·복구 상태를 변경했습니다. 목록을 새로 조회하세요.')
    if before['archived']==archived:return {'id':id,'record_kind':kind,**before}
    version=before['archive_version']+1;reason=payload['reason'].strip()
    c.execute('INSERT INTO record_archives(record_kind,record_id,archived,version,actor_id,reason) VALUES(%s,%s,%s,%s,%s,%s) ON CONFLICT(record_kind,record_id) DO UPDATE SET archived=excluded.archived,version=excluded.version,actor_id=excluded.actor_id,reason=excluded.reason,updated_at=now()', (kind,id,archived,version,actor,reason))
    after={'id':id,'record_kind':kind,'archived':archived,'archive_version':version}
    put(c,'audit',{'id':uid(),'application_id':None,'proposal_id':None,'product_id':product_id,'document_id':id if kind=='document' else None,'kind':kind+('_archived' if archived else '_restored'),'entity_id':id,'before':before,'after':after,'evidence_ids':evidence,'actor':actor,'recorded_at':now(),'period':None,'reason':reason})
    # Bump catalog target version so an approval made before deletion cannot write through it.
    if kind=='food':c.execute("UPDATE catalog_entities SET version=version+1,data=jsonb_set(data,'{version}',to_jsonb(version+1)) WHERE id=%s",(id,))
    return after
