"""Keep domain routing and dependency boundaries intact as the service grows."""
import ast
import importlib
import re
from pathlib import Path
from backend.app.api.main import app
from backend.app.api.registry import DOMAINS, HANDLERS
from backend.app.api.http import DomainResult


def test_every_public_domain_operation_has_one_owner_and_unique_openapi_id():
    seen = set()
    schema = app.openapi()
    operation_ids = []
    for domain in DOMAINS:
        for path, methods in domain.ROUTES:
            assert HANDLERS[path.split('/')[0]] is domain.handle
            documented = schema['paths']['/api/v1/' + path]
            for method in methods:
                key = (path, method)
                assert key not in seen, key
                seen.add(key)
                operation = documented[method.lower()]
                assert operation['tags'] == [domain.__name__.split('.')[-2]]
                operation_ids.append(operation['operationId'])
                declared = {p['name'] for p in operation.get('parameters', []) if p['in'] == 'path'}
                assert declared == set(re.findall(r'\{([^}]+)\}', path))
    assert len(seen) >= 60
    assert len(set(operation_ids)) == len(operation_ids)
    assert '/api/v1/{path}' not in schema['paths']


def test_canonical_domains_do_not_depend_on_compatibility_modules_or_app_bootstrap():
    root = Path(__file__).parents[1] / 'app' / 'domains'
    forbidden = ('backend.app.services', 'backend.app.ai', 'backend.app.food', 'backend.app.domain.', 'backend.app.workflows', 'backend.app.workers', 'backend.app.db', 'backend.app.api.main')
    for file in root.rglob('*.py'):
        for node in ast.walk(ast.parse(file.read_text())):
            if isinstance(node, ast.ImportFrom):
                assert not node.level, (file, node.module)
                assert not (node.module or '').startswith(forbidden), (file, node.module)
                assert all(a.name != '*' for a in node.names), file


def test_catalog_queries_do_not_own_catalog_mutations():
    from backend.app.domains.catalog import queries
    from backend.app.domains.review.application import apply
    assert not hasattr(queries, 'apply')
    assert callable(apply)


def test_legacy_module_paths_share_database_and_model_instances():
    assert importlib.import_module('backend.app.db') is importlib.import_module('backend.app.infrastructure.database')
    assert importlib.import_module('backend.app.ai.provider') is importlib.import_module('backend.app.domains.analysis.provider')
    assert importlib.import_module('backend.app.food.record') is importlib.import_module('backend.app.domains.catalog.record')


def test_response_headers_are_not_shared_between_requests():
    first, second = DomainResult({}), DomainResult({})
    first.headers['ETag'] = 'one'
    assert second.headers == {}
