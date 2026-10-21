"""
==============================================================================
FMS_FILE_SPEC
api.py - analysis 도메인 HTTP 유스케이스
==============================================================================
설명:
    - analysis 도메인 HTTP 유스케이스
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

    상세 Git 이력: git log --follow -- backend/app/domains/analysis/api.py
    공통 규칙: doc/file-header-policy.md

기존 모듈 설명:
    Analysis HTTP use cases. The transport owns authentication and the transaction.
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

import json
from backend.app.infrastructure.database import Problem
from backend.app.infrastructure.database import ROOT
from backend.app.infrastructure.database import get
from backend.app.api.http import DomainResult
from backend.app.infrastructure.contracts import schema_check
from backend.app.domains.jobs.service import getjob
from backend.app.api.routing import domain_router

def handle(ctx):
    c, req, method, q, payload = ctx.connection, ctx.request, ctx.method, ctx.query, ctx.payload
    content, u, path = ctx.content, ctx.actor, ctx.path
    parts, root, id, action = ctx.parts, ctx.root, ctx.id, ctx.action
    mutating = method != 'GET'
    status, headers = 200, {}
    if root == 'analysis-profiles':
        out = json.loads((ROOT / 'doc/food-agent/examples/analysis-profiles.json').read_text())
    elif root == 'analysis-runs':
        if action == 'items' and method == 'PATCH':
            from backend.app.domains.review.items import save_item
            out = save_item(c, id, parts[3], payload, u['id'])
            headers['ETag'] = str(out.get('version', 1))
        elif action == 'review-export' and method == 'POST':
            from backend.app.domains.analysis.export import export_review
            run = get(c, 'analysis_run', id)
            if not run.get('agent_report_id') or get(c, 'agent_report', run['agent_report_id'])['status'] != 'completed':
                raise Problem(409, 'REPORT_NOT_READY', '분석이 끝난 뒤 다운로드할 수 있습니다.')
            out = export_review({'run_id': id, 'revision_id': run['document_revision_id'], 'agent_report_id': run['agent_report_id'], 'review_mode': True}, connection=c)
        elif action == 'review-proposals' and method == 'POST':
            from backend.app.domains.review.items import prepare
            out = prepare(c, id, payload, u['id'])
        elif method == 'POST':
            schema_check('AnalysisInput', payload)
            from backend.app.domains.analysis.service import queue_analysis
            run, out = queue_analysis(c, payload['document_revision_id'], force=True)
            if run is None:
                raise Problem(409, 'DOCUMENT_ARCHIVED', '삭제된 자료입니다. 자료 관리에서 복구한 뒤 분석해 주세요.')
            if not out:
                out = getjob(c, run['job_id'])
            status = 202
        else:
            out = get(c, 'analysis_run', id)
            if action == 'report':
                if not out.get('agent_report_id'):
                    raise Problem(404, 'REPORT_NOT_READY', 'AI 분석 결과를 준비하고 있습니다.')
                out = get(c, 'agent_report', out['agent_report_id'])
                from backend.app.domains.catalog.record import upgrade_event
                out['events'] = [upgrade_event(e) for e in out['events']]
                out.setdefault('version', 1)
                out.setdefault('dto_schema', 'food-change-dto-v1')
                latest = c.execute("SELECT data FROM app_records WHERE kind='analysis_run' AND data->>'document_revision_id'=%s AND data->>'mode'!='rules' AND data->>'status'='succeeded' ORDER BY created_at DESC LIMIT 1", (out['document_revision_id'],)).fetchone()
                out['latest_analysis_run_id'] = latest['data']['id'] if latest else id
    else:
        raise Problem(404, 'NOT_FOUND', '지원하지 않는 경로입니다.')
    return DomainResult(out, status, headers)

ROUTES = (('analysis-runs', ('POST',)), ('analysis-profiles', ('GET',)), ('analysis-runs/{id}', ('GET',)), ('analysis-runs/{id}/review-export', ('POST',)), ('analysis-runs/{id}/report', ('GET',)), ('analysis-runs/{id}/items/{item_id}', ('PATCH',)), ('analysis-runs/{id}/review-proposals', ('POST',)))

router = domain_router('analysis', ROUTES)
