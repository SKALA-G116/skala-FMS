"""Compatibility entry point; new code uses domains.ingestion.archives."""
import importlib
import sys
module = importlib.import_module("backend.app.domains.ingestion.archives")
sys.modules[__name__] = module
