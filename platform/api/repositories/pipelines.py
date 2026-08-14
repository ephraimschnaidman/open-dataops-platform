from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

ACTIVE_ALERTS = "('OPEN', 'ACKNOWLEDGED')"

PIPELINE_STATE_CTE = f"""
WITH pipeline_state AS (
    SELECT
        p.pipeline_id, p.pipeline_key, p.pipeline_name, p.airflow_dag_id,
        p.is_enabled, p.environment_id, p.data_source_id,
        e.environment_key, e.environment_name,
        s.source_key, s.source_name, s.source_type,
        s.operational_status AS source_status,
        latest.pipeline_run_id AS latest_run_uuid,
        latest.corvetra_run_id, latest.run_status, latest.stage_name,
        latest.started_at, latest.completed_at, latest.platform_code,
        latest.vendor_code, latest.rule_code,
        issue.alert_key, issue.alert_title, issue.severity AS alert_severity,
        issue.alert_status, issue.alert_platform_code, issue.alert_vendor_code,
        issue.alert_rule_code, issue.alert_message, issue.detected_at,
        issue.last_seen_at, issue.acknowledged_at, issue.resolved_at,
        CASE
            WHEN NOT p.is_enabled THEN 'DISABLED'
            WHEN latest.run_status = 'RUNNING' THEN 'RUNNING'
            WHEN active_severity.has_critical THEN 'FAILED'
            WHEN active_severity.has_warning THEN 'WARNING'
            WHEN latest.run_status = 'FAILED' THEN 'FAILED'
            WHEN s.operational_status = 'DISCONNECTED' THEN 'FAILED'
            WHEN s.operational_status IN ('WARNING', 'DISABLED') THEN 'WARNING'
            WHEN latest.run_status = 'SUCCESS' AND EXISTS (
                SELECT 1
                FROM metadata.validation_executions vx
                WHERE vx.pipeline_run_id = latest.pipeline_run_id
                  AND vx.result_status = 'FAILED'
                  AND vx.effective_severity = 'WARNING'
            ) THEN 'WARNING'
            WHEN latest.run_status = 'SUCCESS' THEN 'HEALTHY'
            ELSE 'WARNING'
        END AS operational_status
    FROM metadata.pipelines p
    JOIN metadata.environments e ON e.environment_id = p.environment_id
    JOIN metadata.data_sources s ON s.data_source_id = p.data_source_id
    LEFT JOIN LATERAL (
        SELECT r.*
        FROM metadata.pipeline_runs r
        WHERE r.pipeline_id = p.pipeline_id
          AND r.corvetra_run_id IS NOT NULL
        ORDER BY r.started_at DESC, r.pipeline_run_id DESC
        LIMIT 1
    ) latest ON TRUE
    LEFT JOIN LATERAL (
        SELECT
            bool_or(a.severity = 'CRITICAL') AS has_critical,
            bool_or(a.severity = 'WARNING') AS has_warning
        FROM metadata.operational_alerts a
        JOIN metadata.pipeline_runs ar ON ar.pipeline_run_id = a.pipeline_run_id
        WHERE ar.pipeline_id = p.pipeline_id
          AND a.alert_status IN {ACTIVE_ALERTS}
    ) active_severity ON TRUE
    LEFT JOIN LATERAL (
        SELECT a.alert_key, a.alert_title, a.severity, a.alert_status,
               a.platform_code AS alert_platform_code,
               a.vendor_code AS alert_vendor_code,
               a.rule_code AS alert_rule_code,
               a.alert_message, a.detected_at, a.last_seen_at,
               a.acknowledged_at, a.resolved_at
        FROM metadata.operational_alerts a
        JOIN metadata.pipeline_runs ar ON ar.pipeline_run_id = a.pipeline_run_id
        WHERE ar.pipeline_id = p.pipeline_id
          AND a.alert_status IN {ACTIVE_ALERTS}
        ORDER BY CASE a.severity WHEN 'CRITICAL' THEN 0 ELSE 1 END,
                 a.last_seen_at DESC, a.alert_id DESC
        LIMIT 1
    ) issue ON TRUE
)
"""

PIPELINE_ITEM_COLUMNS = """
    pipeline_key,
    pipeline_name AS name,
    jsonb_build_object(
        'environment_key', environment_key, 'name', environment_name
    ) AS environment,
    jsonb_build_object(
        'source_key', source_key, 'name', source_name,
        'source_type', source_type, 'operational_status', source_status
    ) AS source,
    is_enabled,
    operational_status,
    CASE WHEN corvetra_run_id IS NULL THEN NULL ELSE jsonb_build_object(
        'corvetra_run_id', corvetra_run_id, 'status', run_status,
        'stage', stage_name, 'started_at', started_at,
        'completed_at', completed_at,
        'duration_seconds', CASE WHEN completed_at IS NULL THEN NULL ELSE
            EXTRACT(EPOCH FROM completed_at - started_at)::double precision END,
        'platform_code', platform_code, 'vendor_code', vendor_code,
        'rule_code', rule_code
    ) END AS latest_run,
    CASE WHEN alert_key IS NULL THEN NULL ELSE jsonb_build_object(
        'alert_key', alert_key, 'title', alert_title,
        'severity', alert_severity, 'status', alert_status,
        'platform_code', alert_platform_code,
        'vendor_code', alert_vendor_code, 'rule_code', alert_rule_code,
        'message', alert_message, 'detected_at', detected_at,
        'last_seen_at', last_seen_at, 'acknowledged_at', acknowledged_at,
        'resolved_at', resolved_at
    ) END AS current_issue
"""


