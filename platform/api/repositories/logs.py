from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from api.repositories.pipelines import PIPELINE_STATE_CTE, escape_like


@dataclass(frozen=True)
class LogFilters:
    environment: str | None = None
    pipeline: str | None = None
    run: str | None = None
    source: str | None = None
    stage: str | None = None
    alert: str | None = None
    check: str | None = None
    levels: tuple[str, ...] = ()
    platform_code: str | None = None
    vendor_code: str | None = None
    rule_code: str | None = None
    occurred_from: datetime | None = None
    occurred_to: datetime | None = None
    search: str | None = None
    sort: str = "newest"


LOG_JOINS = """
    FROM metadata.technical_events te
    JOIN metadata.environments e ON e.environment_id = te.environment_id
    LEFT JOIN pipeline_state ps ON ps.pipeline_id = te.pipeline_id
    LEFT JOIN metadata.pipeline_runs r ON r.pipeline_run_id = te.pipeline_run_id
    LEFT JOIN metadata.data_sources s ON s.data_source_id = te.data_source_id
    LEFT JOIN metadata.operational_alerts a ON a.alert_id = te.alert_id
    LEFT JOIN metadata.validation_executions x
      ON x.validation_execution_id = te.validation_execution_id
    LEFT JOIN metadata.validation_checks c ON c.validation_check_id = x.validation_check_id
"""

LOG_ITEM_SELECT = """
    te.event_key, te.occurred_at, te.event_level AS level,
    te.event_message AS message,
    jsonb_build_object('environment_key', e.environment_key,
                       'name', e.environment_name) AS environment,
    CASE WHEN ps.pipeline_id IS NULL THEN NULL ELSE
      jsonb_build_object('pipeline_key', ps.pipeline_key, 'name', ps.pipeline_name,
                         'operational_status', ps.operational_status) END AS pipeline,
    CASE WHEN r.corvetra_run_id IS NULL THEN NULL ELSE
      jsonb_build_object(
        'corvetra_run_id', r.corvetra_run_id, 'status', r.run_status,
        'stage', r.stage_name, 'started_at', r.started_at,
        'completed_at', r.completed_at,
        'duration_seconds', CASE WHEN r.completed_at IS NULL THEN NULL ELSE
          EXTRACT(EPOCH FROM r.completed_at - r.started_at)::double precision END,
        'platform_code', r.platform_code, 'vendor_code', r.vendor_code,
        'rule_code', r.rule_code) END AS run,
    CASE WHEN s.data_source_id IS NULL THEN NULL ELSE
      jsonb_build_object('source_key', s.source_key, 'name', s.source_name,
                         'source_type', s.source_type,
                         'operational_status', s.operational_status) END AS source,
    te.stage_name AS stage, te.platform_code, te.vendor_code, te.rule_code,
    CASE WHEN a.alert_id IS NULL THEN NULL ELSE
      jsonb_build_object('alert_key', a.alert_key, 'status', a.alert_status)
      END AS related_alert,
    CASE WHEN x.validation_execution_id IS NULL THEN NULL ELSE
      jsonb_build_object('check_key', c.check_key, 'name', c.check_name,
        'result', x.result_status, 'severity', x.effective_severity,
        'evaluated_at', x.evaluated_at) END AS related_validation
"""


