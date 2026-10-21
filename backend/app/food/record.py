"""Compatibility entry point; new code uses domains.catalog.record."""
import importlib
import sys
module = importlib.import_module("backend.app.domains.catalog.record")
sys.modules[__name__] = module
