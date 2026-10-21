"""Compatibility entry point; new code uses domains.analysis.provider."""
import importlib
import sys
module = importlib.import_module("backend.app.domains.analysis.provider")
sys.modules[__name__] = module
