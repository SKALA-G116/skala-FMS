"""
==============================================================================
FMS_FILE_SPEC
validate_contract.py - 프로젝트 문서 validate_contract
==============================================================================
설명:
    - 프로젝트 문서 validate_contract
입력·출력 명세:
    - 입력: 설계·구현·측정·검증 근거
    - 출력: 설명·명세·예제·검증 또는 발표 안내
실행 가정:
    - 계획·테스트 대역·실제 실행 결과를 구분하고 현재 상태는 README 및 검증 근거 확인
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

    상세 Git 이력: git log --follow -- doc/food-agent/validate_contract.py
    공통 규칙: doc/file-header-policy.md

기존 모듈 설명:
    Stdlib-only checks for this draft; not a complete OpenAPI validator.
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

import copy
import datetime as dt
import json
from pathlib import Path
import re
import uuid

ROOT = Path(__file__).resolve().parent
SPEC = json.loads((ROOT / "openapi.json").read_text())


def resolve(pointer):
    assert pointer.startswith("#/"), f"External reference not checked: {pointer}"
    value = SPEC
    for part in pointer[2:].split("/"):
        value = value[part.replace("~1", "/").replace("~0", "~")]
    return value


def validate(value, schema, path="$"):
    if "$ref" in schema:
        return validate(value, resolve(schema["$ref"]), path)
    for keyword in ("oneOf", "anyOf"):
        if keyword in schema:
            matches = 0
            for branch in schema[keyword]:
                try:
                    validate(value, branch, path)
                    matches += 1
                except AssertionError:
                    pass
            assert matches == 1 if keyword == "oneOf" else matches >= 1, (path, keyword, matches)
    if "const" in schema:
        assert value == schema["const"], (path, "const")
    if "enum" in schema:
        assert value in schema["enum"], (path, "enum")
    kind = schema.get("type")
    if kind == "null":
        assert value is None, (path, kind)
    elif kind == "object":
        assert isinstance(value, dict), (path, kind)
        for key in schema.get("required", []):
            assert key in value, (path, "missing", key)
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            assert not set(value) - set(properties), (path, "extra", set(value) - set(properties))
        if "minProperties" in schema:
            assert len(value) >= schema["minProperties"], (path, "minProperties")
        for key, item in value.items():
            if key in properties:
                validate(item, properties[key], f"{path}.{key}")
    elif kind == "array":
        assert isinstance(value, list), (path, kind)
        assert len(value) >= schema.get("minItems", 0), (path, "minItems")
        if "maxItems" in schema:
            assert len(value) <= schema["maxItems"], (path, "maxItems")
        if schema.get("uniqueItems"):
            normalized = [json.dumps(item, sort_keys=True) for item in value]
            assert len(set(normalized)) == len(value), (path, "uniqueItems")
        for index, item in enumerate(value):
            validate(item, schema["items"], f"{path}[{index}]")
    elif kind == "string":
        assert isinstance(value, str), (path, kind)
        assert len(value) >= schema.get("minLength", 0), (path, "minLength")
        if "maxLength" in schema:
            assert len(value) <= schema["maxLength"], (path, "maxLength")
        if "pattern" in schema:
            assert re.search(schema["pattern"], value), (path, "pattern")
        try:
            if schema.get("format") == "uuid":
                uuid.UUID(value)
            elif schema.get("format") == "date":
                assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", value), (path, "date")
                dt.date.fromisoformat(value)
            elif schema.get("format") == "date-time":
                parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
                assert parsed.tzinfo is not None, (path, "timezone")
            elif schema.get("format") == "uri":
                assert re.match(r"^https?://[^/]+", value), (path, "uri")
        except (ValueError, TypeError) as error:
            raise AssertionError((path, "format")) from error
    elif kind in ("integer", "number"):
        valid_type = isinstance(value, int) if kind == "integer" else isinstance(value, (int, float))
        assert valid_type and not isinstance(value, bool), (path, kind)
        if "minimum" in schema:
            assert value >= schema["minimum"], (path, "minimum")
        if "maximum" in schema:
            assert value <= schema["maximum"], (path, "maximum")
    elif kind == "boolean":
        assert isinstance(value, bool), (path, kind)


def walk(value):
    yield value
    if isinstance(value, dict):
        for item in value.values():
            yield from walk(item)
    elif isinstance(value, list):
        for item in value:
            yield from walk(item)


def main():
    reference_count = 0
    for item in walk(SPEC):
        if isinstance(item, dict) and "$ref" in item:
            resolve(item["$ref"])
            reference_count += 1
        if isinstance(item, dict) and item.get("type") == "object":
            assert set(item.get("required", [])) <= set(item.get("properties", {}))
    operations = []
    for path, methods in SPEC["paths"].items():
        for method, operation in methods.items():
            assert method in ("get", "post", "patch", "delete")
            operations.append(operation["operationId"])
            parameters = [resolve(p["$ref"]) if "$ref" in p else p for p in operation.get("parameters", [])]
            assert set(re.findall(r"\{([^}]+)\}", path)) == {p["name"] for p in parameters if p["in"] == "path"}
            parameter_pairs = [(p["in"], p["name"]) for p in parameters]
            assert len(parameter_pairs) == len(set(parameter_pairs))
            if method != "get":
                assert ("header", "X-CSRF-Token") in parameter_pairs
                if operation["tags"] != ["Auth"]:
                    assert ("header", "Idempotency-Key") in parameter_pairs
            if "security" in operation and operation["security"] == []:
                assert operation["x-required-roles"] == []
    assert len(operations) == len(set(operations))

    manifest = json.loads((ROOT / "examples/manifest.json").read_text())
    fixtures = {}
    for name, schema_name in manifest.items():
        value = json.loads((ROOT / "examples" / name).read_text())
        validate(value, SPEC["components"]["schemas"][schema_name], name)
        fixtures[name] = value
    for example in SPEC["components"].get("examples", {}).values():
        assert "value" in example

    negative = [
        ("money must be string", 12500, "PriceValue", "amount"),
        ("money must be nonnegative", "-1", "PriceValue", "amount"),
        ("unsupported availability", "deleted", "SetAvailability", "status"),
        ("malformed uuid", "not-a-uuid", "Evidence", "id"),
        ("bbox length", [0, 0, 1], "ImageLocator", "bbox"),
    ]
    base = {
        "PriceValue": fixtures["price-list.json"]["items"][0]["value"],
        "SetAvailability": fixtures["proposal-ready.json"]["changes"][0]["operation"],
        "Evidence": fixtures["evidence.json"],
        "ImageLocator": fixtures["evidence.json"]["locator"],
    }
    for label, bad, schema_name, field in negative:
        candidate = copy.deepcopy(base[schema_name])
        candidate[field] = bad
        try:
            validate(candidate, SPEC["components"]["schemas"][schema_name])
        except AssertionError:
            pass
        else:
            raise AssertionError(f"Negative case accepted: {label}")
    try:
        validate({"id": fixtures["evidence.json"]["id"], "local_ref": "new_item"}, SPEC["components"]["schemas"]["EntityRef"])
    except AssertionError:
        pass
    else:
        raise AssertionError("EntityRef must not have both id and local_ref")

    evidence_id = fixtures["evidence.json"]["id"]
    for name in ("proposal-ready.json", "proposal-approved.json"):
        proposal = fixtures[name]
        assert proposal["summary"]["change_count"] == len(proposal["changes"])
        for change in proposal["changes"]:
            for binding in change["field_evidence"]:
                assert evidence_id in binding["evidence_ids"]
                value = change["operation"]
                for token in binding["field_path"].strip("/").split("/"):
                    value = value[token.replace("~1", "/").replace("~0", "~")]
    ready = fixtures["proposal-ready.json"]["summary"]
    approved = fixtures["proposal-approved.json"]["summary"]
    assert approved["revision"] == ready["revision"] == approved["approved_revision"]
    assert approved["version"] > ready["version"]
    application = fixtures["application-accepted.json"]["application"]
    assert application["proposal_id"] == approved["id"]
    assert application["approved_revision"] == approved["revision"]
    price_list = fixtures["price-list.json"]
    assert price_list["items"][0]["period"]["effective_from"] > price_list["as_of"]
    assert price_list["items"][0]["effective_state"] == "scheduled"
    x0, y0, x1, y1 = fixtures["evidence.json"]["locator"]["bbox"]
    assert 0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1

    missing_links = []
    for document in ROOT.glob("*.md"):
        for link in re.findall(r"\]\((\./[^)]+)\)", document.read_text()):
            if not (document.parent / link.split("#")[0]).exists():
                missing_links.append((document.name, link))
    assert not missing_links, missing_links
    assert not re.search(r"[\u3040-\u30ff]", (ROOT / "openapi.json").read_text())
    report = {
        "status": "passed",
        "openapi_version": SPEC["openapi"],
        "path_count": len(SPEC["paths"]),
        "operation_count": len(operations),
        "schema_count": len(SPEC["components"]["schemas"]),
        "resolved_local_references": reference_count,
        "valid_fixture_count": len(manifest),
        "rejected_invalid_fixture_count": len(negative) + 1,
        "checks": ["local references", "unique operation IDs", "path parameters", "CSRF/idempotency headers", "example schema subset", "fixture cross-links and approval versions", "future effective date", "bbox geometry", "Markdown local links"],
        "limitations": ["Not a complete OpenAPI/JSON Schema validator", "No server or Vue implementation tested", "No OCR engine or real source file accuracy measured", "No DB transaction, concurrency, or worker recovery test executed"],
    }
    (ROOT / "validation-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
