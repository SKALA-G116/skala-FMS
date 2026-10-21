"""Compatibility entry point; new code uses domains.analysis.workflow."""
import importlib
import sys
module = importlib.import_module("backend.app.domains.analysis.workflow")
sys.modules[__name__] = module
