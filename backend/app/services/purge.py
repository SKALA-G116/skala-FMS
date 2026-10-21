"""Compatibility entry point; new code uses domains.ingestion.purge."""
import importlib
import sys
module = importlib.import_module("backend.app.domains.ingestion.purge")
sys.modules[__name__] = module
