from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

PIPELINE_COLUMNS = """
    pipeline_run_id, dag_id, airflow_run_id, started_at, completed_at,
    run_status, created_at
"""


@dataclass(frozen=True)
class PipelineFilters:
    dag_id: str | None = None
    run_status: str | None = None
    pipeline_run_id: UUID | None = None
    airflow_run_id: str | None = None


class PipelineRepository:
    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool

    @staticmethod
    def _where_clause(filters: PipelineFilters) -> tuple[str, list[object]]:
        candidates = (
            ("dag_id", filters.dag_id),
            ("run_status", filters.run_status),
            ("pipeline_run_id", filters.pipeline_run_id),
            ("airflow_run_id", filters.airflow_run_id),
        )
        conditions: list[str] = []
        parameters: list[object] = []
        for column, value in candidates:
            if value is not None:
                conditions.append(f"{column} = %s")
                parameters.append(value)
        clause = f" WHERE {' AND '.join(conditions)}" if conditions else ""
        return clause, parameters

    async def list_pipelines(
        self,
        *,
        limit: int,
        offset: int,
        filters: PipelineFilters,
    ) -> tuple[list[dict[str, Any]], int]:
        where_clause, parameters = self._where_clause(filters)
        count_query = (
            "SELECT COUNT(*) FROM metadata.pipeline_runs"
            f"{where_clause}"
        )
        list_query = f"""
            SELECT {PIPELINE_COLUMNS}
            FROM metadata.pipeline_runs
            {where_clause}
            ORDER BY started_at DESC, pipeline_run_id DESC
            LIMIT %s OFFSET %s
        """
        async with self._pool.connection() as connection:
            count_result = await connection.execute(count_query, parameters)
            count_row = await count_result.fetchone()
            async with connection.cursor(row_factory=dict_row) as cursor:
                await cursor.execute(list_query, [*parameters, limit, offset])
                rows = await cursor.fetchall()
        return rows, int(count_row[0])
