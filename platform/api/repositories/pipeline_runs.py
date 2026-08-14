from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from api.repositories.pipelines import PIPELINE_STATE_CTE, escape_like


@dataclass(frozen=True)
class PipelineRunFilters:
    pipeline: str | None = None
    environment: str | None = None
    status: str | None = None
    stage: str | None = None
    source: str | None = None
    started_from: datetime | None = None
    started_to: datetime | None = None
    search: str | None = None


RUN_SELECT = """
    r.corvetra_run_id,
    jsonb_build_object(
        'pipeline_key', ps.pipeline_key, 'name', ps.pipeline_name,
        'operational_status', ps.operational_status
    ) AS pipeline,
    jsonb_build_object(
        'source_key', ps.source_key, 'name', ps.source_name,
        'source_type', ps.source_type, 'operational_status', ps.source_status
    ) AS source,
    jsonb_build_object(
        'environment_key', ps.environment_key, 'name', ps.environment_name
    ) AS environment,
    r.run_status AS status, r.stage_name AS stage, r.started_at, r.completed_at,
    CASE WHEN r.completed_at IS NULL THEN NULL ELSE
        EXTRACT(EPOCH FROM r.completed_at - r.started_at)::double precision END
        AS duration_seconds,
    r.platform_code, r.vendor_code, r.rule_code,
    (SELECT COUNT(*)::int FROM metadata.operational_alerts a
     WHERE a.pipeline_run_id = r.pipeline_run_id
       AND a.alert_status IN ('OPEN', 'ACKNOWLEDGED')) AS active_alert_count
"""


