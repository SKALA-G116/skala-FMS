"""
==============================================================================
FMS_FILE_SPEC
validate_design.py - 프로젝트 문서 validate_design
==============================================================================
설명:
    - 프로젝트 문서 validate_design
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

    상세 Git 이력: git log --follow -- doc/food-agent/validate_design.py
    공통 규칙: doc/file-header-policy.md

기존 모듈 설명:
    Check v0.2 design artifacts, not a running MCP server or resource benchmark.
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

from collections import Counter
import copy
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def load(name):
    return json.loads((ROOT / name).read_text())


def main():
    module_spec = importlib.util.spec_from_file_location("food_contract_checker", ROOT / "validate_contract.py")
    checker = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(checker)
    api = load("openapi.json")
    manifest = load("mcp-capabilities.json")
    policy = load("runtime-policy.json")
    checklist = load("review-checklist.json")
    assert api["info"]["version"] == manifest["version"] == checklist["version"] == "0.2.0-draft"
    assert manifest["design_manifest_only"] is True
    assert len(manifest["tools"]) == 6
    assert len(manifest["resources"]) == 5
    assert len(manifest["prompts"]) == 3
    assert set(manifest["model_tool_allowlist"]) == {
        "find_product_candidates", "get_supplier_item_facts", "get_product_history"
    }
    assert not set(manifest["model_tool_allowlist"]) & set(manifest["forbidden_model_capabilities"])
    assert len({tool["name"] for tool in manifest["tools"]}) == len(manifest["tools"])
    for tool in manifest["tools"]:
        assert tool["description"] and tool["inputSchema"]["type"] == "object"
        assert tool["outputSchema"]["type"] == "object"
        assert tool["max_result_bytes"] == policy["limits"]["max_tool_result_bytes"]
        assert (tool["name"] in manifest["model_tool_allowlist"]) == (tool["exposure"] == "model_allowed")
        if tool["exposure"] == "model_allowed":
            assert tool["annotations"]["readOnlyHint"] is True

    file_hashes = 0
    for artifact in manifest["resources"] + manifest["prompts"]:
        if "source_file" not in artifact:
            continue
        path = ROOT / artifact["source_file"]
        assert path.is_file(), path
        assert hashlib.sha256(path.read_bytes()).hexdigest() == artifact["sha256"], path
        if "uriTemplate" in artifact:
            assert path.stat().st_size <= policy["limits"]["max_resource_segment_bytes"], path
        file_hashes += 1

    resource_schema = load("schemas/food-change-v1.json")
    for node in checker.walk(resource_schema):
        if isinstance(node, dict) and "$ref" in node:
            target = resource_schema
            assert node["$ref"].startswith("#/")
            for token in node["$ref"][2:].split("/"):
                target = target[token]

    def normalize(value):
        if isinstance(value, dict):
            return {
                key: item.replace("#/$defs/", "#/components/schemas/")
                if key == "$ref" else normalize(item)
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [normalize(item) for item in value]
        return value

    for name, schema in resource_schema["$defs"].items():
        assert normalize(schema) == api["components"]["schemas"][name], name

    by_name = {tool["name"]: tool for tool in manifest["tools"]}
    valid_input = {"query": "가상 식품 40~50g", "as_of": "2026-10-20", "limit": 10}
    checker.validate(valid_input, by_name["find_product_candidates"]["inputSchema"])
    invalid = []
    for label, payload in [
        ("extra SQL argument", {**valid_input, "sql": "SELECT * FROM products"}),
        ("unbounded result count", {**valid_input, "limit": 10000}),
    ]:
        try:
            checker.validate(payload, by_name["find_product_candidates"]["inputSchema"])
        except AssertionError:
            invalid.append(label)
        else:
            raise AssertionError(label)
    parse_tool = by_name["parse_document_segment"]
    try:
        checker.validate({"url": "https://example.com/file"}, parse_tool["inputSchema"])
    except AssertionError:
        invalid.append("arbitrary parse URL")
    else:
        raise AssertionError("arbitrary parse URL")

    examples = load("examples/manifest.json")
    proposal = load("examples/proposal-ready.json")
    job = load("examples/job-analyzed.json")
    run = load("examples/analysis-run.json")
    assert proposal["analysis_run_id"] == job["analysis_run_id"] == run["id"]
    assert job["id"] in run["job_ids"]
    assert job["id"] != run["id"]
    assert proposal["summary"]["id"] in run["proposal_ids"]
    assert len(checklist["items"]) == 34
    assert len({item["id"] for item in checklist["items"]}) == 34
    assert all(item["verification"] and item["owner"] for item in checklist["items"])
    assert all(1 <= p <= 253 for item in checklist["items"] for p in item["pdf_pages"])
    limits = policy["limits"]
    assert limits["ocr_workers_per_deployment"] == limits["ocr_tasks_per_worker"] == 1
    assert limits["max_transport_attempts"] == 3
    assert limits["max_checkpoint_state_bytes"] > limits["max_tool_result_bytes"]
    assert len(policy["required_deployment_values"]) == 3
    statuses = dict(Counter(item["review_status"] for item in checklist["items"]))
    report = {
        "status": "design_consistency_passed",
        "operational_readiness": "NOT_VERIFIED",
        "rest_operations": sum(len(value) for value in api["paths"].values()),
        "mcp_tools": len(manifest["tools"]),
        "model_allowed_tools": len(manifest["model_tool_allowlist"]),
        "resource_templates": len(manifest["resources"]),
        "prompt_templates": len(manifest["prompts"]),
        "resource_prompt_hashes_verified": file_hashes,
        "resource_schema_definitions_consistent": len(resource_schema["$defs"]),
        "fixture_count": len(examples),
        "additional_invalid_tool_inputs_rejected": invalid,
        "checklist_statuses": statuses,
        "unresolved_deployment_values": list(policy["required_deployment_values"]),
        "not_executed": [
            "Actual MCP initialize/list/read/get/call or Inspector test",
            "PaddleOCR accuracy, RAM/VRAM, sustained load or browser heap tests",
            "PostgreSQL saver, lease fencing or commit recovery tests",
            "Full OpenAPI/JSON Schema standards validation",
        ],
    }
    (ROOT / "design-review-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
