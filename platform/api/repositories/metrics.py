from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

METRIC_COLUMNS = """
    metric_id, pipeline_run_id, table_schema, table_name, row_count,
    freshness_column, max_freshness_value, measured_at, created_at
"""


@dataclass(frozen=True)
class MetricFilters:
    pipeline_run_id: UUID | None = None
    table_schema: str | None = None
    table_name: str | None = None


class MetricRepository:
    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool

    @staticmethod
    def _where_clause(filters: MetricFilters) -> tuple[str, list[object]]:
        conditions: list[str] = []
        parameters: list[object] = []
        for column, value in (
            ("pipeline_run_id", filters.pipeline_run_id),
            ("table_schema", filters.table_schema),
            ("table_name", filters.table_name),
        ):
            if value is not None:
                conditions.append(f"{column} = %s")
                parameters.append(value)
        clause = f" WHERE {' AND '.join(conditions)}" if conditions else ""
        return clause, parameters

    async def list_metrics(
        self,
        *,
        limit: int,
        offset: int,
        filters: MetricFilters,
        latest: bool,
    ) -> tuple[list[dict[str, Any]], int]:
        where_clause, parameters = self._where_clause(filters)
        if latest:
            count_query = f"""
                SELECT COUNT(*)
                FROM (
                    SELECT 1
                    FROM metadata.table_health_metrics
                    {where_clause}
                    GROUP BY table_schema, table_name
                ) AS latest_metric_tables
            """
            list_query = f"""
                SELECT {METRIC_COLUMNS}
                FROM (
                    SELECT DISTINCT ON (table_schema, table_name)
                        {METRIC_COLUMNS}
                    FROM metadata.table_health_metrics
                    {where_clause}
                    ORDER BY
                        table_schema,
                        table_name,
                        measured_at DESC,
                        metric_id DESC
                ) AS latest_metrics
                ORDER BY table_schema ASC, table_name ASC
                LIMIT %s OFFSET %s
            """
        else:
            count_query = (
                "SELECT COUNT(*) FROM metadata.table_health_metrics"
                f"{where_clause}"
            )
            list_query = f"""
                SELECT {METRIC_COLUMNS}
                FROM metadata.table_health_metrics
                {where_clause}
                ORDER BY measured_at DESC, metric_id DESC
                LIMIT %s OFFSET %s
            """

        async with self._pool.connection() as connection:
            count_result = await connection.execute(count_query, parameters)
            count_row = await count_result.fetchone()
            async with connection.cursor(row_factory=dict_row) as cursor:
                await cursor.execute(list_query, [*parameters, limit, offset])
                rows = await cursor.fetchall()
        return rows, int(count_row[0])
