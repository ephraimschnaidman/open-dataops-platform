from __future__ import annotations
import logging
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DBT_DIR = REPO_ROOT / "platform" / "dbt"
ARTIFACT_DIR = Path(os.getenv("DBT_ARTIFACT_ROOT", REPO_ROOT / "runtime" / "dbt")) / "test"
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)


def main() -> int:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    command = ["dbt", "test", "--project-dir", str(DBT_DIR), "--profiles-dir", str(DBT_DIR),
               "--target-path", str(ARTIFACT_DIR)]
    logger.info("Starting dbt test")
    try:
        result = subprocess.run(command, cwd=REPO_ROOT, check=False)
    except OSError:
        logger.exception("Unable to execute dbt test")
        return 1
    if result.returncode:
        logger.error("dbt test failed", extra={"exit_code": result.returncode})
    else:
        logger.info("dbt test complete")
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
