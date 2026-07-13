from __future__ import annotations

import argparse
import logging
import os
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

import psycopg
from dotenv import load_dotenv
from psycopg import sql

from data_health_config import MONITORED_TABLES, MonitoredTable

REPO_ROOT = Path(__file__).resolve().parents[2]
ID_NAMESPACE = uuid.UUID("14c69470-a231-4a97-8ff2-e10e445bce52")
logger = logging.getLogger(__name__)


class DataHealthCollectionError(RuntimeError):
    """Base error for invalid health collection inputs or database state."""


class MonitoredTableNotFoundError(DataHealthCollectionError):
    """Raised when a configured table does not exist."""


class FreshnessColumnNotFoundError(DataHealthCollectionError):
    """Raised when a configured freshness column does not exist."""


@dataclass(frozen=True)
class ColumnSnapshot:
    column_name: str
    ordinal_position: int
    data_type: str
    is_nullable: bool


@dataclass(frozen=True)
class TableMeasurement:
    table: MonitoredTable
    row_count: int
    max_freshness_value: datetime | None
    columns: tuple[ColumnSnapshot, ...]


def get_connection_params() -> dict[str, str]:
    load_dotenv(REPO_ROOT / ".env")
    return {
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": os.getenv("POSTGRES_PORT", "5433"),
        "dbname": os.getenv("POSTGRES_DB", "dataops"),
        "user": os.getenv("POSTGRES_USER", "dataops"),
        "password": os.getenv("POSTGRES_PASSWORD", ""),
    }


def parse_schema_rows(rows: Iterable[Sequence[Any]]) -> tuple[ColumnSnapshot, ...]:
    snapshots = []
    for row in rows:
        if len(row) != 4:
            raise DataHealthCollectionError("Expected four fields for an information_schema column")
        column_name, ordinal_position, data_type, is_nullable = row
        snapshots.append(ColumnSnapshot(
            column_name=str(column_name),
            ordinal_position=int(ordinal_position),
            data_type=str(data_type),
            is_nullable=str(is_nullable).upper() == "YES",
        ))
    return tuple(snapshots)


def resolve_pipeline_run_id(conn: psycopg.Connection, *, pipeline_run_id: uuid.UUID | None,
                            dag_id: str | None, airflow_run_id: str | None) -> uuid.UUID:
    if pipeline_run_id is not None:
        row = conn.execute(
            "SELECT pipeline_run_id FROM metadata.pipeline_runs WHERE pipeline_run_id = %s",
            (pipeline_run_id,),
        ).fetchone()
    else:
        if not dag_id or not airflow_run_id:
            raise DataHealthCollectionError(
                "Provide --pipeline-run-id or both --dag-id and --airflow-run-id"
            )
        row = conn.execute(
            """SELECT pipeline_run_id FROM metadata.pipeline_runs
               WHERE dag_id = %s AND airflow_run_id = %s""",
            (dag_id, airflow_run_id),
        ).fetchone()
    if row is None:
        raise DataHealthCollectionError("No matching metadata.pipeline_runs record was found")
    return row[0]


def measure_table(conn: psycopg.Connection, table: MonitoredTable) -> TableMeasurement:
    rows = conn.execute(
        """SELECT column_name, ordinal_position, data_type, is_nullable
           FROM information_schema.columns
           WHERE table_schema = %s AND table_name = %s
           ORDER BY ordinal_position""",
        (table.schema, table.name),
    ).fetchall()
    if not rows:
        raise MonitoredTableNotFoundError(f"Monitored table does not exist: {table.schema}.{table.name}")
    columns = parse_schema_rows(rows)
    column_names = {column.column_name for column in columns}
    if table.freshness_column and table.freshness_column not in column_names:
        raise FreshnessColumnNotFoundError(
            f"Freshness column {table.freshness_column!r} does not exist on "
            f"{table.schema}.{table.name}"
        )

    qualified_table = sql.Identifier(table.schema, table.name)
    if table.freshness_column:
        statement = sql.SQL("SELECT COUNT(*), MAX({})::timestamptz FROM {}").format(
            sql.Identifier(table.freshness_column), qualified_table,
        )
    else:
        statement = sql.SQL("SELECT COUNT(*), NULL::timestamptz FROM {}").format(qualified_table)
    row_count, max_freshness_value = conn.execute(statement).fetchone()
    return TableMeasurement(table, int(row_count), max_freshness_value, columns)


