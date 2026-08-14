from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from api.repositories.pipelines import PIPELINE_STATE_CTE, escape_like


@dataclass(frozen=True)
class AlertFilters:
    status: str | None = None
    severity: str | None = None
    environment: str | None = None
    pipeline: str | None = None
    source: str | None = None
    platform_code: str | None = None
    activity_from: datetime | None = None
    activity_to: datetime | None = None
    search: str | None = None


ALERT_ITEM_SELECT = """
    a.alert_key, a.alert_title AS title, a.severity,
    a.alert_status AS status, a.platform_code, a.vendor_code, a.rule_code,
    a.alert_message AS message, a.detected_at, a.last_seen_at,
    a.acknowledged_at, a.resolved_at,
    jsonb_build_object('pipeline_key', ps.pipeline_key, 'name', ps.pipeline_name,
                       'operational_status', ps.operational_status) AS pipeline,
    jsonb_build_object(
        'corvetra_run_id', r.corvetra_run_id, 'status', r.run_status,
        'stage', r.stage_name, 'started_at', r.started_at,
        'completed_at', r.completed_at,
        'duration_seconds', CASE WHEN r.completed_at IS NULL THEN NULL ELSE
            EXTRACT(EPOCH FROM r.completed_at - r.started_at)::double precision END,
        'platform_code', r.platform_code, 'vendor_code', r.vendor_code,
        'rule_code', r.rule_code
    ) AS run,
    jsonb_build_object('source_key', ps.source_key, 'name', ps.source_name,
                       'source_type', ps.source_type,
                       'operational_status', ps.source_status) AS source,
    jsonb_build_object('environment_key', ps.environment_key,
                       'name', ps.environment_name) AS environment
"""


