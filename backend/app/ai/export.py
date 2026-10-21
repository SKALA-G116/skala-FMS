"""Compatibility entry point; new code uses domains.analysis.export."""
import importlib
import sys
module = importlib.import_module("backend.app.domains.analysis.export")
sys.modules[__name__] = module