def persist_measurements(conn: psycopg.Connection, *, pipeline_run_id: uuid.UUID,
                         measurements: Iterable[TableMeasurement],
                         measured_at: datetime) -> None:
    for measurement in measurements:
        table = measurement.table
        metric_id = uuid.uuid5(
            ID_NAMESPACE, f"health\0{pipeline_run_id}\0{table.schema}\0{table.name}",
        )
        conn.execute(
            """INSERT INTO metadata.table_health_metrics
               (metric_id, pipeline_run_id, table_schema, table_name, row_count,
                freshness_column, max_freshness_value, measured_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT (pipeline_run_id, table_schema, table_name) DO UPDATE SET
                 row_count = EXCLUDED.row_count,
                 freshness_column = EXCLUDED.freshness_column,
                 max_freshness_value = EXCLUDED.max_freshness_value,
                 measured_at = EXCLUDED.measured_at""",
            (metric_id, pipeline_run_id, table.schema, table.name, measurement.row_count,
             table.freshness_column, measurement.max_freshness_value, measured_at),
        )
        conn.execute(
            """DELETE FROM metadata.table_schema_snapshots
               WHERE pipeline_run_id = %s AND table_schema = %s AND table_name = %s""",
            (pipeline_run_id, table.schema, table.name),
        )
        for column in measurement.columns:
            snapshot_id = uuid.uuid5(
                ID_NAMESPACE,
                f"schema\0{pipeline_run_id}\0{table.schema}\0{table.name}\0{column.column_name}",
            )
            conn.execute(
                """INSERT INTO metadata.table_schema_snapshots
                   (snapshot_id, pipeline_run_id, table_schema, table_name, column_name,
                    ordinal_position, data_type, is_nullable, measured_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (pipeline_run_id, table_schema, table_name, column_name)
                   DO UPDATE SET ordinal_position = EXCLUDED.ordinal_position,
                     data_type = EXCLUDED.data_type,
                     is_nullable = EXCLUDED.is_nullable,
                     measured_at = EXCLUDED.measured_at""",
                (snapshot_id, pipeline_run_id, table.schema, table.name, column.column_name,
                 column.ordinal_position, column.data_type, column.is_nullable, measured_at),
            )


def collect_data_health_metrics(*, dag_id: str | None, airflow_run_id: str | None,
                                pipeline_run_id: uuid.UUID | None = None) -> uuid.UUID:
    measured_at = datetime.now(timezone.utc)
    with psycopg.connect(**get_connection_params()) as conn, conn.transaction():
        resolved_id = resolve_pipeline_run_id(
            conn, pipeline_run_id=pipeline_run_id, dag_id=dag_id,
            airflow_run_id=airflow_run_id,
        )
        measurements = []
        for table in MONITORED_TABLES:
            measurement = measure_table(conn, table)
            measurements.append(measurement)
            logger.info(
                "Measured table health for %s.%s: rows=%s freshness=%s",
                table.schema, table.name, measurement.row_count,
                measurement.max_freshness_value,
            )
        persist_measurements(
            conn, pipeline_run_id=resolved_id, measurements=measurements,
            measured_at=measured_at,
        )
    logger.info("Data health collection complete for pipeline_run_id=%s", resolved_id)
    return resolved_id


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Collect table health metrics and schema snapshots")
    parser.add_argument("--dag-id")
    parser.add_argument("--airflow-run-id")
    parser.add_argument("--pipeline-run-id", type=uuid.UUID)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    try:
        collect_data_health_metrics(
            dag_id=args.dag_id, airflow_run_id=args.airflow_run_id,
            pipeline_run_id=args.pipeline_run_id,
        )
    except Exception:
        logger.exception("Data health collection failed")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
