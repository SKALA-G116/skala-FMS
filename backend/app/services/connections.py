"""Compatibility entry point; new code uses domains.ingestion.connections."""
import importlib
import sys
module = importlib.import_module("backend.app.domains.ingestion.connections")
sys.modules[__name__] = module
