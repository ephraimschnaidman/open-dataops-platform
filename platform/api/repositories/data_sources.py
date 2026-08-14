from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from api.repositories.pipelines import ACTIVE_ALERTS, PIPELINE_STATE_CTE, escape_like


@dataclass(frozen=True)
class DataSourceFilters:
    environment: str | None = None
    operational_status: str | None = None
    source_type: str | None = None
    search: str | None = None


class DataSourceRepository:
    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool

    @staticmethod
    def _where_clause(filters: DataSourceFilters) -> tuple[str, list[object]]:
        conditions: list[str] = []
        parameters: list[object] = []
        for expression, value in (
            ("e.environment_key = %s", filters.environment),
            ("s.operational_status = %s", filters.operational_status),
            ("s.source_type = %s", filters.source_type),
        ):
            if value is not None:
                conditions.append(expression)
                parameters.append(value)
        if filters.search is not None:
            conditions.append("""(
                s.source_key ILIKE %s ESCAPE E'\\\\'
                OR s.source_name ILIKE %s ESCAPE E'\\\\'
            )""")
            pattern = f"%{escape_like(filters.search)}%"
            parameters.extend([pattern, pattern])
        return (f"WHERE {' AND '.join(conditions)}" if conditions else ""), parameters

    async def list_data_sources(
        self, *, limit: int, offset: int, filters: DataSourceFilters
    ) -> tuple[list[dict[str, Any]], int]:
        where_clause, parameters = self._where_clause(filters)
        count_query = f"""
            SELECT COUNT(*)
            FROM metadata.data_sources s
            JOIN metadata.environments e ON e.environment_id = s.environment_id
            {where_clause}
        """
        list_query = f"""
            SELECT s.source_key, s.source_name AS name, s.source_type,
                   jsonb_build_object(
                       'environment_key', e.environment_key,
                       'name', e.environment_name
                   ) AS environment,
                   s.operational_status,
                   COUNT(DISTINCT p.pipeline_id)::int AS connected_pipeline_count,
                   MAX(te.occurred_at) AS last_observed_at
            FROM metadata.data_sources s
            JOIN metadata.environments e ON e.environment_id = s.environment_id
            LEFT JOIN metadata.pipelines p ON p.data_source_id = s.data_source_id
            LEFT JOIN metadata.technical_events te ON te.data_source_id = s.data_source_id
            {where_clause}
            GROUP BY s.data_source_id, e.environment_key, e.environment_name
            ORDER BY name, s.source_key
            LIMIT %s OFFSET %s
        """
        async with self._pool.connection() as connection:
            result = await connection.execute(count_query, parameters)
            count_row = await result.fetchone()
            async with connection.cursor(row_factory=dict_row) as cursor:
                await cursor.execute(list_query, [*parameters, limit, offset])
                rows = await cursor.fetchall()
        return rows, int(count_row[0])

    async def get_data_source(self, source_key: str) -> dict[str, Any] | None:
        query = """
            SELECT s.data_source_id, s.source_key, s.source_name AS name,
                   s.source_type,
                   jsonb_build_object(
                       'environment_key', e.environment_key,
                       'name', e.environment_name
                   ) AS environment,
                   s.operational_status,
                   (SELECT COUNT(*)::int FROM metadata.pipelines p
                    WHERE p.data_source_id = s.data_source_id) AS connected_pipeline_count,
                   (SELECT MAX(te.occurred_at) FROM metadata.technical_events te
                    WHERE te.data_source_id = s.data_source_id) AS last_observed_at
            FROM metadata.data_sources s
            JOIN metadata.environments e ON e.environment_id = s.environment_id
            WHERE s.source_key = %s
        """
        rows = await self._fetchall(query, [source_key])
        return rows[0] if rows else None

    async def get_connected_pipelines(self, data_source_id: object) -> list[dict[str, Any]]:
        query = f"""
            {PIPELINE_STATE_CTE}
            SELECT pipeline_key, pipeline_name AS name, is_enabled,
                   operational_status,
                   CASE WHEN corvetra_run_id IS NULL THEN NULL ELSE jsonb_build_object(
                       'corvetra_run_id', corvetra_run_id, 'status', run_status,
                       'stage', stage_name, 'started_at', started_at,
                       'completed_at', completed_at,
                       'duration_seconds', CASE WHEN completed_at IS NULL THEN NULL ELSE
                           EXTRACT(EPOCH FROM completed_at - started_at)::double precision END,
                       'platform_code', platform_code, 'vendor_code', vendor_code,
                       'rule_code', rule_code
                   ) END AS latest_run
            FROM pipeline_state
            WHERE data_source_id = %s
            ORDER BY name, pipeline_key
        """
        return await self._fetchall(query, [data_source_id])

    async def get_validation_summary(self, data_source_id: object) -> dict[str, Any]:
        query = """
            SELECT COUNT(*)::int AS total,
                   COUNT(*) FILTER (WHERE x.result_status = 'PASSED')::int AS passed,
                   COUNT(*) FILTER (WHERE x.result_status = 'FAILED')::int AS failed,
                   COUNT(*) FILTER (WHERE x.result_status = 'NOT_EVALUATED')::int AS not_evaluated,
                   COUNT(*) FILTER (WHERE x.result_status = 'FAILED' AND x.effective_severity = 'BLOCKING')::int AS blocking_failed,
                   COUNT(*) FILTER (WHERE x.result_status = 'FAILED' AND x.effective_severity = 'WARNING')::int AS warning_failed,
                   MAX(x.evaluated_at) AS last_evaluated_at
            FROM metadata.validation_executions x
            JOIN metadata.pipeline_runs r ON r.pipeline_run_id = x.pipeline_run_id
            JOIN metadata.pipelines p ON p.pipeline_id = r.pipeline_id
            WHERE p.data_source_id = %s AND r.corvetra_run_id IS NOT NULL
        """
        return (await self._fetchall(query, [data_source_id]))[0]

    async def count_active_alerts(self, data_source_id: object) -> int:
        query = f"""
            SELECT COUNT(*)
            FROM metadata.operational_alerts a
            JOIN metadata.pipeline_runs r ON r.pipeline_run_id = a.pipeline_run_id
            JOIN metadata.pipelines p ON p.pipeline_id = r.pipeline_id
            WHERE p.data_source_id = %s AND a.alert_status IN {ACTIVE_ALERTS}
        """
        async with self._pool.connection() as connection:
            result = await connection.execute(query, [data_source_id])
            row = await result.fetchone()
        return int(row[0])

    async def get_recent_evidence(self, data_source_id: object) -> list[dict[str, Any]]:
        query = """
            SELECT event_key, occurred_at, event_level AS level,
                   stage_name AS stage, platform_code, vendor_code, rule_code,
                   event_message AS message
            FROM metadata.technical_events
            WHERE data_source_id = %s
            ORDER BY occurred_at DESC, technical_event_id DESC
            LIMIT 5
        """
        return await self._fetchall(query, [data_source_id])

    async def _fetchall(self, query: str, parameters: list[object]) -> list[dict[str, Any]]:
        async with self._pool.connection() as connection:
            async with connection.cursor(row_factory=dict_row) as cursor:
                await cursor.execute(query, parameters)
                return await cursor.fetchall()
