"""Compatibility entry point; new code uses domains.pricing.workbooks."""
import importlib
import sys
module = importlib.import_module("backend.app.domains.pricing.workbooks")
sys.modules[__name__] = module
