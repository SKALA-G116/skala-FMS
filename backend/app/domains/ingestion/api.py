"""
==============================================================================
FMS_FILE_SPEC
api.py - ingestion 도메인 HTTP 유스케이스
==============================================================================
설명:
    - ingestion 도메인 HTTP 유스케이스
입력·출력 명세:
    - 입력: 인증·권한·CSRF를 확인한 RequestContext와 경로/조회/본문
    - 출력: DomainResult 또는 HTTP Response
실행 가정:
    - 공통 transport가 소유한 같은 DB 트랜잭션을 사용
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

    상세 Git 이력: git log --follow -- backend/app/domains/ingestion/api.py
    공통 규칙: doc/file-header-policy.md

기존 모듈 설명:
    Ingestion HTTP use cases. The transport owns authentication and the transaction.
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

import hmac
import hashlib
from datetime import datetime
from datetime import timezone
from datetime import timedelta
from fastapi.responses import FileResponse
from backend.app.infrastructure.database import Problem
from backend.app.infrastructure.database import get
from backend.app.infrastructure.database import put
from backend.app.infrastructure.database import records
from backend.app.api.http import DomainResult
from backend.app.api.http import etag
from backend.app.api.http import match
from backend.app.api.http import page
from backend.app.api.http import filtered
from backend.app.domains.identity.service import permit
from backend.app.infrastructure.contracts import schema_check
from backend.app.domains.ingestion.documents import import_document
from backend.app.domains.ingestion.documents import DATA
from backend.app.domains.jobs.service import enqueue
from backend.app.api.assets import ASSET_SIGN_KEY
from backend.app.api.routing import domain_router

def handle(ctx):
    c, req, method, q, payload = ctx.connection, ctx.request, ctx.method, ctx.query, ctx.payload
    content, u, path = ctx.content, ctx.actor, ctx.path
    parts, root, id, action = ctx.parts, ctx.root, ctx.id, ctx.action
    mutating = method != 'GET'
    status, headers = 200, {}
    if ctx.extra_archive:
        from backend.app.domains.ingestion.archives import change
        return DomainResult(change(c, 'food' if root == 'foods' else 'document', id, method == 'DELETE', payload, u['id']))
    if path == 'document-selections':
        from backend.app.domains.ingestion.purge import selection
        out = selection(c, q)
    elif path == 'document-actions' and method == 'POST':
        from backend.app.domains.ingestion.purge import batch
        out = batch(c, payload, u['id'])
    elif root == 'sources':
        if action == 'connection':
            permit(u, ['admin'])
            get(c, 'source', id)
            from backend.app.domains.ingestion.connections import public; from backend.app.domains.ingestion.connections import save
            if method == 'GET':
                out = public(c, id)
            elif len(parts) == 4 and parts[3] == 'test':
                out = enqueue(c, 'collect', {'source_id': id, 'login_only': True})
                status = 202
            else:
                out = save(c, id, payload)
        elif id:
            out = get(c, 'source', id, mutating)
            if method == 'PATCH':
                schema_check('SourcePatch', payload)
                match(req, out)
                out.update(payload)
                out['version'] += 1
                put(c, 'source', out)
            headers['ETag'] = etag(out)
        else:
            out = page(records(c, 'source'), q, c)
    elif root == 'collection-runs' and method == 'POST':
        schema_check('CollectionInput', {k: v for k, v in payload.items() if k != 'auto_analyze'})
        get(c, 'source', payload['source_id'])
        c.execute('SELECT pg_advisory_xact_lock(hashtext(%s))', ('collect:' + payload['source_id'],))
        active = c.execute("SELECT data FROM jobs WHERE type='collect' AND status IN ('queued','running') AND payload->>'source_id'=%s ORDER BY created_at LIMIT 1", (payload['source_id'],)).fetchone()
        out = active['data'] if active else enqueue(c, 'collect', {**payload, 'auto_analyze': payload.get('auto_analyze', True)})
        status = 202
    elif root == 'documents':
        if id == 'import' and method == 'POST':
            out = import_document(c, payload['title'], content, payload['filename'])
            from backend.app.domains.analysis.service import queue_analysis
            _, job = queue_analysis(c, out['revision']['id'])
            out['analysis_job'] = job
            status = 201
        elif id:
            from backend.app.domains.ingestion.archives import state
            out = {**get(c, 'document', id), **state(c, 'document', id)}
            latest = c.execute("SELECT data FROM app_records WHERE kind='analysis_run' AND data->>'document_revision_id'=%s AND data->>'mode'!='rules' ORDER BY created_at DESC LIMIT 1", (out['latest_revision_id'],)).fetchone()
            if latest:
                latest = latest['data']
                out = {**out, 'latest_analysis_run_id': latest['id'], 'latest_analysis_job_id': latest.get('job_id'), 'analysis_review_ready': bool(latest.get('agent_report_id') and latest['status'] == 'succeeded')}
            if action == 'revisions':
                out = page([r for r in records(c, 'revision') if r['document_id'] == id], q, c)
        else:
            from backend.app.domains.ingestion.archives import document_rows
            rows = filtered(document_rows(c, records(c, 'document'), q), q)
            out = page(rows, q, c)
            out['total'] = len(rows)
    elif root == 'document-revisions':
        if action == 'evidence':
            out = page([e for e in records(c, 'evidence') if e['document_revision_id'] == id], q, c)
        else:
            out = get(c, 'revision', id)
    elif root == 'evidence':
        out = get(c, 'evidence', id)
    elif root == 'assets':
        asset = get(c, 'asset', id)
        if action == 'access':
            expires = datetime.now(timezone.utc) + timedelta(minutes=5)
            exp = str(int(expires.timestamp()))
            sig = hmac.new(ASSET_SIGN_KEY, f"{id}:{u['id']}:{exp}".encode(), hashlib.sha256).hexdigest()
            out = {'asset_id': id, 'url': f'/api/v1/assets/{id}/content?exp={exp}&sig={sig}', 'expires_at': expires.isoformat(), 'content_type': asset['content_type']}
        elif action == 'content':
            exp = q.get('exp', '0')
            sig = q.get('sig', '')
            expected = hmac.new(ASSET_SIGN_KEY, f"{id}:{u['id']}:{exp}".encode(), hashlib.sha256).hexdigest()
            if int(exp) < datetime.now(timezone.utc).timestamp() or not hmac.compare_digest(sig, expected):
                raise Problem(403, 'ASSET_LINK_EXPIRED', '다운로드 링크가 만료되었습니다. 새 링크를 요청하세요.')
            return FileResponse(DATA / asset['storage_key'], media_type=asset['content_type'], filename=asset['filename'], content_disposition_type='inline' if q.get('preview') == 'true' and asset['content_type'] in ('image/png', 'image/jpeg', 'image/webp', 'image/gif', 'application/pdf') else 'attachment')
        else:
            raise Problem(404, 'NOT_FOUND', '파일을 찾을 수 없습니다.')
    else:
        raise Problem(404, 'NOT_FOUND', '지원하지 않는 경로입니다.')
    return DomainResult(out, status, headers)

ROUTES = (('sources', ('GET',)), ('sources/{id}', ('GET', 'PATCH')), ('collection-runs', ('POST',)), ('documents', ('GET',)), ('documents/import', ('POST',)), ('documents/{id}', ('DELETE', 'GET')), ('documents/{id}/revisions', ('GET',)), ('document-revisions/{id}', ('GET',)), ('evidence/{id}', ('GET',)), ('assets/{id}/access', ('GET',)), ('documents/{id}/restore', ('POST',)), ('document-selections', ('GET',)), ('document-actions', ('POST',)), ('document-revisions/{id}/evidence', ('GET',)), ('assets/{id}/content', ('GET',)), ('sources/{id}/connection', ('GET', 'POST')), ('sources/{id}/connection/test', ('POST',)))

router = domain_router('ingestion', ROUTES)
