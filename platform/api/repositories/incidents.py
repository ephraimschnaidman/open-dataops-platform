from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

INCIDENT_COLUMNS = """
    incident_id, pipeline_run_id, incident_type, severity, table_schema,
    table_name, column_name, expected_value, observed_value, incident_message,
    incident_status, detected_at, resolved_at, created_at, updated_at
"""

CONTEXT_COLUMNS = """
    context_id, incident_id, context_version, qualified_table,
    evaluation_status, severity, expected_freshness_hours,
    observed_freshness_hours, recommended_action_code, generated_at,
    created_at, updated_at, change_type, affected_column
"""


@dataclass(frozen=True)
class IncidentFilters:
    incident_status: str | None = None
    severity: str | None = None
    incident_type: str | None = None
    table_schema: str | None = None
    table_name: str | None = None
    pipeline_run_id: UUID | None = None


class IncidentRepository:
    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool

    @staticmethod
    def _where_clause(filters: IncidentFilters) -> tuple[str, list[object]]:
        conditions: list[str] = []
        parameters: list[object] = []
        for column, value in (
            ("incident_status", filters.incident_status),
            ("severity", filters.severity),
            ("incident_type", filters.incident_type),
            ("table_schema", filters.table_schema),
            ("table_name", filters.table_name),
            ("pipeline_run_id", filters.pipeline_run_id),
        ):
            if value is not None:
                conditions.append(f"{column} = %s")
                parameters.append(value)
        clause = f" WHERE {' AND '.join(conditions)}" if conditions else ""
        return clause, parameters

    async def list_incidents(
        self,
        *,
        limit: int,
        offset: int,
        filters: IncidentFilters,
    ) -> tuple[list[dict[str, Any]], int]:
        where_clause, parameters = self._where_clause(filters)
        count_query = f"SELECT COUNT(*) FROM metadata.data_incidents{where_clause}"
        list_query = f"""
            SELECT {INCIDENT_COLUMNS}
            FROM metadata.data_incidents
            {where_clause}
            ORDER BY detected_at DESC, incident_id DESC
            LIMIT %s OFFSET %s
        """

        async with self._pool.connection() as connection:
            count_result = await connection.execute(count_query, parameters)
            count_row = await count_result.fetchone()
            async with connection.cursor(row_factory=dict_row) as cursor:
                await cursor.execute(list_query, [*parameters, limit, offset])
                rows = await cursor.fetchall()
        return rows, int(count_row[0])

    async def get_incident(self, incident_id: UUID) -> dict[str, Any] | None:
        query = f"""
            SELECT {INCIDENT_COLUMNS}
            FROM metadata.data_incidents
            WHERE incident_id = %s
        """
        async with self._pool.connection() as connection:
            async with connection.cursor(row_factory=dict_row) as cursor:
                await cursor.execute(query, (incident_id,))
                return await cursor.fetchone()

    async def get_incident_context(
        self,
        incident_id: UUID,
    ) -> dict[str, Any] | None:
        query = f"""
            SELECT {CONTEXT_COLUMNS}
            FROM metadata.incident_context
            WHERE incident_id = %s
            ORDER BY generated_at DESC, context_id DESC
            LIMIT 1
        """
        async with self._pool.connection() as connection:
            async with connection.cursor(row_factory=dict_row) as cursor:
                await cursor.execute(query, (incident_id,))
                return await cursor.fetchone()
