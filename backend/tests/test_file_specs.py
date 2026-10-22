"""
==============================================================================
FMS_FILE_SPEC
test_file_specs.py - 기능·경계·회귀 검증
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
    2026-10-21  미지정      v0.1.0   파일 역할·입출력·가정·이력 명세 추가

    상세 Git 이력: git log --follow -- backend/tests/test_file_specs.py
    공통 규칙: doc/file-header-policy.md

기존 모듈 설명:
    Check that documenting source files preserves executable code and original inputs.
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
import importlib.util
from pathlib import Path

MODULE = Path(__file__).resolve().parents[2] / 'scripts/file-specs.py'
loader = importlib.util.spec_from_file_location('file_specs', MODULE)
file_specs = importlib.util.module_from_spec(loader)
loader.loader.exec_module(file_specs)


def test_python_header_preserves_future_unicode_docstring_and_decorator(tmp_path, monkeypatch):
    monkeypatch.setattr(file_specs, 'ROOT', tmp_path)
    original = '#!/usr/bin/env python3\n# coding: utf-8\n"""한글 원문 설명."""\nfrom __future__ import annotations\n\ndef decorate(cls):\n    return cls\n\n@decorate\nclass Example:\n    field: Example | None = None\n'
    path = tmp_path / 'example.py'
    path.write_text(original)
    meta = {'spec': file_specs.spec('example.py'), 'style': 'python', 'created': '2026-10-21', 'documented': '2026-10-21', 'git_history': []}
    file_specs.apply_header('example.py', meta)
    updated = path.read_text()
    assert updated.startswith('#!/usr/bin/env python3\n# coding: utf-8\n')
    assert meta['original_docstring'] == '한글 원문 설명.'
    assert '한글 원문 설명.' in ast.get_docstring(ast.parse(updated))
    namespace = {}
    exec(compile(updated, str(path), 'exec'), namespace)
    assert namespace['Example'].__annotations__ == {'field': 'Example | None'}
    assert namespace['__author__'] == '김재현(Finn)'
    assert namespace['__email__']=='penguin.klg@gmail.com'
    file_specs.apply_header('example.py', meta)
    assert path.read_text() == updated


def test_marker_literal_does_not_hide_missing_header():
    assert not file_specs.has_header("MARKER = 'FMS_FILE_SPEC'\n")
    assert file_specs.has_header('/*\nFMS_FILE_SPEC\n*/\n')


def test_external_formats_preserve_raw_and_legacy_contracts():
    for path in ['doc/food-agent/prompts/notice-v1.md', 'doc/food-agent/policies/food-policy-v1.md', 'data/raw.json', 'data/raw.csv', 'frontend/package-lock.json', 'legacy/incident_agent/server.py', 'doc/submission/demo/notice.txt']:
        assert file_specs.style(path) == 'external'
