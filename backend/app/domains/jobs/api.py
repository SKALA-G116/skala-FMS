"""
==============================================================================
FMS_FILE_SPEC
api.py - jobs 도메인 HTTP 유스케이스
==============================================================================
설명:
    - jobs 도메인 HTTP 유스케이스
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

    상세 Git 이력: git log --follow -- backend/app/domains/jobs/api.py
    공통 규칙: doc/file-header-policy.md

기존 모듈 설명:
    Jobs HTTP use cases. The transport owns authentication and the transaction.
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
from psycopg.types.json import Jsonb
from backend.app.infrastructure.database import Problem
from backend.app.infrastructure.database import get
from backend.app.infrastructure.database import now
from backend.app.infrastructure.database import put
from backend.app.api.http import DomainResult
from backend.app.api.http import page
from backend.app.api.http import filtered
from backend.app.domains.review.proposals import bump
from backend.app.domains.jobs.service import enqueue
from backend.app.domains.jobs.service import getjob
from backend.app.domains.jobs.service import savejob
from backend.app.api.routing import domain_router

def handle(ctx):
    c, req, method, q, payload = ctx.connection, ctx.request, ctx.method, ctx.query, ctx.payload
    content, u, path = ctx.content, ctx.actor, ctx.path
    parts, root, id, action = ctx.parts, ctx.root, ctx.id, ctx.action
    mutating = method != 'GET'
    status, headers = 200, {}
    if root == 'jobs':
        if not id:
            out = page(filtered([x['data'] for x in c.execute('SELECT data FROM jobs ORDER BY created_at DESC LIMIT 2000')], q), q, c)
        else:
            out = getjob(c, id, mutating)
            if action == 'cancel' and method == 'POST':
                if out['type'] == 'apply' or out['status'] not in ('queued', 'running'):
                    raise Problem(409, 'CANNOT_CANCEL', '이 작업은 취소할 수 없습니다.')
                out.update(status='cancelled', stage='취소됨', finished_at=now(), allowed_actions=[])
                savejob(c, out)
            elif action == 'retry' and method == 'POST':
                if out['status'] not in ('failed', 'partial'):
                    raise Problem(409, 'CANNOT_RETRY', '실패하거나 일부 완료된 작업만 재시도할 수 있습니다.')
                p = c.execute('SELECT payload FROM jobs WHERE id=%s', (id,)).fetchone()['payload']
                previous = out
                if previous['type'] == 'analyze':
                    from backend.app.domains.ingestion.archives import state
                    material_revision = get(c, 'revision', p['document_revision_id'])
                    get(c, 'document', material_revision['document_id'], True)
                    if state(c, 'document', material_revision['document_id'])['archived']:
                        raise Problem(409, 'DOCUMENT_ARCHIVED', '자료를 복구한 뒤 분석을 재시도해 주세요.')
                    oldrun = get(c, 'analysis_run', previous['analysis_run_id'])
                    if oldrun.get('mode') == 'rules' and os.getenv('FOOD_ANALYSIS_MODE', 'agent') != 'rules':
                        from backend.app.domains.analysis.service import queue_analysis
                        _, out = queue_analysis(c, p['document_revision_id'], force=True)
                    else:
                        out = enqueue(c, 'analyze', p, previous['analysis_run_id'], id)
                else:
                    out = enqueue(c, previous['type'], p, previous['analysis_run_id'], id)
                out['parent_job_id'] = id
                out['attempt'] = previous['attempt'] + 1
                savejob(c, out)
                if previous['type'] == 'apply':
                    a = c.execute('SELECT data FROM applications WHERE id=%s FOR UPDATE', (p['application_id'],)).fetchone()['data']
                    prop = get(c, 'proposal', a['proposal_id'], True)
                    if prop['summary']['status'] != 'apply_failed':
                        raise Problem(409, 'REVIEW_REQUIRED', '충돌한 변경안은 다시 검토해야 합니다.')
                    prop['summary']['status'] = 'applying'
                    bump(prop)
                    put(c, 'proposal', prop)
                    a['status'] = 'pending'
                    a['job_id'] = out['id']
                    c.execute('UPDATE applications SET data=%s WHERE id=%s', (Jsonb(a), a['id']))
                status = 202
    else:
        raise Problem(404, 'NOT_FOUND', '지원하지 않는 경로입니다.')
    return DomainResult(out, status, headers)

ROUTES = (('jobs', ('GET',)), ('jobs/{id}', ('GET',)), ('jobs/{id}/retry', ('POST',)), ('jobs/{id}/cancel', ('POST',)))

router = domain_router('jobs', ROUTES)
