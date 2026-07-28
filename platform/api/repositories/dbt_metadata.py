from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

DBT_METADATA_COLUMNS = """
    result_id, pipeline_run_id, invocation_id, command_type, node_unique_id,
    node_name, resource_type, execution_status, execution_time_seconds,
    message, recorded_at
"""


@dataclass(frozen=True)
class DbtMetadataFilters:
    pipeline_run_id: UUID | None = None
    invocation_id: str | None = None
    resource_type: str | None = None
    execution_status: str | None = None
    node_name: str | None = None


class DbtMetadataRepository:
    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool

    @staticmethod
    def _where_clause(filters: DbtMetadataFilters) -> tuple[str, list[object]]:
        candidates = (
            ("pipeline_run_id", filters.pipeline_run_id),
            ("invocation_id", filters.invocation_id),
            ("resource_type", filters.resource_type),
            ("execution_status", filters.execution_status),
            ("node_name", filters.node_name),
        )
        conditions: list[str] = []
        parameters: list[object] = []
        for column, value in candidates:
            if value is not None:
                conditions.append(f"{column} = %s")
                parameters.append(value)
        clause = f" WHERE {' AND '.join(conditions)}" if conditions else ""
        return clause, parameters

    async def list_dbt_metadata(
        self,
        *,
        limit: int,
        offset: int,
        filters: DbtMetadataFilters,
    ) -> tuple[list[dict[str, Any]], int]:
        where_clause, parameters = self._where_clause(filters)
        count_query = (
            "SELECT COUNT(*) FROM metadata.dbt_node_results"
            f"{where_clause}"
        )
        list_query = f"""
            SELECT {DBT_METADATA_COLUMNS}
            FROM metadata.dbt_node_results
            {where_clause}
            ORDER BY recorded_at DESC, result_id DESC
            LIMIT %s OFFSET %s
        """
        async with self._pool.connection() as connection:
            count_result = await connection.execute(count_query, parameters)
            count_row = await count_result.fetchone()
            async with connection.cursor(row_factory=dict_row) as cursor:
                await cursor.execute(list_query, [*parameters, limit, offset])
                rows = await cursor.fetchall()
        return rows, int(count_row[0])
