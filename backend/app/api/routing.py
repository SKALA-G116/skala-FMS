"""Create explicit domain paths with unique operations and documented path parameters."""
import re
from fastapi import APIRouter, Request


def domain_router(domain, routes):
    router = APIRouter(prefix='/api/v1', tags=[domain])
    for path, methods in routes:
        parameters = [
            {'name': name, 'in': 'path', 'required': True, 'schema': {'type': 'string'}}
            for name in re.findall(r'\{([^}]+)\}', path)
        ]
        for method in methods:
            async def endpoint(req: Request):
                from .transport import process_request
                return await process_request(req.url.path.removeprefix('/api/v1/'), req)

            operation = domain + '_' + method.lower() + '_' + re.sub(r'[^a-zA-Z0-9_]', '_', path)
            endpoint.__name__ = operation
            router.add_api_route(
                '/' + path, endpoint, methods=[method], operation_id=operation,
                openapi_extra={'parameters': parameters},
            )
    return router
