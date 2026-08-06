from __future__ import annotations

import json
import os
from pathlib import Path

from .models import ValidationResult


def write_report(result: ValidationResult, report_dir: str | Path | None = None) -> Path:
    directory = Path(report_dir or os.getenv("VALIDATION_REPORT_DIR", "runtime/validation/reports"))
    directory.mkdir(parents=True, exist_ok=True)
    stamp = result.started_at.replace(":", "").replace("-", "").replace(".", "")
    base = directory / f"{result.test_name}_{stamp}.json"
    path = base
    counter = 1
    while path.exists():
        path = base.with_name(f"{base.stem}_{counter}{base.suffix}")
        counter += 1
    path.write_text(json.dumps(result.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def print_summary(result: ValidationResult, report_path: Path | None = None) -> None:
    print(f"[{result.status.value}] {result.test_name}: {result.summary} ({result.duration_seconds:.2f}s)")
    if report_path:
        print(f"Report: {report_path}")
