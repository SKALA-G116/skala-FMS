"""Compatibility entry point; new code uses domains.jobs.service."""
import importlib
import sys
module = importlib.import_module("backend.app.domains.jobs.service")
sys.modules[__name__] = module
