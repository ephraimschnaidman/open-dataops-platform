"""Backward-compatible wrapper for the canonical platform bootstrap job."""
import importlib.util
from pathlib import Path
import sys

job_path = Path(__file__).resolve().parents[1] / "platform" / "jobs" / "bootstrap_raw_data.py"
spec = importlib.util.spec_from_file_location("bootstrap_raw_data_job", job_path)
if spec is None or spec.loader is None:
    raise ImportError(f"Unable to load canonical bootstrap job: {job_path}")
job = importlib.util.module_from_spec(spec)
spec.loader.exec_module(job)
main = job.main

if __name__ == "__main__":
    sys.exit(main())
