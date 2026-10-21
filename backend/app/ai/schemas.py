"""Compatibility entry point; new code uses domains.analysis.schemas."""
import importlib
import sys
module = importlib.import_module("backend.app.domains.analysis.schemas")
sys.modules[__name__] = module
