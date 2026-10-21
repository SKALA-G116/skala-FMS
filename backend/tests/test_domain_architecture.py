"""
==============================================================================
FMS_FILE_SPEC
test_domain_architecture.py - 기능·경계·회귀 검증
==============================================================================
설명:
    - 기능·경계·회귀 검증
입력·출력 명세:
    - 입력: 테스트 fixture·가상 입력·명시적 mock/테스트 대역
    - 출력: assert 결과와 실패 사유
실행 가정:
    - DB 통합 테스트는 별도 _test DB·임시 assets 사용; 대역과 실제 모델 검증을 구분
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

    상세 Git 이력: git log --follow -- backend/tests/test_domain_architecture.py
    공통 규칙: doc/file-header-policy.md

기존 모듈 설명:
    Keep domain routing and dependency boundaries intact as the service grows.
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
