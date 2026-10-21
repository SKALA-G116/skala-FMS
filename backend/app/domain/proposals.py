"""Compatibility entry point; new code uses domains.review.proposals."""
import importlib
import sys
module = importlib.import_module("backend.app.domains.review.proposals")
from backend.app.infrastructure.contracts import SPEC, schema_check
module.SPEC = SPEC
module.schema_check = schema_check
sys.modules[__name__] = module
