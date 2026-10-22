"""
==============================================================================
FMS_FILE_SPEC
api.py - catalog 도메인 HTTP 유스케이스
==============================================================================
설명:
    - catalog 도메인 HTTP 유스케이스
입력·출력 명세:
    - 입력: 인증·권한·CSRF를 확인한 RequestContext와 경로/조회/본문
    - 출력: DomainResult 또는 HTTP Response
실행 가정:
    - 공통 transport가 소유한 같은 DB 트랜잭션을 사용
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

    2026-10-22  김재현(Finn) v0.1.0   자료·Agent·검수 승인·식품 DB 중심 흐름 및 알레르기 표기 정리

    상세 Git 이력: git log --follow -- backend/app/domains/catalog/api.py
    공통 규칙: doc/file-header-policy.md

기존 모듈 설명:
    Catalog HTTP use cases. The transport owns authentication and the transaction.
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

from backend.app.infrastructure.database import Problem
from backend.app.infrastructure.database import entities
from backend.app.infrastructure.database import entity
from backend.app.infrastructure.database import put
from backend.app.infrastructure.database import records
from backend.app.infrastructure.database import uid
from backend.app.api.http import DomainResult
from backend.app.api.http import page
from backend.app.api.http import filtered
from backend.app.domains.catalog.queries import product_detail
from backend.app.domains.catalog.queries import item_detail
from backend.app.domains.catalog.queries import active_facts
from backend.app.domains.catalog.queries import foods
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
    if root == 'suppliers':
        if method == 'POST':
            name = payload.get('name', '').strip()
            if not 1 <= len(name) <= 200:
                raise Problem(422, 'SUPPLIER_NAME', '업체명을 입력하세요.')
            existing = next((s for s in records(c, 'supplier') if s['name'] == name), None)
            out = existing or put(c, 'supplier', {'id': uid(), 'name': name, 'roles': ['supplier'], 'aliases': []})
            status = 201
        else:
            out = page(records(c, 'supplier'), q, c)
    elif root == 'foods':
        if method=='PATCH':
            from backend.app.domains.catalog.editing import update_food
            out=update_food(c,id,payload,req,u['id'])
            headers['ETag']='"'+str(out['version'])+'"'
        else:out = foods(c, q)
    elif root == 'products':
        if not id:
            out = page(filtered(entities(c, 'product'), q), q, c)
        elif action == 'history':
            out = page([x for x in records(c, 'audit') if x['product_id'] == id], q, c)
        elif action == 'variants':
            out = page([v for v in entities(c, 'variant') if v['product_id'] == id], q, c)
        else:
            out = product_detail(c, id, q.get('as_of'))
    elif root == 'supplier-items':
        if action == 'substitutions':
            out = page(active_facts(c, id, 'set_substitution', q.get('as_of'), q.get('include_scheduled') == 'true'), q, c)
        else:
            rows = entities(c, 'supplier_item')
            for key in ('variant_id', 'supplier_id'):
                if q.get(key):
                    rows = [x for x in rows if x[key] == q[key]]
            if q.get('product_id'):
                rows = [x for x in rows if entity(c, x['variant_id'])['product_id'] == q['product_id']]
            out = page([item_detail(c, x, q.get('as_of')) for x in rows], q, c)
    else:
        raise Problem(404, 'NOT_FOUND', '지원하지 않는 경로입니다.')
    return DomainResult(out, status, headers)

ROUTES = (('suppliers', ('GET', 'POST')), ('products', ('GET',)), ('products/{id}', ('GET',)), ('supplier-items', ('GET',)), ('products/{id}/history', ('GET',)), ('supplier-items/{id}/substitutions', ('GET',)), ('products/{id}/variants', ('GET',)), ('foods', ('GET',)), ('foods/{id}', ('DELETE','PATCH')), ('foods/{id}/restore', ('POST',)))

router = domain_router('catalog', ROUTES)
