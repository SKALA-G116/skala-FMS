"""Pricing HTTP use cases. The transport owns authentication and the transaction."""
import os
from backend.app.infrastructure.database import Problem
from backend.app.infrastructure.database import today
from backend.app.api.http import DomainResult
from backend.app.api.http import page
from backend.app.api.http import filtered
from backend.app.domains.catalog.queries import prices
from backend.app.api.routing import domain_router

def handle(ctx):
    c, req, method, q, payload = ctx.connection, ctx.request, ctx.method, ctx.query, ctx.payload
    content, u, path = ctx.content, ctx.actor, ctx.path
    parts, root, id, action = ctx.parts, ctx.root, ctx.id, ctx.action
    mutating = method != 'GET'
    status, headers = 200, {}
    if root == 'price-workbooks':
        from backend.app.domains.pricing.workbooks import import_workbook; from backend.app.domains.pricing.workbooks import metadata; from backend.app.domains.pricing.workbooks import register
        if id == 'import' and method == 'POST':
            out = import_workbook(c, payload['title'], content, payload['filename'])
            if os.getenv('FOOD_ANALYSIS_MODE', 'agent') != 'rules':
                from backend.app.domains.analysis.service import queue_analysis
                _, job = queue_analysis(c, out['document_revision_id'])
                out['analysis_job'] = job
            status = 201
        elif method == 'POST':
            if not payload.get('document_revision_id'):
                raise Problem(422, 'REVISION_REQUIRED', '원본 문서 버전이 필요합니다.')
            out = register(c, payload['document_revision_id'], payload.get('asset_id'))
            status = 201
        elif id:
            out = metadata(c, id)
        else:
            out = {'items': [{'id': str(r['id']), 'filename': r['filename'], 'document_id': str(r['document_id']), 'created_at': r['created_at'].isoformat()} for r in c.execute("SELECT * FROM price_workbooks w WHERE NOT EXISTS(SELECT 1 FROM record_archives a WHERE a.record_kind='document' AND a.record_id=w.document_id AND a.archived) ORDER BY created_at DESC,id DESC LIMIT 100")]}
    elif root == 'price-sheets' and action == 'header':
        from backend.app.domains.pricing.workbooks import set_header
        out = set_header(c, id, payload.get('header_row'))
        status = 200
    elif root == 'price-sheets' and action == 'proposals':
        from backend.app.domains.pricing.proposals import stage
        out = stage(c, id, payload)
        status = 201
    elif root == 'price-sheets' and action == 'rows':
        from backend.app.domains.pricing.workbooks import query_rows
        out = query_rows(c, id, q)
    elif root == 'prices':
        rows = prices(c, q.get('as_of'), q.get('include_scheduled') == 'true')
        for key in ('product_id', 'supplier_item_id', 'supplier_id'):
            if q.get(key):
                rows = [x for x in rows if (x['supplier']['id'] if key == 'supplier_id' else x[key]) == q[key]]
        from decimal import Decimal, InvalidOperation
        for key in ('amount_min', 'amount_max'):
            if q.get(key):
                try:
                    n = Decimal(q[key])
                    if not n.is_finite() or n < 0:
                        raise InvalidOperation()
                except InvalidOperation:
                    raise Problem(422, 'PRICE_RANGE', '유효한 단가 범위를 입력하세요.')
                rows = [x for x in rows if (Decimal(x['value']['amount']) >= n if key == 'amount_min' else Decimal(x['value']['amount']) <= n)]
        if q.get('spec'):
            rows = [x for x in rows if q['spec'].casefold() in x['spec_label'].casefold()]
        if q.get('supplier'):
            rows = [x for x in rows if q['supplier'].casefold() in x['supplier']['name'].casefold()]
        if q.get('unit'):
            rows = [x for x in rows if x['value']['unit'] == q['unit']]
        out = {**page(filtered(rows, q), q, c), 'as_of': q.get('as_of', today())}
    else:
        raise Problem(404, 'NOT_FOUND', '지원하지 않는 경로입니다.')
    return DomainResult(out, status, headers)

ROUTES = (('prices', ('GET',)), ('price-workbooks', ('GET', 'POST')), ('price-workbooks/import', ('POST',)), ('price-workbooks/{id}', ('GET',)), ('price-sheets/{id}/rows', ('GET',)), ('price-sheets/{id}/proposals', ('POST',)), ('price-sheets/{id}/header', ('POST',)))

router = domain_router('pricing', ROUTES)
