"""Compatibility entry point; new code uses domains.review.items."""
import importlib
import sys
module = importlib.import_module("backend.app.domains.review.items")
sys.modules[__name__] = module
