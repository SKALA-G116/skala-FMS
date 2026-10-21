"""Compatibility entry point; new code uses domains.pricing.proposals."""
import importlib
import sys
module = importlib.import_module("backend.app.domains.pricing.proposals")
sys.modules[__name__] = module