class LogRepository:
    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool

    @staticmethod
    def _where_clause(filters: LogFilters) -> tuple[str, list[object]]:
        conditions: list[str] = []
        parameters: list[object] = []
        for expression, value in (
            ("e.environment_key = %s", filters.environment),
            ("ps.pipeline_key = %s", filters.pipeline),
            ("r.corvetra_run_id = %s", filters.run),
            ("s.source_key = %s", filters.source),
            ("te.stage_name = %s", filters.stage),
            ("c.check_key = %s", filters.check),
            ("te.platform_code = %s", filters.platform_code),
            ("te.vendor_code = %s", filters.vendor_code),
            ("te.rule_code = %s", filters.rule_code),
            ("te.occurred_at >= %s", filters.occurred_from),
            ("te.occurred_at <= %s", filters.occurred_to),
        ):
            if value is not None:
                conditions.append(expression)
                parameters.append(value)
        if filters.alert is not None:
            conditions.append("""te.pipeline_run_id = (
                SELECT alert_run.pipeline_run_id
                FROM metadata.operational_alerts alert_run
                WHERE alert_run.alert_key = %s
            )""")
            parameters.append(filters.alert)
        if filters.levels:
            conditions.append("te.event_level = ANY(%s)")
            parameters.append(list(filters.levels))
        if filters.search is not None:
            pattern = f"%{escape_like(filters.search)}%"
            conditions.append("""(
                te.event_key ILIKE %s ESCAPE E'\\\\'
                OR te.event_message ILIKE %s ESCAPE E'\\\\'
                OR COALESCE(r.corvetra_run_id, '') ILIKE %s ESCAPE E'\\\\'
                OR COALESCE(ps.pipeline_name, '') ILIKE %s ESCAPE E'\\\\'
                OR COALESCE(s.source_name, '') ILIKE %s ESCAPE E'\\\\'
                OR COALESCE(c.check_key, '') ILIKE %s ESCAPE E'\\\\'
                OR COALESCE(c.check_name, '') ILIKE %s ESCAPE E'\\\\'
                OR COALESCE(te.platform_code, '') ILIKE %s ESCAPE E'\\\\'
                OR COALESCE(te.vendor_code, '') ILIKE %s ESCAPE E'\\\\'
                OR COALESCE(te.rule_code, '') ILIKE %s ESCAPE E'\\\\'
            )""")
            parameters.extend([pattern] * 10)
        return (f"WHERE {' AND '.join(conditions)}" if conditions else ""), parameters

    async def list_logs(self, *, limit: int, offset: int, filters: LogFilters) -> tuple[list[dict[str, Any]], int]:
        where, parameters = self._where_clause(filters)
        direction = "DESC" if filters.sort == "newest" else "ASC"
        count_query = f"{PIPELINE_STATE_CTE} SELECT COUNT(*) {LOG_JOINS} {where}"
        list_query = f"""
            {PIPELINE_STATE_CTE} SELECT {LOG_ITEM_SELECT} {LOG_JOINS} {where}
            ORDER BY te.occurred_at {direction}, te.event_key {direction},
                     te.technical_event_id {direction}
            LIMIT %s OFFSET %s
        """
        async with self._pool.connection() as connection:
            result = await connection.execute(count_query, parameters)
            total = int((await result.fetchone())[0])
            async with connection.cursor(row_factory=dict_row) as cursor:
                await cursor.execute(list_query, [*parameters, limit, offset])
                rows = await cursor.fetchall()
        return rows, total

    async def get_log(self, event_key: str) -> dict[str, Any] | None:
        query = f"""
            {PIPELINE_STATE_CTE}
            SELECT {LOG_ITEM_SELECT}, te.event_details,
              CASE WHEN a.alert_id IS NULL THEN NULL ELSE jsonb_build_object(
                'alert_key', a.alert_key, 'title', a.alert_title,
                'severity', a.severity, 'status', a.alert_status,
                'platform_code', a.platform_code, 'vendor_code', a.vendor_code,
                'rule_code', a.rule_code, 'message', a.alert_message,
                'detected_at', a.detected_at, 'last_seen_at', a.last_seen_at,
                'acknowledged_at', a.acknowledged_at, 'resolved_at', a.resolved_at
              ) END AS alert,
              CASE WHEN x.validation_execution_id IS NULL THEN NULL ELSE
                jsonb_build_object(
                  'check_key', c.check_key, 'name', c.check_name, 'type', c.check_type,
                  'dataset_name', c.dataset_name, 'column_name', c.column_name,
                  'result', x.result_status, 'severity', x.effective_severity,
                  'platform_code', x.platform_code, 'rule_code', x.rule_code,
                  'vendor_code', x.vendor_code, 'actual', x.actual_value,
                  'expected', x.expected_value, 'message', x.result_message,
                  'evaluated_at', x.evaluated_at
                ) END AS validation_execution
            {LOG_JOINS} WHERE te.event_key = %s
        """
        rows = await self._fetchall(query, [event_key])
        return rows[0] if rows else None

    async def _fetchall(self, query: str, parameters: list[object]) -> list[dict[str, Any]]:
        async with self._pool.connection() as connection:
            async with connection.cursor(row_factory=dict_row) as cursor:
                await cursor.execute(query, parameters)
                return await cursor.fetchall()
