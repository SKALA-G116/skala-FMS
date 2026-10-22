"""
==============================================================================
FMS_FILE_SPEC
documents.py - 원본 파일·문서 revision 등록
==============================================================================
설명:
    - 원본 파일·문서 revision 등록
입력·출력 명세:
    - 입력: 파일명·제목·bytes·선택 source 정보
    - 출력: 내용 해시·asset·문서·revision DTO
실행 가정:
    - 파일 크기를 제한하고 실제 업무 사실 반영과 분리
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

    2026-10-22  김재현(Finn) v0.1.0   25MB·표 삽입 이미지 근거 보완 및 검수 오류 개선

    상세 Git 이력: git log --follow -- backend/app/domains/ingestion/documents.py
    공통 규칙: doc/file-header-policy.md
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
import mimetypes
import os
from pathlib import Path
from backend.app.infrastructure.database import Problem
from backend.app.runtime.limits import MAX_FILE_BYTES
from backend.app.infrastructure.database import ROOT
from backend.app.infrastructure.database import get
from backend.app.infrastructure.database import now
from backend.app.infrastructure.database import put
from backend.app.infrastructure.database import uid

DATA=Path(os.getenv('FOOD_DATA_DIR',str(ROOT/'.local/assets'))).resolve()

DATA.mkdir(parents=True,exist_ok=True)

def import_document(c,title,content,filename,source=None):
    if len(content)>MAX_FILE_BYTES:raise Problem(413,'FILE_TOO_LARGE','파일은 25MB까지 지원합니다.')
    digest=hashlib.sha256(content).hexdigest();aid=uid();did=uid();rid=uid();stamp=now()
    c.execute('SELECT pg_advisory_xact_lock(hashtext(%s))',('asset:'+digest,))
    path=DATA/digest
    if not path.exists():path.write_bytes(content)
    asset={'id':aid,'filename':Path(filename).name,'content_type':mimetypes.guess_type(filename)[0] or 'application/octet-stream','size_bytes':len(content),'sha256':digest,'access_status':'available'}
    put(c,'asset',dict(asset,storage_key=digest))
    if source:
        rows=c.execute("SELECT data FROM app_records WHERE kind='document' AND data->>'source_url'=%s",(source['url'],)).fetchall()
        if rows:
            old=rows[0]['data'];oldrev=get(c,'revision',old['latest_revision_id'])
            if oldrev['content_sha256']==digest:return {'document':old,'revision':oldrev}
            did=old['id'];oldrev['is_latest']=False;put(c,'revision',oldrev)
    doc={'id':did,'source_id':source['id'] if source else None,'board_key':source.get('board') if source else None,'external_post_id':source.get('post') if source else None,'title':title,'author_display_name':None,'source_url':source['url'] if source else None,'published_at':None,'collected_at':stamp,'latest_revision_id':rid,'analysis_status':'not_analyzed','attachment_status':'none','proposal_count':0,'first_seen_at':stamp}
    body=content.decode('utf-8','replace') if Path(filename).suffix.lower() in ('.txt','.csv','.tsv','.md','.html','.json') else ''
    rev={'id':rid,'document_id':did,'revision_number':oldrev['revision_number']+1 if source and 'oldrev' in locals() else 1,'title':title,'content_sha256':digest,'collected_at':stamp,'published_at':None,'snapshot_asset_id':aid,'body_text':body[:8192],'assets':[asset],'extraction_ids':[],'is_latest':True,'body_truncated':len(body)>8192,'segment_manifest_id':None}
    put(c,'document',doc);put(c,'revision',rev)
    return {'document':doc,'revision':rev}
