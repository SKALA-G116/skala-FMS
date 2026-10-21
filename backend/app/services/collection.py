"""Compatibility entry point; new code uses domains.ingestion.collection."""
import importlib
import sys
module = importlib.import_module("backend.app.domains.ingestion.collection")
from backend.app.domains.analysis.service import queue_analysis
module.queue_analysis = queue_analysis
sys.modules[__name__] = module
