"""Compatibility entry point; new code uses domains.analysis.agent."""
import importlib
import sys
module = importlib.import_module("backend.app.domains.analysis.agent")
sys.modules[__name__] = module
