"""Authenticated session reads and logout; login/CSRF are pre-auth transport hooks."""
import hashlib
from fastapi.responses import Response
from backend.app.api.http import DomainResult
from backend.app.domains.identity.service import public_user
from backend.app.api.routing import domain_router

def handle(ctx):
    if ctx.path == 'auth/me':
        return DomainResult(public_user(ctx.actor))
    ctx.connection.execute('DELETE FROM sessions WHERE token_hash=%s', (hashlib.sha256(ctx.request.cookies['food_session'].encode()).hexdigest(),))
    response = Response(status_code=204)
    response.delete_cookie('food_session')
    response.delete_cookie('food_csrf')
    return response

ROUTES = (('auth/csrf', ('GET',)), ('auth/session', ('DELETE', 'POST')), ('auth/me', ('GET',)))

router = domain_router('identity', ROUTES)