class PipelineRunRepository:
    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool

    @staticmethod
    def _where_clause(filters: PipelineRunFilters) -> tuple[str, list[object]]:
        conditions = ["r.corvetra_run_id IS NOT NULL"]
        parameters: list[object] = []
        for expression, value in (
            ("ps.pipeline_key = %s", filters.pipeline),
            ("ps.environment_key = %s", filters.environment),
            ("r.run_status = %s", filters.status),
            ("r.stage_name = %s", filters.stage),
            ("ps.source_key = %s", filters.source),
            ("r.started_at >= %s", filters.started_from),
            ("r.started_at <= %s", filters.started_to),
        ):
            if value is not None:
                conditions.append(expression)
                parameters.append(value)
        if filters.search is not None:
            conditions.append("""(
                r.corvetra_run_id ILIKE %s ESCAPE E'\\\\'
                OR ps.pipeline_name ILIKE %s ESCAPE E'\\\\'
            )""")
            pattern = f"%{escape_like(filters.search)}%"
            parameters.extend([pattern, pattern])
        return f"WHERE {' AND '.join(conditions)}", parameters

    async def list_pipeline_runs(
        self, *, limit: int, offset: int, filters: PipelineRunFilters
    ) -> tuple[list[dict[str, Any]], int]:
        where_clause, parameters = self._where_clause(filters)
        from_clause = """
            FROM metadata.pipeline_runs r
            JOIN pipeline_state ps ON ps.pipeline_id = r.pipeline_id
        """
        count_query = f"{PIPELINE_STATE_CTE} SELECT COUNT(*) {from_clause} {where_clause}"
        list_query = f"""
            {PIPELINE_STATE_CTE}
            SELECT {RUN_SELECT}
            {from_clause}
            {where_clause}
            ORDER BY r.started_at DESC, r.pipeline_run_id DESC
            LIMIT %s OFFSET %s
        """
        async with self._pool.connection() as connection:
            result = await connection.execute(count_query, parameters)
            count_row = await result.fetchone()
            async with connection.cursor(row_factory=dict_row) as cursor:
                await cursor.execute(list_query, [*parameters, limit, offset])
                rows = await cursor.fetchall()
        return rows, int(count_row[0])

    async def get_pipeline_run(self, corvetra_run_id: str) -> dict[str, Any] | None:
        query = f"""
            {PIPELINE_STATE_CTE}
            SELECT {RUN_SELECT}, r.pipeline_run_id,
                   jsonb_build_object(
                       'dag_id', r.dag_id, 'airflow_run_id', r.airflow_run_id
                   ) AS airflow
            FROM metadata.pipeline_runs r
            JOIN pipeline_state ps ON ps.pipeline_id = r.pipeline_id
            WHERE r.corvetra_run_id = %s AND r.corvetra_run_id IS NOT NULL
        """
        rows = await self._fetchall(query, [corvetra_run_id])
        return rows[0] if rows else None

    async def get_alerts(self, pipeline_run_id: object) -> list[dict[str, Any]]:
        query = """
            SELECT alert_key, alert_title AS title, severity,
                   alert_status AS status, platform_code, vendor_code, rule_code,
                   alert_message AS message, detected_at, last_seen_at,
                   acknowledged_at, resolved_at
            FROM metadata.operational_alerts
            WHERE pipeline_run_id = %s
            ORDER BY detected_at DESC, alert_id DESC
        """
        return await self._fetchall(query, [pipeline_run_id])

    async def get_validation_summary(self, pipeline_run_id: object) -> dict[str, Any]:
        query = """
            SELECT COUNT(*)::int AS total,
                   COUNT(*) FILTER (WHERE result_status = 'PASSED')::int AS passed,
                   COUNT(*) FILTER (WHERE result_status = 'FAILED')::int AS failed,
                   COUNT(*) FILTER (WHERE result_status = 'NOT_EVALUATED')::int AS not_evaluated,
                   COUNT(*) FILTER (WHERE result_status = 'FAILED' AND effective_severity = 'BLOCKING')::int AS blocking_failed,
                   COUNT(*) FILTER (WHERE result_status = 'FAILED' AND effective_severity = 'WARNING')::int AS warning_failed,
                   MAX(evaluated_at) AS last_evaluated_at
            FROM metadata.validation_executions
            WHERE pipeline_run_id = %s
        """
        return (await self._fetchall(query, [pipeline_run_id]))[0]

    async def get_validation_executions(self, pipeline_run_id: object) -> list[dict[str, Any]]:
        query = """
            SELECT c.check_key, c.check_name AS name, c.check_type AS type,
                   c.dataset_name, c.column_name, x.result_status AS result,
                   x.effective_severity AS severity, x.platform_code,
                   x.rule_code, x.vendor_code, x.actual_value AS actual,
                   x.expected_value AS expected, x.result_message AS message,
                   x.evaluated_at
            FROM metadata.validation_executions x
            JOIN metadata.validation_checks c
              ON c.validation_check_id = x.validation_check_id
            WHERE x.pipeline_run_id = %s
            ORDER BY x.evaluated_at, c.check_key
        """
        return await self._fetchall(query, [pipeline_run_id])

    async def count_technical_evidence(self, pipeline_run_id: object) -> int:
        query = "SELECT COUNT(*) FROM metadata.technical_events WHERE pipeline_run_id = %s"
        async with self._pool.connection() as connection:
            result = await connection.execute(query, [pipeline_run_id])
            row = await result.fetchone()
        return int(row[0])

    async def get_technical_evidence(self, pipeline_run_id: object) -> list[dict[str, Any]]:
        query = """
            SELECT event_key, occurred_at, level, stage, platform_code,
                   vendor_code, rule_code, message
            FROM (
                SELECT technical_event_id, event_key, occurred_at,
                       event_level AS level, stage_name AS stage, platform_code,
                       vendor_code, rule_code, event_message AS message
                FROM metadata.technical_events
                WHERE pipeline_run_id = %s
                ORDER BY occurred_at DESC, technical_event_id DESC
                LIMIT 20
            ) recent
            ORDER BY occurred_at, technical_event_id
        """
        return await self._fetchall(query, [pipeline_run_id])

    async def _fetchall(self, query: str, parameters: list[object]) -> list[dict[str, Any]]:
        async with self._pool.connection() as connection:
            async with connection.cursor(row_factory=dict_row) as cursor:
                await cursor.execute(query, parameters)
                return await cursor.fetchall()
