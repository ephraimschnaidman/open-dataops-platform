from __future__ import annotations

import argparse
import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
import sys
import uuid
from datetime import datetime, timezone

import psycopg

from collect_data_health_metrics import get_connection_params
from incident_context_rules import (
    IncidentContext,
    IncidentMetadata,
    SCHEMA_CHANGE_TYPES,
    generate_null_values_context,
    generate_schema_change_context,
    generate_stale_data_context,
)

ID_NAMESPACE = uuid.UUID("14c69470-a231-4a97-8ff2-e10e445bce52")
logger = logging.getLogger(__name__)
LOG_PATH = Path(__file__).resolve().parents[2] / "runtime" / "logs" / "jobs" / "incident_context.log"


class IncidentContextGenerationError(RuntimeError):
    """Base error for incident context generation failures."""


class IncidentNotFoundError(IncidentContextGenerationError):
    """Raised when a requested incident does not exist."""


class UnsupportedIncidentTypeError(IncidentContextGenerationError):
    """Raised when a requested incident has no context rules."""


def _to_incident(row: tuple[object, ...]) -> tuple[uuid.UUID, IncidentMetadata]:
    incident_id, incident_type, severity, schema, table, column, expected, observed, status = row
    return incident_id, IncidentMetadata(
        incident_type=str(incident_type),
        severity=str(severity),
        table_schema=str(schema),
        table_name=str(table),
        expected_value=None if expected is None else str(expected),
        observed_value=None if observed is None else str(observed),
        incident_status=str(status),
        column_name=None if column is None else str(column),
    )


def load_incidents(
    conn: psycopg.Connection, incident_id: uuid.UUID | None,
) -> list[tuple[uuid.UUID, IncidentMetadata]]:
    columns = """incident_id, incident_type, severity, table_schema, table_name, column_name,
                 expected_value, observed_value, incident_status"""
    if incident_id is not None:
        rows = conn.execute(
            f"SELECT {columns} FROM metadata.data_incidents WHERE incident_id = %s",
            (incident_id,),
        ).fetchall()
        if not rows:
            raise IncidentNotFoundError(f"Incident {incident_id} was not found")
    else:
        rows = conn.execute(
            f"""SELECT {columns} FROM metadata.data_incidents
                WHERE incident_type IN (%s, %s, %s, %s, %s, %s) AND incident_status = %s
                ORDER BY detected_at, incident_id""",
            ("STALE_DATA", *SCHEMA_CHANGE_TYPES, "NULL_VALUES", "OPEN"),
        ).fetchall()
    return [_to_incident(row) for row in rows]


def persist_context(conn: psycopg.Connection, incident_id: uuid.UUID,
                    context: IncidentContext, generated_at: datetime) -> uuid.UUID:
    context_id = uuid.uuid5(ID_NAMESPACE, f"context\0{incident_id}\0{context.context_version}")
    result = conn.execute(
        """INSERT INTO metadata.incident_context
           (context_id, incident_id, context_version, qualified_table, evaluation_status,
            severity, expected_freshness_hours, observed_freshness_hours,
            recommended_action_code, change_type, affected_column, generated_at)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
           ON CONFLICT (incident_id, context_version) DO UPDATE SET
             qualified_table = EXCLUDED.qualified_table,
             evaluation_status = EXCLUDED.evaluation_status,
             severity = EXCLUDED.severity,
             expected_freshness_hours = EXCLUDED.expected_freshness_hours,
             observed_freshness_hours = EXCLUDED.observed_freshness_hours,
             recommended_action_code = EXCLUDED.recommended_action_code,
             change_type = EXCLUDED.change_type,
             affected_column = EXCLUDED.affected_column,
             generated_at = EXCLUDED.generated_at,
             updated_at = CURRENT_TIMESTAMP
           RETURNING (xmax = 0)""",
        (context_id, incident_id, context.context_version, context.qualified_table,
         context.evaluation_status, context.severity, context.expected_freshness_hours,
         context.observed_freshness_hours, context.recommended_action_code,
         context.change_type, context.affected_column, generated_at),
    ).fetchone()
    inserted = bool(result and result[0])
    logger.info("%s context for incident %s", "Inserted" if inserted else "Updated", incident_id)
    return context_id


def generate_contexts(conn: psycopg.Connection, incident_id: uuid.UUID | None,
                      generated_at: datetime) -> list[uuid.UUID]:
    context_ids = []
    for current_id, incident in load_incidents(conn, incident_id):
        logger.info("Processing incident %s", current_id)
        if incident.incident_type == "STALE_DATA":
            context = generate_stale_data_context(incident)
        elif incident.incident_type in SCHEMA_CHANGE_TYPES:
            context = generate_schema_change_context(incident)
        elif incident.incident_type == "NULL_VALUES":
            context = generate_null_values_context(incident)
        else:
            raise UnsupportedIncidentTypeError(
                f"Incident {current_id} has unsupported type {incident.incident_type!r}; "
                "only STALE_DATA, SCHEMA_CHANGE, and NULL_VALUES v1 are supported"
            )
        context_ids.append(persist_context(conn, current_id, context, generated_at))
    return context_ids


def generate_incident_context(incident_id: uuid.UUID | None = None) -> list[uuid.UUID]:
    logger.info("Incident context generation started")
    generated_at = datetime.now(timezone.utc)
    with psycopg.connect(**get_connection_params()) as conn, conn.transaction():
        context_ids = generate_contexts(conn, incident_id, generated_at)
    logger.info("Incident context generation complete: %d context(s)", len(context_ids))
    return context_ids


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate deterministic context for supported incidents",
    )
    parser.add_argument("incident_id", nargs="?", type=uuid.UUID)
    args = parser.parse_args(argv)
    configure_logging()
    try:
        generate_incident_context(args.incident_id)
    except Exception:
        logger.exception("Incident context generation failed")
        return 1
    return 0


def configure_logging(log_path: Path = LOG_PATH) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    if not any(isinstance(handler, TimedRotatingFileHandler) for handler in root.handlers):
        file_handler = TimedRotatingFileHandler(
            log_path, when="midnight", interval=1, backupCount=30,
            encoding="utf-8", delay=True,
        )
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)
    if not any(type(handler) is logging.StreamHandler for handler in root.handlers):
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        root.addHandler(console_handler)


if __name__ == "__main__":
    sys.exit(main())
