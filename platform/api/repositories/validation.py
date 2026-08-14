from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from api.repositories.pipelines import PIPELINE_STATE_CTE, escape_like


@dataclass(frozen=True)
class ValidationFilters:
    pipeline: str | None = None
    source: str | None = None
    environment: str | None = None
    run: str | None = None
    result: str | None = None
    severity: str | None = None
    check_type: str | None = None
    evaluated_from: datetime | None = None
    evaluated_to: datetime | None = None
    search: str | None = None


VALIDATION_SELECT = """
    check_key, check_name AS name, check_type AS type, dataset_name,
    column_name, result_status AS result, effective_severity AS severity,
    execution_platform_code AS platform_code, execution_rule_code AS rule_code,
    execution_vendor_code AS vendor_code, actual_value AS actual,
    expected_value AS expected, result_message AS message, evaluated_at,
    stage_name AS stage,
    jsonb_build_object(
        'corvetra_run_id', corvetra_run_id, 'status', run_status,
        'stage', run_stage, 'started_at', started_at, 'completed_at', completed_at,
        'duration_seconds', CASE WHEN completed_at IS NULL THEN NULL ELSE
            EXTRACT(EPOCH FROM completed_at - started_at)::double precision END,
        'platform_code', run_platform_code, 'vendor_code', run_vendor_code,
        'rule_code', run_rule_code) AS run,
    jsonb_build_object('pipeline_key', pipeline_key, 'name', pipeline_name,
                       'operational_status', operational_status) AS pipeline,
    jsonb_build_object('source_key', source_key, 'name', source_name,
                       'source_type', source_type,
                       'operational_status', source_status) AS source,
    jsonb_build_object('environment_key', environment_key,
                       'name', environment_name) AS environment
"""


