"""Reporting HTTP use cases. The transport owns authentication and the transaction."""
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