class AlertRepository:
    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool

    @staticmethod
    def _where_clause(filters: AlertFilters) -> tuple[str, list[object]]:
        conditions = ["r.corvetra_run_id IS NOT NULL"]
        parameters: list[object] = []
        if filters.status == "ACTIVE":
            conditions.append("a.alert_status IN ('OPEN', 'ACKNOWLEDGED')")
        elif filters.status is not None:
            conditions.append("a.alert_status = %s")
            parameters.append(filters.status)
        for expression, value in (
            ("a.severity = %s", filters.severity),
            ("ps.environment_key = %s", filters.environment),
            ("ps.pipeline_key = %s", filters.pipeline),
            ("ps.source_key = %s", filters.source),
            ("a.platform_code = %s", filters.platform_code),
            ("a.last_seen_at >= %s", filters.activity_from),
            ("a.last_seen_at <= %s", filters.activity_to),
        ):
            if value is not None:
                conditions.append(expression)
                parameters.append(value)
        if filters.search is not None:
            pattern = f"%{escape_like(filters.search)}%"
            conditions.append("""(
                a.alert_key ILIKE %s ESCAPE E'\\\\'
                OR a.alert_title ILIKE %s ESCAPE E'\\\\'
                OR a.alert_message ILIKE %s ESCAPE E'\\\\'
                OR ps.pipeline_name ILIKE %s ESCAPE E'\\\\'
                OR ps.source_name ILIKE %s ESCAPE E'\\\\'
                OR r.corvetra_run_id ILIKE %s ESCAPE E'\\\\'
                OR a.platform_code ILIKE %s ESCAPE E'\\\\'
                OR COALESCE(a.vendor_code, '') ILIKE %s ESCAPE E'\\\\'
                OR COALESCE(a.rule_code, '') ILIKE %s ESCAPE E'\\\\'
            )""")
            parameters.extend([pattern] * 9)
        return f"WHERE {' AND '.join(conditions)}", parameters

    async def list_alerts(self, *, limit: int, offset: int, filters: AlertFilters) -> tuple[list[dict[str, Any]], int]:
        where, parameters = self._where_clause(filters)
        joins = """
            FROM metadata.operational_alerts a
            JOIN metadata.pipeline_runs r ON r.pipeline_run_id = a.pipeline_run_id
            JOIN pipeline_state ps ON ps.pipeline_id = r.pipeline_id
            LEFT JOIN metadata.validation_executions x
              ON x.validation_execution_id = a.validation_execution_id
            LEFT JOIN metadata.validation_checks c
              ON c.validation_check_id = x.validation_check_id
        """
        count_query = f"{PIPELINE_STATE_CTE} SELECT COUNT(*) {joins} {where}"
        list_query = f"""
            {PIPELINE_STATE_CTE}
            SELECT {ALERT_ITEM_SELECT},
                   CASE WHEN x.validation_execution_id IS NULL THEN NULL ELSE
                     jsonb_build_object('check_key', c.check_key, 'name', c.check_name,
                       'result', x.result_status, 'severity', x.effective_severity,
                       'evaluated_at', x.evaluated_at) END AS validation_execution
            {joins} {where}
            ORDER BY a.last_seen_at DESC, a.detected_at DESC, a.alert_key DESC
            LIMIT %s OFFSET %s
        """
        async with self._pool.connection() as connection:
            result = await connection.execute(count_query, parameters)
            total = int((await result.fetchone())[0])
            async with connection.cursor(row_factory=dict_row) as cursor:
                await cursor.execute(list_query, [*parameters, limit, offset])
                rows = await cursor.fetchall()
        return rows, total

    async def get_alert(self, alert_key: str) -> dict[str, Any] | None:
        query = f"""
            {PIPELINE_STATE_CTE}
            SELECT {ALERT_ITEM_SELECT}, a.alert_id, a.pipeline_run_id,
                   CASE WHEN x.validation_execution_id IS NULL THEN NULL ELSE
                     jsonb_build_object(
                       'check_key', c.check_key, 'name', c.check_name,
                       'type', c.check_type, 'dataset_name', c.dataset_name,
                       'column_name', c.column_name, 'result', x.result_status,
                       'severity', x.effective_severity, 'platform_code', x.platform_code,
                       'rule_code', x.rule_code, 'vendor_code', x.vendor_code,
                       'actual', x.actual_value, 'expected', x.expected_value,
                       'message', x.result_message, 'evaluated_at', x.evaluated_at
                     ) END AS validation_execution
            FROM metadata.operational_alerts a
            JOIN metadata.pipeline_runs r ON r.pipeline_run_id = a.pipeline_run_id
            JOIN pipeline_state ps ON ps.pipeline_id = r.pipeline_id
            LEFT JOIN metadata.validation_executions x
              ON x.validation_execution_id = a.validation_execution_id
            LEFT JOIN metadata.validation_checks c
              ON c.validation_check_id = x.validation_check_id
            WHERE a.alert_key = %s AND r.corvetra_run_id IS NOT NULL
        """
        rows = await self._fetchall(query, [alert_key])
        return rows[0] if rows else None

    async def count_evidence(self, pipeline_run_id: object) -> int:
        async with self._pool.connection() as connection:
            result = await connection.execute(
                "SELECT COUNT(*) FROM metadata.technical_events WHERE pipeline_run_id = %s",
                [pipeline_run_id],
            )
            return int((await result.fetchone())[0])

    async def get_evidence(self, pipeline_run_id: object) -> list[dict[str, Any]]:
        query = """
            SELECT event_key, occurred_at, level, stage, platform_code,
                   vendor_code, rule_code, message
            FROM (
                SELECT technical_event_id, event_key, occurred_at,
                       event_level AS level, stage_name AS stage, platform_code,
                       vendor_code, rule_code, event_message AS message
                FROM metadata.technical_events
                WHERE pipeline_run_id = %s
                ORDER BY occurred_at DESC, technical_event_id DESC LIMIT 5
            ) recent
            ORDER BY occurred_at, technical_event_id
        """
        return await self._fetchall(query, [pipeline_run_id])

    async def _fetchall(self, query: str, parameters: list[object]) -> list[dict[str, Any]]:
        async with self._pool.connection() as connection:
            async with connection.cursor(row_factory=dict_row) as cursor:
                await cursor.execute(query, parameters)
                return await cursor.fetchall()
