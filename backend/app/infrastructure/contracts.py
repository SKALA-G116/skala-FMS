"""Versioned JSON contracts shared by HTTP, MCP and application services."""
import json
from jsonschema import Draft202012Validator
from jsonschema import FormatChecker
from backend.app.infrastructure.database import ROOT
from backend.app.infrastructure.database import Problem

SPEC=json.loads((ROOT/'doc/food-agent/openapi.json').read_text())

def schema_check(name,data):
    schema={'$ref':f'#/components/schemas/{name}','components':SPEC['components']}
    errors=list(Draft202012Validator(schema,format_checker=FormatChecker()).iter_errors(data))
    if errors: raise Problem(422,'INVALID_INPUT','입력값의 형식이 올바르지 않습니다.',[{'path':'/'.join(map(str,e.absolute_path)), 'message':e.message} for e in errors[:10]])