@dataclass(frozen=True)
class PipelineFilters:
    environment: str | None = None
    operational_status: str | None = None
    source: str | None = None
    enabled: bool | None = None
    search: str | None = None


def escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def build_pipeline_where(filters: PipelineFilters) -> tuple[str, list[object]]:
    conditions: list[str] = []
    parameters: list[object] = []
    for expression, value in (
        ("environment_key = %s", filters.environment),
        ("operational_status = %s", filters.operational_status),
        ("source_key = %s", filters.source),
        ("is_enabled = %s", filters.enabled),
    ):
        if value is not None:
            conditions.append(expression)
            parameters.append(value)
    if filters.search is not None:
        conditions.append("""(
            pipeline_key ILIKE %s ESCAPE E'\\\\'
            OR pipeline_name ILIKE %s ESCAPE E'\\\\'
            OR source_key ILIKE %s ESCAPE E'\\\\'
            OR source_name ILIKE %s ESCAPE E'\\\\'
            OR airflow_dag_id ILIKE %s ESCAPE E'\\\\'
        )""")
        pattern = f"%{escape_like(filters.search)}%"
        parameters.extend([pattern] * 5)
    return (f"WHERE {' AND '.join(conditions)}" if conditions else ""), parameters


class PipelineRepository:
    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool

    async def list_pipelines(
        self, *, limit: int, offset: int, filters: PipelineFilters
    ) -> tuple[list[dict[str, Any]], int]:
        where_clause, parameters = build_pipeline_where(filters)
        count_query = f"{PIPELINE_STATE_CTE} SELECT COUNT(*) FROM pipeline_state {where_clause}"
        list_query = f"""
            {PIPELINE_STATE_CTE}
            SELECT {PIPELINE_ITEM_COLUMNS}
            FROM pipeline_state
            {where_clause}
            ORDER BY name, pipeline_key
            LIMIT %s OFFSET %s
        """
        async with self._pool.connection() as connection:
            count_result = await connection.execute(count_query, parameters)
            count_row = await count_result.fetchone()
            async with connection.cursor(row_factory=dict_row) as cursor:
                await cursor.execute(list_query, [*parameters, limit, offset])
                rows = await cursor.fetchall()
        return rows, int(count_row[0])

    async def get_pipeline(self, pipeline_key: str) -> dict[str, Any] | None:
        query = f"""
            {PIPELINE_STATE_CTE}
            SELECT {PIPELINE_ITEM_COLUMNS}, airflow_dag_id, pipeline_id
            FROM pipeline_state
            WHERE pipeline_key = %s
        """
        async with self._pool.connection() as connection:
            async with connection.cursor(row_factory=dict_row) as cursor:
                await cursor.execute(query, [pipeline_key])
                return await cursor.fetchone()

    async def get_recent_runs(self, pipeline_id: object) -> list[dict[str, Any]]:
        query = """
            SELECT corvetra_run_id, run_status AS status, stage_name AS stage,
                   started_at, completed_at,
                   CASE WHEN completed_at IS NULL THEN NULL ELSE
                       EXTRACT(EPOCH FROM completed_at - started_at)::double precision END
                       AS duration_seconds,
                   platform_code, vendor_code, rule_code
            FROM metadata.pipeline_runs
            WHERE pipeline_id = %s AND corvetra_run_id IS NOT NULL
            ORDER BY started_at DESC, pipeline_run_id DESC
            LIMIT 10
        """
        return await self._fetchall(query, [pipeline_id])

    async def get_validation_summary(self, pipeline_id: object) -> dict[str, Any]:
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
            WHERE r.pipeline_id = %s AND r.corvetra_run_id IS NOT NULL
        """
        return await self._fetchone_required(query, [pipeline_id])

    async def get_active_alerts(self, pipeline_id: object) -> list[dict[str, Any]]:
        query = f"""
            SELECT a.alert_key, a.alert_title AS title, a.severity,
                   a.alert_status AS status, a.platform_code, a.vendor_code,
                   a.rule_code, a.alert_message AS message, a.detected_at,
                   a.last_seen_at, a.acknowledged_at, a.resolved_at
            FROM metadata.operational_alerts a
            JOIN metadata.pipeline_runs r ON r.pipeline_run_id = a.pipeline_run_id
            WHERE r.pipeline_id = %s AND a.alert_status IN {ACTIVE_ALERTS}
            ORDER BY CASE a.severity WHEN 'CRITICAL' THEN 0 ELSE 1 END,
                     a.last_seen_at DESC, a.alert_id DESC
        """
        return await self._fetchall(query, [pipeline_id])

    async def count_technical_evidence(self, pipeline_id: object) -> int:
        query = "SELECT COUNT(*) FROM metadata.technical_events WHERE pipeline_id = %s"
        async with self._pool.connection() as connection:
            result = await connection.execute(query, [pipeline_id])
            row = await result.fetchone()
        return int(row[0])

    async def _fetchall(self, query: str, parameters: list[object]) -> list[dict[str, Any]]:
        async with self._pool.connection() as connection:
            async with connection.cursor(row_factory=dict_row) as cursor:
                await cursor.execute(query, parameters)
                return await cursor.fetchall()

    async def _fetchone_required(self, query: str, parameters: list[object]) -> dict[str, Any]:
        rows = await self._fetchall(query, parameters)
        return rows[0]
