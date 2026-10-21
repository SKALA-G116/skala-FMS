"""Review HTTP use cases. The transport owns authentication and the transaction."""
from psycopg.types.json import Jsonb
from backend.app.infrastructure.database import Problem
from backend.app.infrastructure.database import get
from backend.app.infrastructure.database import now
from backend.app.infrastructure.database import put
from backend.app.infrastructure.database import records
from backend.app.infrastructure.database import uid
from backend.app.api.http import DomainResult
from backend.app.api.http import etag
from backend.app.api.http import match
from backend.app.api.http import page
from backend.app.api.http import filtered
from backend.app.domains.identity.service import public_user
from backend.app.infrastructure.contracts import schema_check
from backend.app.domains.review.proposals import create
from backend.app.domains.review.proposals import validate
from backend.app.domains.review.proposals import bump
from backend.app.domains.review.proposals import actions
from backend.app.domains.review.proposals import revision
from backend.app.domains.jobs.service import enqueue
from backend.app.domains.jobs.service import getjob
from backend.app.api.routing import domain_router

def handle(ctx):
    c, req, method, q, payload = ctx.connection, ctx.request, ctx.method, ctx.query, ctx.payload
    content, u, path = ctx.content, ctx.actor, ctx.path
    parts, root, id, action = ctx.parts, ctx.root, ctx.id, ctx.action
    mutating = method != 'GET'
    status, headers = 200, {}
    if root == 'proposals':
        if not id:
            if method == 'POST':
                schema_check('ProposalCreate', payload)
                out = create(c, payload['title'], payload['source_document_revision_ids'], payload['changes'])
                status = 201
            else:
                out = page(filtered(records(c, 'proposal'), q), q, c)
        else:
            out = get(c, 'proposal', id, mutating)
            s = out['summary']
            if mutating:
                match(req, out)
                if method == 'PATCH':
                    schema_check('ProposalPatch', payload)
                    if 'edit' not in actions(out)['summary']['allowed_actions']:
                        raise Problem(409, 'NOT_EDITABLE', '승인 철회 또는 새 변경안이 필요합니다.')
                    out['changes'] = payload['changes']
                    s['title'] = payload.get('title', s['title'])
                    s['revision'] += 1
                    validate(c, out)
                    revision(c, out, u['id'], payload['edit_reason'])
                    bump(out)
                elif action == 'validate':
                    if s['status'] not in ('draft', 'ready', 'on_hold', 'conflict'):
                        raise Problem(409, 'NOT_VALIDATABLE', '현재 상태에서 재검증할 수 없습니다.')
                    s['revision'] += 1
                    validate(c, out)
                    revision(c, out, u['id'], '재검증')
                    bump(out)
                elif action == 'confirm-ai':
                    if s['status'] not in ('draft', 'ready'):
                        raise Problem(409, 'NOT_EDITABLE', '검토 중인 변경안만 확인할 수 있습니다.')
                    if payload.get('revision') != s['revision']:
                        raise Problem(409, 'REVISION_CHANGED', '검토 내용이 변경되었습니다.')
                    if not payload.get('reason', '').strip():
                        raise Problem(422, 'REASON_REQUIRED', '원문과 대조한 내용을 기록하세요.')
                    if not out.get('analysis_run_id'):
                        raise Problem(409, 'NOT_AI_PROPOSAL', 'AI 변경안이 아닙니다.')
                    run = get(c, 'analysis_run', out['analysis_run_id'])
                    report = get(c, 'agent_report', run['agent_report_id'], True)
                    report.setdefault('confirmed_proposals', {})[id] = {'revision': s['revision'], 'reason': payload['reason'], 'actor_id': u['id'], 'created_at': now()}
                    put(c, 'agent_report', report)
                    validate(c, out)
                    revision(c, out, u['id'], 'AI 추정 필드 확인: ' + payload['reason'])
                    bump(out)
                elif action == 'decisions':
                    schema_check('DecisionInput', payload)
                    a = payload['action']
                    if payload['revision'] != s['revision']:
                        raise Problem(409, 'REVISION_CHANGED', '검토 내용이 변경되었습니다.')
                    if a not in actions(out)['summary']['allowed_actions']:
                        raise Problem(409, 'INVALID_TRANSITION', '현재 상태에서는 이 결정을 할 수 없습니다.')
                    if a == 'approve' and s['blocking_count']:
                        raise Problem(409, 'BLOCKERS', '확인이 필요한 항목을 해결하세요.')
                    if a != 'approve' and (not payload.get('reason', '').strip()):
                        raise Problem(422, 'REASON_REQUIRED', '사유를 입력하세요.')
                    out['decisions'].append({'id': uid(), 'action': a, 'revision': s['revision'], 'reason': payload.get('reason', ''), 'actor': public_user(u), 'created_at': now()})
                    s['status'] = {'approve': 'approved', 'reject': 'rejected', 'hold': 'on_hold'}[a]
                    s['approved_revision'] = s['revision'] if a == 'approve' else None
                    bump(out)
                elif action == 'withdraw-approval':
                    schema_check('ReasonInput', payload)
                    if s['status'] != 'approved':
                        raise Problem(409, 'INVALID_TRANSITION', '승인 상태에서만 철회할 수 있습니다.')
                    s.update(status='draft', approved_revision=None)
                    bump(out)
                elif action == 'applications':
                    schema_check('ApplicationInput', payload)
                    if payload['approved_revision'] != s['approved_revision']:
                        raise Problem(409, 'REVISION_CHANGED', '승인 내용이 변경되었습니다.')
                    existing = c.execute('SELECT data FROM applications WHERE proposal_id=%s AND approved_revision=%s', (id, s['approved_revision'])).fetchone()
                    if existing:
                        out = {'application': existing['data'], 'job': getjob(c, existing['data']['job_id'])}
                        status = 202
                    else:
                        if s['status'] != 'approved':
                            raise Problem(409, 'NOT_APPROVED', '승인된 변경안만 반영할 수 있습니다.')
                        a = {'id': uid(), 'proposal_id': id, 'approved_revision': s['approved_revision'], 'status': 'pending', 'created_at': now(), 'finished_at': None, 'audit_event_ids': [], 'actor_id': u['id']}
                        job = enqueue(c, 'apply', {'application_id': a['id'], 'actor_id': u['id']})
                        a['job_id'] = job['id']
                        c.execute('INSERT INTO applications(id,proposal_id,approved_revision,data) VALUES(%s,%s,%s,%s)', (a['id'], id, a['approved_revision'], Jsonb(a)))
                        s['status'] = 'applying'
                        out['application_id'] = a['id']
                        bump(out)
                        put(c, 'proposal', out)
                        out = {'application': a, 'job': job}
                        status = 202
                else:
                    raise Problem(404, 'NOT_FOUND', '지원하지 않는 작업입니다.')
                if action != 'applications':
                    put(c, 'proposal', out)
            elif action == 'revisions':
                out = page([r for r in records(c, 'proposal_revision') if r['proposal_id'] == id], q, c)
            if 'summary' in out:
                headers['ETag'] = etag(out)
    elif root == 'applications':
        r = c.execute('SELECT data FROM applications WHERE id=%s', (id,)).fetchone()
        if not r:
            raise Problem(404, 'NOT_FOUND', '반영 기록이 없습니다.')
        out = r['data']
    elif root == 'audit-events':
        out = get(c, 'audit', id)
    else:
        raise Problem(404, 'NOT_FOUND', '지원하지 않는 경로입니다.')
    return DomainResult(out, status, headers)

ROUTES = (('proposals', ('GET', 'POST')), ('proposals/{id}', ('GET', 'PATCH')), ('proposals/{id}/validate', ('POST',)), ('proposals/{id}/decisions', ('POST',)), ('proposals/{id}/withdraw-approval', ('POST',)), ('proposals/{id}/revisions', ('GET',)), ('proposals/{id}/applications', ('POST',)), ('applications/{id}', ('GET',)), ('audit-events/{id}', ('GET',)), ('proposals/{id}/confirm-ai', ('POST',)))

router = domain_router('review', ROUTES)
