"""
==============================================================================
FMS_FILE_SPEC
api.py - reporting 도메인 HTTP 유스케이스
==============================================================================
설명:
    - reporting 도메인 HTTP 유스케이스
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

    상세 Git 이력: git log --follow -- backend/app/domains/reporting/api.py
    공통 규칙: doc/file-header-policy.md

기존 모듈 설명:
    Reporting HTTP use cases. The transport owns authentication and the transaction.
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
from backend.app.infrastructure.database import records
from backend.app.infrastructure.database import today
from backend.app.api.http import DomainResult
from backend.app.api.routing import domain_router

def handle(ctx):
    c, req, method, q, payload = ctx.connection, ctx.request, ctx.method, ctx.query, ctx.payload
    content, u, path = ctx.content, ctx.actor, ctx.path
    parts, root, id, action = ctx.parts, ctx.root, ctx.id, ctx.action
    mutating = method != 'GET'
    status, headers = 200, {}
    if path == 'dashboard':
        ps = records(c, 'proposal')
        counts = lambda s: sum((p['summary']['status'] == s for p in ps))
        out = {'review_ready_count': counts('ready'), 'on_hold_count': counts('on_hold'), 'conflict_count': counts('conflict'), 'failed_job_count': c.execute("SELECT count(*) n FROM jobs WHERE status='failed'").fetchone()['n'], 'scheduled_fact_count': c.execute('SELECT count(*) n FROM facts WHERE effective_from>%s', (today(),)).fetchone()['n'], 'as_of': today(), 'food_count': c.execute("SELECT count(*) n FROM catalog_entities v WHERE v.kind='variant' AND NOT EXISTS(SELECT 1 FROM record_archives a WHERE a.record_kind='food' AND a.record_id=v.id AND a.archived)").fetchone()['n'], 'document_count': c.execute("SELECT count(*) n FROM app_records d WHERE d.kind='document' AND NOT EXISTS(SELECT 1 FROM record_archives a WHERE a.record_kind='document' AND a.record_id=d.id AND a.archived)").fetchone()['n']}
    else:
        raise Problem(404, 'NOT_FOUND', '지원하지 않는 경로입니다.')
    return DomainResult(out, status, headers)

ROUTES = (('dashboard', ('GET',)),)

router = domain_router('reporting', ROUTES)
