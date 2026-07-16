from __future__ import annotations

import argparse
import logging
import sys
import uuid
from datetime import datetime, timezone

import psycopg

from collect_data_health_metrics import get_connection_params
from incident_context_rules import (
    IncidentContext,
    IncidentMetadata,
    generate_stale_data_context,
)

ID_NAMESPACE = uuid.UUID("14c69470-a231-4a97-8ff2-e10e445bce52")
logger = logging.getLogger(__name__)


class IncidentContextGenerationError(RuntimeError):
    """Base error for incident context generation failures."""


class IncidentNotFoundError(IncidentContextGenerationError):
    """Raised when a requested incident does not exist."""


class UnsupportedIncidentTypeError(IncidentContextGenerationError):
    """Raised when a requested incident has no context rules."""


def _to_incident(row: tuple[object, ...]) -> tuple[uuid.UUID, IncidentMetadata]:
    incident_id, incident_type, severity, schema, table, expected, observed, status = row
    return incident_id, IncidentMetadata(
        incident_type=str(incident_type),
        severity=str(severity),
        table_schema=str(schema),
        table_name=str(table),
        expected_value=None if expected is None else str(expected),
        observed_value=None if observed is None else str(observed),
        incident_status=str(status),
    )


def load_incidents(
    conn: psycopg.Connection, incident_id: uuid.UUID | None,
) -> list[tuple[uuid.UUID, IncidentMetadata]]:
    columns = """incident_id, incident_type, severity, table_schema, table_name,
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
                WHERE incident_type = %s AND incident_status = %s
                ORDER BY detected_at, incident_id""",
            ("STALE_DATA", "OPEN"),
        ).fetchall()
    return [_to_incident(row) for row in rows]


def persist_context(conn: psycopg.Connection, incident_id: uuid.UUID,
                    context: IncidentContext, generated_at: datetime) -> uuid.UUID:
    context_id = uuid.uuid5(ID_NAMESPACE, f"context\0{incident_id}\0{context.context_version}")
    conn.execute(
        """INSERT INTO metadata.incident_context
           (context_id, incident_id, context_version, what_happened, why_it_matters,
            recommended_next_step, generated_at)
           VALUES (%s, %s, %s, %s, %s, %s, %s)
           ON CONFLICT (incident_id, context_version) DO UPDATE SET
             what_happened = EXCLUDED.what_happened,
             why_it_matters = EXCLUDED.why_it_matters,
             recommended_next_step = EXCLUDED.recommended_next_step,
             generated_at = EXCLUDED.generated_at,
             updated_at = CURRENT_TIMESTAMP""",
        (context_id, incident_id, context.context_version, context.what_happened,
         context.why_it_matters, context.recommended_next_step, generated_at),
    )
    return context_id


def generate_contexts(conn: psycopg.Connection, incident_id: uuid.UUID | None,
                      generated_at: datetime) -> list[uuid.UUID]:
    context_ids = []
    for current_id, incident in load_incidents(conn, incident_id):
        if incident.incident_type != "STALE_DATA":
            raise UnsupportedIncidentTypeError(
                f"Incident {current_id} has unsupported type {incident.incident_type!r}; "
                "only STALE_DATA is supported"
            )
        context = generate_stale_data_context(incident)
        context_ids.append(persist_context(conn, current_id, context, generated_at))
        logger.info("Generated incident context", extra={
            "incident_id": str(current_id), "context_version": context.context_version,
        })
    return context_ids


def generate_incident_context(incident_id: uuid.UUID | None = None) -> list[uuid.UUID]:
    generated_at = datetime.now(timezone.utc)
    with psycopg.connect(**get_connection_params()) as conn, conn.transaction():
        context_ids = generate_contexts(conn, incident_id, generated_at)
    logger.info("Incident context generation complete", extra={"contexts": len(context_ids)})
    return context_ids


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate deterministic context for STALE_DATA incidents",
    )
    parser.add_argument("incident_id", nargs="?", type=uuid.UUID)
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    try:
        generate_incident_context(args.incident_id)
    except Exception:
        logger.exception("Incident context generation failed")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
