"""Compatibility entry point; new code uses domains.jobs.worker."""
import importlib
import sys
module = importlib.import_module("backend.app.domains.jobs.worker")
if __name__ == "__main__":
    module.main()
else:
    sys.modules[__name__] = module