class ValidationRepository:
    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool

    @staticmethod
    def _scope_where(filters: ValidationFilters) -> tuple[str, list[object]]:
        conditions = ["c.is_enabled", "r.corvetra_run_id IS NOT NULL"]
        parameters: list[object] = []
        for expression, value in (
            ("ps.pipeline_key = %s", filters.pipeline),
            ("ps.source_key = %s", filters.source),
            ("ps.environment_key = %s", filters.environment),
            ("r.corvetra_run_id = %s", filters.run),
            ("x.evaluated_at >= %s", filters.evaluated_from),
            ("x.evaluated_at <= %s", filters.evaluated_to),
        ):
            if value is not None:
                conditions.append(expression)
                parameters.append(value)
        return " AND ".join(conditions), parameters

    @staticmethod
    def _result_where(filters: ValidationFilters) -> tuple[str, list[object]]:
        conditions = ["rank_number = 1"]
        parameters: list[object] = []
        for expression, value in (
            ("result_status = %s", filters.result),
            ("effective_severity = %s", filters.severity),
            ("check_type = %s", filters.check_type),
        ):
            if value is not None:
                conditions.append(expression)
                parameters.append(value)
        if filters.search is not None:
            pattern = f"%{escape_like(filters.search)}%"
            conditions.append("""(
                check_key ILIKE %s ESCAPE E'\\\\' OR check_name ILIKE %s ESCAPE E'\\\\'
                OR dataset_name ILIKE %s ESCAPE E'\\\\'
                OR COALESCE(column_name, '') ILIKE %s ESCAPE E'\\\\'
                OR pipeline_name ILIKE %s ESCAPE E'\\\\'
                OR source_name ILIKE %s ESCAPE E'\\\\'
                OR corvetra_run_id ILIKE %s ESCAPE E'\\\\'
                OR execution_platform_code ILIKE %s ESCAPE E'\\\\'
                OR COALESCE(execution_vendor_code, '') ILIKE %s ESCAPE E'\\\\'
                OR COALESCE(execution_rule_code, '') ILIKE %s ESCAPE E'\\\\'
            )""")
            parameters.extend([pattern] * 10)
        return " AND ".join(conditions), parameters

    @classmethod
    def _projection(cls, filters: ValidationFilters) -> tuple[str, list[object]]:
        scope_where, scope_parameters = cls._scope_where(filters)
        result_where, result_parameters = cls._result_where(filters)
        query = f"""
            {PIPELINE_STATE_CTE}, eligible AS (
                SELECT x.validation_execution_id, x.validation_check_id,
                       x.result_status, x.effective_severity,
                       x.platform_code AS execution_platform_code,
                       x.rule_code AS execution_rule_code,
                       x.vendor_code AS execution_vendor_code,
                       x.actual_value, x.expected_value, x.result_message,
                       x.evaluated_at, x.stage_name,
                       c.check_key, c.check_name, c.check_type,
                       c.dataset_name, c.column_name,
                       r.pipeline_run_id, r.corvetra_run_id, r.run_status,
                       r.stage_name AS run_stage, r.started_at, r.completed_at,
                       r.platform_code AS run_platform_code,
                       r.vendor_code AS run_vendor_code,
                       r.rule_code AS run_rule_code,
                       ps.pipeline_key, ps.pipeline_name, ps.operational_status,
                       ps.source_key, ps.source_name, ps.source_type, ps.source_status,
                       ps.environment_key, ps.environment_name
                FROM metadata.validation_executions x
                JOIN metadata.validation_checks c
                  ON c.validation_check_id = x.validation_check_id
                JOIN metadata.pipeline_runs r ON r.pipeline_run_id = x.pipeline_run_id
                JOIN pipeline_state ps ON ps.pipeline_id = r.pipeline_id
                WHERE {scope_where}
            ), ranked AS (
                SELECT eligible.*,
                       row_number() OVER (
                         PARTITION BY validation_check_id
                         ORDER BY evaluated_at DESC, validation_execution_id DESC
                       ) AS rank_number
                FROM eligible
            ), selected AS (
                SELECT * FROM ranked WHERE {result_where}
            )
        """
        return query, [*scope_parameters, *result_parameters]

    async def list_validation(self, *, limit: int, offset: int, filters: ValidationFilters) -> tuple[list[dict[str, Any]], int]:
        projection, parameters = self._projection(filters)
        count_query = f"{projection} SELECT COUNT(*) FROM selected"
        list_query = f"""
            {projection} SELECT {VALIDATION_SELECT} FROM selected
            ORDER BY evaluated_at DESC, check_key ASC LIMIT %s OFFSET %s
        """
        async with self._pool.connection() as connection:
            result = await connection.execute(count_query, parameters)
            total = int((await result.fetchone())[0])
            async with connection.cursor(row_factory=dict_row) as cursor:
                await cursor.execute(list_query, [*parameters, limit, offset])
                rows = await cursor.fetchall()
        return rows, total

    async def get_execution(self, check_key: str, corvetra_run_id: str) -> dict[str, Any] | None:
        query = f"""
            {PIPELINE_STATE_CTE}, selected AS (
                SELECT x.validation_execution_id, x.validation_check_id,
                       x.result_status, x.effective_severity,
                       x.platform_code AS execution_platform_code,
                       x.rule_code AS execution_rule_code,
                       x.vendor_code AS execution_vendor_code,
                       x.actual_value, x.expected_value, x.result_message,
                       x.evaluated_at, x.stage_name,
                       c.check_key, c.check_name, c.check_type,
                       c.dataset_name, c.column_name,
                       r.corvetra_run_id, r.run_status,
                       r.stage_name AS run_stage, r.started_at, r.completed_at,
                       r.platform_code AS run_platform_code,
                       r.vendor_code AS run_vendor_code, r.rule_code AS run_rule_code,
                       ps.pipeline_key, ps.pipeline_name, ps.operational_status,
                       ps.source_key, ps.source_name, ps.source_type, ps.source_status,
                       ps.environment_key, ps.environment_name
                FROM metadata.validation_executions x
                JOIN metadata.validation_checks c USING (validation_check_id)
                JOIN metadata.pipeline_runs r USING (pipeline_run_id)
                JOIN pipeline_state ps ON ps.pipeline_id = r.pipeline_id
                WHERE c.check_key = %s AND r.corvetra_run_id = %s
                  AND r.corvetra_run_id IS NOT NULL
            ) SELECT {VALIDATION_SELECT}, validation_execution_id,
                     validation_check_id FROM selected
        """
        rows = await self._fetchall(query, [check_key, corvetra_run_id])
        return rows[0] if rows else None

    async def get_alerts(self, execution_id: object) -> list[dict[str, Any]]:
        return await self._fetchall("""
            SELECT alert_key, alert_title AS title, severity, alert_status AS status,
                   platform_code, vendor_code, rule_code, alert_message AS message,
                   detected_at, last_seen_at, acknowledged_at, resolved_at
            FROM metadata.operational_alerts WHERE validation_execution_id = %s
            ORDER BY detected_at DESC, alert_key DESC
        """, [execution_id])

    async def count_evidence(self, execution_id: object) -> int:
        async with self._pool.connection() as connection:
            result = await connection.execute(
                "SELECT COUNT(*) FROM metadata.technical_events WHERE validation_execution_id = %s",
                [execution_id])
            return int((await result.fetchone())[0])

    async def get_evidence(self, execution_id: object) -> list[dict[str, Any]]:
        return await self._fetchall("""
            SELECT event_key, occurred_at, event_level AS level, stage_name AS stage,
                   platform_code, vendor_code, rule_code, event_message AS message
            FROM metadata.technical_events WHERE validation_execution_id = %s
            ORDER BY occurred_at, technical_event_id LIMIT 5
        """, [execution_id])

    async def get_history(self, check_id: object) -> list[dict[str, Any]]:
        return await self._fetchall("""
            SELECT r.corvetra_run_id, x.result_status AS result,
                   x.effective_severity AS severity, x.actual_value AS actual,
                   x.expected_value AS expected, x.platform_code,
                   x.vendor_code, x.rule_code, x.evaluated_at
            FROM metadata.validation_executions x
            JOIN metadata.pipeline_runs r USING (pipeline_run_id)
            WHERE x.validation_check_id = %s AND r.corvetra_run_id IS NOT NULL
            ORDER BY x.evaluated_at DESC, x.validation_execution_id DESC LIMIT 10
        """, [check_id])

    async def _fetchall(self, query: str, parameters: list[object]) -> list[dict[str, Any]]:
        async with self._pool.connection() as connection:
            async with connection.cursor(row_factory=dict_row) as cursor:
                await cursor.execute(query, parameters)
                return await cursor.fetchall()
