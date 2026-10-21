"""Compatibility entry point; new code uses infrastructure.database."""
import importlib
import sys
module = importlib.import_module("backend.app.infrastructure.database")
sys.modules[__name__] = module
