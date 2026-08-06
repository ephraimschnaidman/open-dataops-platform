from __future__ import annotations

import csv
import re
import shutil
from pathlib import Path
from typing import Any

EXPECTED_ECOMMERCE_FILES = {
    "customers.csv", "products.csv", "orders.csv", "order_items.csv",
    "payments.csv", "web_events.csv",
}


def validate_ecommerce_dataset(directory: str | Path) -> list[Path]:
    root = Path(directory)
    if not root.is_dir():
        raise FileNotFoundError(f"Dataset directory does not exist: {root}")
    missing = sorted(name for name in EXPECTED_ECOMMERCE_FILES
                     if not (root / name).is_file())
    if missing:
        raise FileNotFoundError(f"Dataset is missing required files: {', '.join(missing)}")
    return [root / name for name in sorted(EXPECTED_ECOMMERCE_FILES)]


def copy_validation_dataset(source: str | Path, destination: str | Path) -> Path:
    source_path = Path(source)
    validate_ecommerce_dataset(source_path)
    destination_path = Path(destination)
    if destination_path.exists():
        raise FileExistsError(f"Temporary dataset already exists: {destination_path}")
    shutil.copytree(source_path, destination_path)
    validate_ecommerce_dataset(destination_path)
    return destination_path


def mutate_csv_value(
    path: str | Path, column: str, invalid_value: str,
) -> dict[str, Any]:
    csv_path = Path(path)
    temporary = csv_path.with_suffix(csv_path.suffix + ".tmp")
    mutation_count = 0
    original_value: str | None = None
    with csv_path.open("r", encoding="utf-8", newline="") as source, temporary.open(
        "w", encoding="utf-8", newline=""
    ) as destination:
        reader = csv.DictReader(source)
        if not reader.fieldnames or column not in reader.fieldnames:
            raise ValueError(f"CSV column not found: {column}")
        writer = csv.DictWriter(destination, fieldnames=reader.fieldnames)
        writer.writeheader()
        for row in reader:
            if mutation_count == 0 and row[column] != invalid_value:
                original_value = row[column]
                row[column] = invalid_value
                mutation_count = 1
            writer.writerow(row)
    if mutation_count != 1 or original_value is None:
        temporary.unlink(missing_ok=True)
        raise ValueError("Could not apply exactly one CSV mutation")
    temporary.replace(csv_path)
    return {"column": column, "original_value": original_value,
            "invalid_value": invalid_value, "mutation_count": mutation_count}


def verify_csv_mutation(path: str | Path, column: str, invalid_value: str) -> int:
    with Path(path).open("r", encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        if not reader.fieldnames or column not in reader.fieldnames:
            raise ValueError(f"CSV column not found: {column}")
        count = sum(row[column] == invalid_value for row in reader)
    if count != 1:
        raise ValueError(
            f"Expected exactly one {column}={invalid_value!r} mutation; found {count}"
        )
    return count


def write_airflow_dataset_override(
    path: str | Path, container_dataset_path: str,
) -> Path:
    if not container_dataset_path.startswith("/opt/airflow/runtime/validation/work/"):
        raise ValueError("Invalid temporary container dataset path")
    override_path = Path(path)
    override_path.parent.mkdir(parents=True, exist_ok=True)
    override_path.write_text(
        "services:\n"
        "  airflow-scheduler:\n"
        "    environment:\n"
        f"      ECOMMERCE_DATA_DIR: {container_dataset_path}\n"
        "  airflow-webserver:\n"
        "    environment:\n"
        f"      ECOMMERCE_DATA_DIR: {container_dataset_path}\n",
        encoding="utf-8",
    )
    return override_path


def resolve_airflow_task_logs(
    runtime_log_root: str | Path, dag_id: str, run_id: str, task_id: str,
) -> list[Path]:
    task_root = (
        Path(runtime_log_root) / f"dag_id={dag_id}" / f"run_id={run_id}"
        / f"task_id={task_id}"
    )
    return sorted(task_root.glob("attempt=*.log"))


def parse_dbt_failure_evidence(log_paths: list[Path]) -> dict[str, Any]:
    ansi = re.compile(r"\x1b\[[0-9;]*m")
    name_pattern = re.compile(
        r"accepted_values_(?:stg|fct)_payments_payment_method__[A-Za-z0-9_]+"
    )
    names: set[str] = set()
    excerpts: list[str] = []
    for path in log_paths:
        for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = ansi.sub("", raw_line).strip()
            names.update(name_pattern.findall(line))
            if (
                "accepted_values_" in line
                or ("Got " in line and "result" in line)
                or "Done. PASS=" in line
                or "Failure in test" in line
            ) and line not in excerpts:
                excerpts.append(line[:500])
    return {"test_names": sorted(names), "excerpts": excerpts[-30:]}
