from __future__ import annotations

import argparse
import logging
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

import psycopg

from collect_data_health_metrics import get_connection_params, resolve_pipeline_run_id
from data_health_config import MONITORED_TABLES, SEVERITY_BY_INCIDENT_TYPE, MonitoredTable

ID_NAMESPACE = uuid.UUID("14c69470-a231-4a97-8ff2-e10e445bce52")
logger = logging.getLogger(__name__)


class IncidentDetectionError(RuntimeError):
    """Raised when incident detection cannot safely evaluate a pipeline run."""


@dataclass(frozen=True)
class HealthMetric:
    row_count: int
    max_freshness_value: datetime | None


@dataclass(frozen=True)
class ColumnShape:
    data_type: str
    is_nullable: bool


@dataclass(frozen=True)
class Incident:
    incident_type: str
    severity: str
    table_schema: str
    table_name: str
    column_name: str | None
    expected_value: str | None
    observed_value: str | None
    message: str


def _incident(kind: str, table: MonitoredTable, message: str, *, column: str | None = None,
              expected: object | None = None, observed: object | None = None) -> Incident:
    return Incident(kind, SEVERITY_BY_INCIDENT_TYPE[kind], table.schema, table.name, column,
                    None if expected is None else str(expected),
                    None if observed is None else str(observed), message)


def detect_for_table(table: MonitoredTable, current: HealthMetric,
                     previous: HealthMetric | None,
                     current_schema: dict[str, ColumnShape],
                     previous_schema: dict[str, ColumnShape] | None,
                     detected_at: datetime) -> list[Incident]:
    incidents: list[Incident] = []
    if current.max_freshness_value is not None:
        age_hours = (detected_at - current.max_freshness_value).total_seconds() / 3600
        if age_hours > table.freshness_threshold_hours:
            incidents.append(_incident(
                "STALE_DATA", table,
                f"{table.schema}.{table.name} freshness is {age_hours:.2f} hours old; "
                f"threshold is {table.freshness_threshold_hours:g} hours",
                expected=f"<= {table.freshness_threshold_hours:g} hours",
                observed=f"{age_hours:.2f} hours",
            ))

    if previous is not None:
        if previous.row_count == 0:
            change_percent = 0.0 if current.row_count == 0 else float("inf")
        else:
            change_percent = ((current.row_count - previous.row_count) / previous.row_count) * 100
        if abs(change_percent) > table.row_count_change_threshold_percent:
            kind = "ROW_COUNT_INCREASE" if change_percent > 0 else "ROW_COUNT_DECREASE"
            display_change = (
                "infinite" if change_percent == float("inf")
                else f"{abs(change_percent):.2f}%"
            )
            incidents.append(_incident(
                kind, table,
                f"{table.schema}.{table.name} row count changed from {previous.row_count} "
                f"to {current.row_count} ({display_change}); threshold is "
                f"{table.row_count_change_threshold_percent:g}%",
                expected=previous.row_count, observed=current.row_count,
            ))

    if table.schema_drift_enabled and previous_schema is not None:
        current_names, previous_names = set(current_schema), set(previous_schema)
        for column in sorted(current_names - previous_names):
            incidents.append(_incident("COLUMN_ADDED", table,
                f"Column {column} was added to {table.schema}.{table.name}", column=column,
                expected="absent", observed=current_schema[column].data_type))
        for column in sorted(previous_names - current_names):
            incidents.append(_incident("COLUMN_REMOVED", table,
                f"Column {column} was removed from {table.schema}.{table.name}", column=column,
                expected=previous_schema[column].data_type, observed="absent"))
        for column in sorted(current_names & previous_names):
            before, after = previous_schema[column], current_schema[column]
            if before.data_type != after.data_type:
                incidents.append(_incident("DATA_TYPE_CHANGED", table,
                    f"Column {column} on {table.schema}.{table.name} changed type from "
                    f"{before.data_type} to {after.data_type}", column=column,
                    expected=before.data_type, observed=after.data_type))
            if before.is_nullable != after.is_nullable:
                incidents.append(_incident("NULLABILITY_CHANGED", table,
                    f"Column {column} on {table.schema}.{table.name} changed nullability from "
                    f"{before.is_nullable} to {after.is_nullable}", column=column,
                    expected=before.is_nullable, observed=after.is_nullable))
    return incidents


def load_metrics(
    conn: psycopg.Connection, pipeline_run_id: uuid.UUID,
) -> dict[tuple[str, str], HealthMetric]:
    rows = conn.execute(
        """SELECT table_schema, table_name, row_count, max_freshness_value
           FROM metadata.table_health_metrics WHERE pipeline_run_id = %s""",
        (pipeline_run_id,),
    ).fetchall()
    return {(row[0], row[1]): HealthMetric(int(row[2]), row[3]) for row in rows}


