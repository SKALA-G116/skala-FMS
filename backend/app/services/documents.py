"""Compatibility entry point; new code uses domains.ingestion.documents."""
import importlib
import sys
module = importlib.import_module("backend.app.domains.ingestion.documents")
sys.modules[__name__] = module
