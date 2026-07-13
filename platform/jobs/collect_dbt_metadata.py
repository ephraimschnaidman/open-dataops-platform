from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import psycopg
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ARTIFACT_ROOT = REPO_ROOT / "runtime" / "dbt"
ID_NAMESPACE = uuid.UUID("14c69470-a231-4a97-8ff2-e10e445bce52")
logger = logging.getLogger(__name__)


class ArtifactValidationError(ValueError):
    """Raised when a dbt run_results artifact is missing required data."""


@dataclass(frozen=True)
class DbtNodeResult:
    invocation_id: str
    command_type: str
    node_unique_id: str
    node_name: str
    resource_type: str
    execution_status: str
    execution_time_seconds: float
    message: str | None


def _required(mapping: dict[str, Any], field: str, location: str) -> Any:
    value = mapping.get(field)
    if value is None or value == "":
        raise ArtifactValidationError(f"Missing required field '{field}' in {location}")
    return value


def parse_run_results(path: Path, command_type: str) -> list[DbtNodeResult]:
    if command_type not in {"run", "test"}:
        raise ValueError(f"Unsupported dbt command type: {command_type}")
    try:
        artifact = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ArtifactValidationError(f"dbt artifact not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ArtifactValidationError(f"Invalid JSON in dbt artifact {path}: {exc}") from exc
    if not isinstance(artifact, dict):
        raise ArtifactValidationError(f"Expected an object in dbt artifact: {path}")
    metadata = _required(artifact, "metadata", str(path))
    if not isinstance(metadata, dict):
        raise ArtifactValidationError(f"Field 'metadata' must be an object in {path}")
    invocation_id = str(_required(metadata, "invocation_id", f"{path}:metadata"))
    results = _required(artifact, "results", str(path))
    if not isinstance(results, list):
        raise ArtifactValidationError(f"Field 'results' must be a list in {path}")

    parsed: list[DbtNodeResult] = []
    for index, result in enumerate(results):
        location = f"{path}:results[{index}]"
        if not isinstance(result, dict):
            raise ArtifactValidationError(f"Expected an object at {location}")
        unique_id = str(_required(result, "unique_id", location))
        parts = unique_id.split(".")
        if len(parts) < 3 or not parts[0] or not parts[-1]:
            raise ArtifactValidationError(f"Invalid dbt unique_id '{unique_id}' at {location}")
        try:
            execution_time = float(_required(result, "execution_time", location))
        except (TypeError, ValueError) as exc:
            raise ArtifactValidationError(f"Invalid execution_time at {location}") from exc
        parsed.append(DbtNodeResult(
            invocation_id=invocation_id,
            command_type=command_type,
            node_unique_id=unique_id,
            node_name=parts[-1],
            resource_type=parts[0],
            execution_status=str(_required(result, "status", location)),
            execution_time_seconds=execution_time,
            message=None if result.get("message") is None else str(result["message"]),
        ))
    return parsed


def get_connection_params() -> dict[str, str]:
    load_dotenv(REPO_ROOT / ".env")
    return {
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": os.getenv("POSTGRES_PORT", "5433"),
        "dbname": os.getenv("POSTGRES_DB", "dataops"),
        "user": os.getenv("POSTGRES_USER", "dataops"),
        "password": os.getenv("POSTGRES_PASSWORD", ""),
    }


def persist_metadata(conn: psycopg.Connection, *, dag_id: str, airflow_run_id: str,
                     started_at: datetime, run_status: str,
                     results: Iterable[DbtNodeResult],
                     pipeline_run_id: uuid.UUID | None = None) -> uuid.UUID:
    pipeline_run_id = pipeline_run_id or uuid.uuid5(ID_NAMESPACE, f"{dag_id}\0{airflow_run_id}")
    completed_at = datetime.now(timezone.utc)
    with conn.transaction():
        pipeline_cursor = conn.execute(
            """INSERT INTO metadata.pipeline_runs
               (pipeline_run_id, dag_id, airflow_run_id, started_at, completed_at, run_status)
               VALUES (%s, %s, %s, %s, %s, %s)
               ON CONFLICT (dag_id, airflow_run_id) DO UPDATE SET
                 started_at = EXCLUDED.started_at,
                 completed_at = EXCLUDED.completed_at,
                 run_status = EXCLUDED.run_status
               RETURNING pipeline_run_id""",
            (pipeline_run_id, dag_id, airflow_run_id, started_at, completed_at, run_status),
        )
        stored_pipeline_run_id = pipeline_cursor.fetchone()[0]
        for result in results:
            result_id = uuid.uuid5(
                ID_NAMESPACE,
                f"{stored_pipeline_run_id}\0{result.invocation_id}\0{result.command_type}\0{result.node_unique_id}",
            )
            conn.execute(
                """INSERT INTO metadata.dbt_node_results
                   (result_id, pipeline_run_id, invocation_id, command_type, node_unique_id,
                    node_name, resource_type, execution_status, execution_time_seconds, message)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (pipeline_run_id, invocation_id, command_type, node_unique_id)
                   DO UPDATE SET node_name = EXCLUDED.node_name,
                     resource_type = EXCLUDED.resource_type,
                     execution_status = EXCLUDED.execution_status,
                     execution_time_seconds = EXCLUDED.execution_time_seconds,
                     message = EXCLUDED.message""",
                (result_id, stored_pipeline_run_id, result.invocation_id, result.command_type,
                 result.node_unique_id, result.node_name, result.resource_type,
                 result.execution_status, result.execution_time_seconds, result.message),
            )
    return stored_pipeline_run_id


def collect_metadata(*, dag_id: str, airflow_run_id: str, started_at: datetime,
                     run_status: str, artifact_root: Path,
                     pipeline_run_id: uuid.UUID | None = None) -> uuid.UUID:
    results: list[DbtNodeResult] = []
    for command_type in ("run", "test"):
        artifact_path = artifact_root / command_type / "run_results.json"
        parsed = parse_run_results(artifact_path, command_type)
        logger.info("Parsed dbt artifact", extra={"command_type": command_type, "nodes": len(parsed)})
        results.extend(parsed)
    logger.info("Recording pipeline metadata", extra={"dag_id": dag_id, "airflow_run_id": airflow_run_id})
    with psycopg.connect(**get_connection_params()) as conn:
        pipeline_run_id = persist_metadata(
            conn, dag_id=dag_id, airflow_run_id=airflow_run_id, started_at=started_at,
            run_status=run_status, results=results, pipeline_run_id=pipeline_run_id,
        )
    logger.info("Pipeline metadata collection complete", extra={"pipeline_run_id": str(pipeline_run_id)})
    return pipeline_run_id


def parse_datetime(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"Invalid ISO-8601 timestamp: {value}") from exc
    if parsed.tzinfo is None:
        raise argparse.ArgumentTypeError("Pipeline start time must include a timezone")
    return parsed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Collect Airflow and dbt execution metadata")
    parser.add_argument("--manual", action="store_true",
                        help="Run with generated development metadata")
    parser.add_argument("--dag-id")
    parser.add_argument("--airflow-run-id")
    parser.add_argument("--started-at", type=parse_datetime)
    parser.add_argument("--run-status")
    parser.add_argument("--artifact-root", type=Path,
                        default=Path(os.getenv("DBT_ARTIFACT_ROOT", DEFAULT_ARTIFACT_ROOT)))
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    orchestration_values = (args.dag_id, args.airflow_run_id, args.started_at, args.run_status)
    if args.manual and any(value is not None for value in orchestration_values):
        parser.error("--manual cannot be combined with Airflow runtime arguments")
    if not args.manual and any(value is not None for value in orchestration_values) \
            and not all(value is not None for value in orchestration_values):
        parser.error("Airflow mode requires --dag-id, --airflow-run-id, --started-at, and --run-status")

    development_mode = args.manual or not any(value is not None for value in orchestration_values)
    pipeline_run_id = uuid.uuid4() if development_mode else None
    dag_id = "manual" if development_mode else args.dag_id
    airflow_run_id = f"manual__{uuid.uuid4()}" if development_mode else args.airflow_run_id
    started_at = datetime.now(timezone.utc) if development_mode else args.started_at
    run_status = "SUCCESS" if development_mode else args.run_status
    if development_mode:
        logger.info("Using generated metadata for standalone development mode")
    try:
        collect_metadata(dag_id=dag_id, airflow_run_id=airflow_run_id,
                         started_at=started_at, run_status=run_status,
                         artifact_root=args.artifact_root,
                         pipeline_run_id=pipeline_run_id)
    except Exception:
        logger.exception("Metadata collection failed")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