def load_schema(
    conn: psycopg.Connection, pipeline_run_id: uuid.UUID,
) -> dict[tuple[str, str], dict[str, ColumnShape]]:
    rows = conn.execute(
        """SELECT table_schema, table_name, column_name, data_type, is_nullable
           FROM metadata.table_schema_snapshots WHERE pipeline_run_id = %s""",
        (pipeline_run_id,),
    ).fetchall()
    result: dict[tuple[str, str], dict[str, ColumnShape]] = {}
    for schema, table, column, data_type, nullable in rows:
        result.setdefault((schema, table), {})[column] = ColumnShape(data_type, nullable)
    return result


def find_previous_successful_run(
    conn: psycopg.Connection, pipeline_run_id: uuid.UUID,
) -> uuid.UUID | None:
    row = conn.execute(
        """SELECT previous.pipeline_run_id
           FROM metadata.pipeline_runs current_run
           JOIN metadata.pipeline_runs previous
             ON previous.dag_id = current_run.dag_id
            AND UPPER(previous.run_status) = 'SUCCESS'
            AND previous.started_at < current_run.started_at
           WHERE current_run.pipeline_run_id = %s
           ORDER BY previous.started_at DESC LIMIT 1""",
        (pipeline_run_id,),
    ).fetchone()
    return None if row is None else row[0]


def persist_incidents(conn: psycopg.Connection, pipeline_run_id: uuid.UUID,
                      incidents: Iterable[Incident], detected_at: datetime) -> int:
    count = 0
    for item in incidents:
        incident_id = uuid.uuid5(ID_NAMESPACE, "\0".join((str(pipeline_run_id), item.incident_type,
            item.table_schema, item.table_name, item.column_name or "")))
        conn.execute(
            """INSERT INTO metadata.data_incidents
               (incident_id, pipeline_run_id, incident_type, severity, table_schema, table_name,
                column_name, expected_value, observed_value, incident_message, detected_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT (incident_id) DO UPDATE SET
                 severity = EXCLUDED.severity, expected_value = EXCLUDED.expected_value,
                 observed_value = EXCLUDED.observed_value,
                 incident_message = EXCLUDED.incident_message, updated_at = CURRENT_TIMESTAMP""",
            (incident_id, pipeline_run_id, item.incident_type, item.severity, item.table_schema,
             item.table_name, item.column_name, item.expected_value, item.observed_value,
             item.message, detected_at),
        )
        count += 1
    return count


def detect_data_incidents(*, dag_id: str | None, airflow_run_id: str | None,
                          pipeline_run_id: uuid.UUID | None = None) -> uuid.UUID:
    detected_at = datetime.now(timezone.utc)
    with psycopg.connect(**get_connection_params()) as conn, conn.transaction():
        run_id = resolve_pipeline_run_id(conn, pipeline_run_id=pipeline_run_id,
                                         dag_id=dag_id, airflow_run_id=airflow_run_id)
        current_metrics, current_schema = load_metrics(conn, run_id), load_schema(conn, run_id)
        missing = [
            (table.schema, table.name) for table in MONITORED_TABLES
            if (table.schema, table.name) not in current_metrics
        ]
        if missing:
            raise IncidentDetectionError(f"Current run is missing health metrics for: {missing}")
        previous_id = find_previous_successful_run(conn, run_id)
        previous_metrics = {} if previous_id is None else load_metrics(conn, previous_id)
        previous_schema = {} if previous_id is None else load_schema(conn, previous_id)
        if previous_id is None:
            logger.info("No previous successful run; establishing row-count and schema baseline",
                        extra={"pipeline_run_id": str(run_id)})
        incidents: list[Incident] = []
        for table in MONITORED_TABLES:
            key = (table.schema, table.name)
            incidents.extend(detect_for_table(
                table, current_metrics[key], previous_metrics.get(key),
                current_schema.get(key, {}),
                None if previous_id is None else previous_schema.get(key), detected_at,
            ))
        count = persist_incidents(conn, run_id, incidents, detected_at)
    logger.info(
        "Data incident detection complete",
        extra={"pipeline_run_id": str(run_id), "incidents": count},
    )
    return run_id


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Detect incidents from stored data health measurements",
    )
    parser.add_argument("--dag-id")
    parser.add_argument("--airflow-run-id")
    parser.add_argument("--pipeline-run-id", type=uuid.UUID)
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    try:
        detect_data_incidents(dag_id=args.dag_id, airflow_run_id=args.airflow_run_id,
                              pipeline_run_id=args.pipeline_run_id)
    except Exception:
        logger.exception("Data incident detection failed")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
