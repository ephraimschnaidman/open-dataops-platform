from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

SNAPSHOT_COLUMNS = """
    snapshot_id, pipeline_run_id, table_schema, table_name, column_name,
    ordinal_position, data_type, is_nullable, measured_at, created_at
"""

QUALIFIED_SNAPSHOT_COLUMNS = """
    s.snapshot_id, s.pipeline_run_id, s.table_schema, s.table_name,
    s.column_name, s.ordinal_position, s.data_type, s.is_nullable,
    s.measured_at, s.created_at
"""


@dataclass(frozen=True)
class SchemaSnapshotFilters:
    pipeline_run_id: UUID | None = None
    table_schema: str | None = None
    table_name: str | None = None
    column_name: str | None = None


class SchemaSnapshotRepository:
    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool

    @staticmethod
    def _where_clause(
        filters: SchemaSnapshotFilters,
        *,
        include_pipeline: bool = True,
        include_column: bool = True,
        prefix: str = "",
    ) -> tuple[str, list[object]]:
        candidates = [
            ("pipeline_run_id", filters.pipeline_run_id, include_pipeline),
            ("table_schema", filters.table_schema, True),
            ("table_name", filters.table_name, True),
            ("column_name", filters.column_name, include_column),
        ]
        conditions: list[str] = []
        parameters: list[object] = []
        for column, value, included in candidates:
            if included and value is not None:
                conditions.append(f"{prefix}{column} = %s")
                parameters.append(value)
        clause = f" WHERE {' AND '.join(conditions)}" if conditions else ""
        return clause, parameters

    @staticmethod
    def _historical_queries(
        filters: SchemaSnapshotFilters,
        *,
        latest_order: bool,
    ) -> tuple[str, str, list[object]]:
        where_clause, parameters = SchemaSnapshotRepository._where_clause(filters)
        order_by = (
            "table_schema ASC, table_name ASC, ordinal_position ASC, "
            "snapshot_id DESC"
            if latest_order
            else "measured_at DESC, table_schema ASC, table_name ASC, "
            "ordinal_position ASC, snapshot_id DESC"
        )
        count_query = (
            "SELECT COUNT(*) FROM metadata.table_schema_snapshots"
            f"{where_clause}"
        )
        list_query = f"""
            SELECT {SNAPSHOT_COLUMNS}
            FROM metadata.table_schema_snapshots
            {where_clause}
            ORDER BY {order_by}
            LIMIT %s OFFSET %s
        """
        return count_query, list_query, parameters

    @staticmethod
    def _latest_queries(
        filters: SchemaSnapshotFilters,
    ) -> tuple[str, str, list[object]]:
        selector_where, selector_parameters = (
            SchemaSnapshotRepository._where_clause(
                filters,
                include_pipeline=False,
                include_column=False,
            )
        )
        column_filters = SchemaSnapshotFilters(column_name=filters.column_name)
        outer_where, outer_parameters = SchemaSnapshotRepository._where_clause(
            column_filters,
            include_pipeline=False,
            prefix="s.",
        )
        common_table_expression = f"""
            WITH latest_table_snapshots AS (
                SELECT DISTINCT ON (table_schema, table_name)
                    pipeline_run_id, table_schema, table_name
                FROM metadata.table_schema_snapshots
                {selector_where}
                ORDER BY
                    table_schema,
                    table_name,
                    measured_at DESC,
                    pipeline_run_id DESC,
                    snapshot_id DESC
            )
        """
        joined_source = f"""
            FROM metadata.table_schema_snapshots AS s
            JOIN latest_table_snapshots AS latest
              ON latest.pipeline_run_id = s.pipeline_run_id
             AND latest.table_schema = s.table_schema
             AND latest.table_name = s.table_name
            {outer_where}
        """
        count_query = (
            f"{common_table_expression} SELECT COUNT(*) {joined_source}"
        )
        list_query = f"""
            {common_table_expression}
            SELECT {QUALIFIED_SNAPSHOT_COLUMNS}
            {joined_source}
            ORDER BY
                s.table_schema ASC,
                s.table_name ASC,
                s.ordinal_position ASC,
                s.snapshot_id DESC
            LIMIT %s OFFSET %s
        """
        return (
            count_query,
            list_query,
            [*selector_parameters, *outer_parameters],
        )

    async def list_schema_snapshots(
        self,
        *,
        limit: int,
        offset: int,
        filters: SchemaSnapshotFilters,
        latest: bool,
    ) -> tuple[list[dict[str, Any]], int]:
        if latest and filters.pipeline_run_id is None:
            count_query, list_query, parameters = self._latest_queries(filters)
        else:
            count_query, list_query, parameters = self._historical_queries(
                filters,
                latest_order=latest,
            )

        async with self._pool.connection() as connection:
            count_result = await connection.execute(count_query, parameters)
            count_row = await count_result.fetchone()
            async with connection.cursor(row_factory=dict_row) as cursor:
                await cursor.execute(list_query, [*parameters, limit, offset])
                rows = await cursor.fetchall()
        return rows, int(count_row[0])
