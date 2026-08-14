from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from api.repositories.pipeline_runs import RUN_SELECT
from api.repositories.pipelines import PIPELINE_ITEM_COLUMNS, PIPELINE_STATE_CTE


@dataclass(frozen=True)
class AggregationFilters:
    environment: str | None = None
    pipeline: str | None = None
    source: str | None = None


class AggregationRepository:
    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool

    @staticmethod
    def _pipeline_scope(filters: AggregationFilters, alias: str = "ps") -> tuple[str, list[object]]:
        conditions: list[str] = []
        parameters: list[object] = []
        for expression, value in (
            (f"{alias}.environment_key = %s", filters.environment),
            (f"{alias}.pipeline_key = %s", filters.pipeline),
            (f"{alias}.source_key = %s", filters.source),
        ):
            if value is not None:
                conditions.append(expression)
                parameters.append(value)
        return (" AND ".join(conditions) if conditions else "TRUE"), parameters

    async def get_pipelines(self, filters: AggregationFilters) -> list[dict[str, Any]]:
        where, parameters = self._pipeline_scope(filters)
        query = f"""
            {PIPELINE_STATE_CTE}
            SELECT {PIPELINE_ITEM_COLUMNS}, pipeline_id, data_source_id,
                   latest_run_uuid
            FROM pipeline_state ps
            WHERE {where}
        """
        return await self._fetchall(query, parameters)

    async def get_sources(self, filters: AggregationFilters) -> list[dict[str, Any]]:
        conditions: list[str] = []
        parameters: list[object] = []
        for expression, value in (
            ("e.environment_key = %s", filters.environment),
            ("p.pipeline_key = %s", filters.pipeline),
            ("s.source_key = %s", filters.source),
        ):
            if value is not None:
                conditions.append(expression)
                parameters.append(value)
        where = " AND ".join(conditions) if conditions else "TRUE"
        query = f"""
            SELECT s.data_source_id, s.source_key, s.source_name AS name,
                   s.source_type,
                   jsonb_build_object('environment_key', e.environment_key,
                                      'name', e.environment_name) AS environment,
                   s.operational_status,
                   COUNT(DISTINCT connected.pipeline_id)::int AS connected_pipeline_count,
                   MAX(te.occurred_at) AS last_observed_at
            FROM metadata.data_sources s
            JOIN metadata.environments e USING (environment_id)
            LEFT JOIN metadata.pipelines p ON p.data_source_id = s.data_source_id
            LEFT JOIN metadata.pipelines connected ON connected.data_source_id = s.data_source_id
            LEFT JOIN metadata.technical_events te ON te.data_source_id = s.data_source_id
            WHERE {where}
            GROUP BY s.data_source_id, e.environment_key, e.environment_name
        """
        return await self._fetchall(query, parameters)

    async def get_active_alerts(self, filters: AggregationFilters) -> list[dict[str, Any]]:
        where, parameters = self._pipeline_scope(filters)
        query = f"""
            {PIPELINE_STATE_CTE}
            SELECT a.alert_id, a.alert_key, a.alert_title AS title, a.severity,
                   a.alert_status AS status, a.platform_code, a.vendor_code,
                   a.rule_code, a.alert_message AS message, a.detected_at,
                   a.last_seen_at, a.pipeline_run_id, a.validation_execution_id,
                   ps.pipeline_id, ps.data_source_id,
                   jsonb_build_object('environment_key', ps.environment_key,
                                      'name', ps.environment_name) AS environment,
                   jsonb_build_object('pipeline_key', ps.pipeline_key,
                                      'name', ps.pipeline_name,
                                      'operational_status', ps.operational_status) AS pipeline,
                   jsonb_build_object('source_key', ps.source_key,
                                      'name', ps.source_name,
                                      'source_type', ps.source_type,
                                      'operational_status', ps.source_status) AS source,
                   jsonb_build_object(
                       'corvetra_run_id', r.corvetra_run_id, 'status', r.run_status,
                       'stage', r.stage_name, 'started_at', r.started_at,
                       'completed_at', r.completed_at,
                       'duration_seconds', CASE WHEN r.completed_at IS NULL THEN NULL ELSE
                           EXTRACT(EPOCH FROM r.completed_at-r.started_at)::double precision END,
                       'platform_code', r.platform_code, 'vendor_code', r.vendor_code,
                       'rule_code', r.rule_code) AS run,
                   evidence.evidence_count, evidence.latest_event_key
            FROM metadata.operational_alerts a
            JOIN metadata.pipeline_runs r ON r.pipeline_run_id = a.pipeline_run_id
            JOIN pipeline_state ps ON ps.pipeline_id = r.pipeline_id
            LEFT JOIN LATERAL (
                SELECT COUNT(*)::int AS evidence_count,
                       (array_agg(te.event_key ORDER BY te.occurred_at DESC,
                                  te.technical_event_id DESC))[1] AS latest_event_key
                FROM metadata.technical_events te
                WHERE te.pipeline_run_id = a.pipeline_run_id
            ) evidence ON TRUE
            WHERE a.alert_status IN ('OPEN', 'ACKNOWLEDGED')
              AND r.corvetra_run_id IS NOT NULL AND {where}
        """
        return await self._fetchall(query, parameters)

    async def get_latest_failed_validations(self, filters: AggregationFilters) -> list[dict[str, Any]]:
        where, parameters = self._pipeline_scope(filters)
        query = f"""
            {PIPELINE_STATE_CTE}
            SELECT x.validation_execution_id, x.pipeline_run_id,
                   c.check_key, c.check_name AS name, c.check_type AS type,
                   x.result_status AS result, x.effective_severity AS severity,
                   x.platform_code, x.rule_code, x.vendor_code,
                   x.actual_value AS actual, x.expected_value AS expected,
                   x.result_message AS message, x.evaluated_at,
                   jsonb_build_object('environment_key', ps.environment_key,
                                      'name', ps.environment_name) AS environment,
                   jsonb_build_object('pipeline_key', ps.pipeline_key,
                                      'name', ps.pipeline_name,
                                      'operational_status', ps.operational_status) AS pipeline,
                   jsonb_build_object('source_key', ps.source_key,
                                      'name', ps.source_name,
                                      'source_type', ps.source_type,
                                      'operational_status', ps.source_status) AS source,
                   jsonb_build_object(
                       'corvetra_run_id', r.corvetra_run_id, 'status', r.run_status,
                       'stage', r.stage_name, 'started_at', r.started_at,
                       'completed_at', r.completed_at,
                       'duration_seconds', CASE WHEN r.completed_at IS NULL THEN NULL ELSE
                           EXTRACT(EPOCH FROM r.completed_at-r.started_at)::double precision END,
                       'platform_code', r.platform_code, 'vendor_code', r.vendor_code,
                       'rule_code', r.rule_code) AS run,
                   represented.alert_key, evidence.evidence_count,
                   evidence.latest_event_key
            FROM pipeline_state ps
            JOIN metadata.pipeline_runs r ON r.pipeline_run_id = ps.latest_run_uuid
            JOIN metadata.validation_executions x ON x.pipeline_run_id = r.pipeline_run_id
            JOIN metadata.validation_checks c USING (validation_check_id)
            LEFT JOIN metadata.operational_alerts represented
              ON represented.validation_execution_id = x.validation_execution_id
             AND represented.alert_status IN ('OPEN', 'ACKNOWLEDGED')
            LEFT JOIN LATERAL (
                SELECT COUNT(*)::int AS evidence_count,
                       (array_agg(te.event_key ORDER BY te.occurred_at DESC,
                                  te.technical_event_id DESC))[1] AS latest_event_key
                FROM metadata.technical_events te
                WHERE te.validation_execution_id = x.validation_execution_id
            ) evidence ON TRUE
            WHERE x.result_status = 'FAILED' AND {where}
        """
        return await self._fetchall(query, parameters)

    async def get_runs(
        self, filters: AggregationFilters, *, started_from: datetime | None = None,
        started_to: datetime | None = None, failed_only: bool = False,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        scope, parameters = self._pipeline_scope(filters)
        conditions = [scope, "r.corvetra_run_id IS NOT NULL"]
        if started_from is not None:
            conditions.append("r.started_at >= %s")
            parameters.append(started_from)
        if started_to is not None:
            conditions.append("r.started_at < %s")
            parameters.append(started_to)
        if failed_only:
            conditions.append("r.run_status = 'FAILED'")
        limit_clause = " LIMIT %s" if limit is not None else ""
        if limit is not None:
            parameters.append(limit)
        query = f"""
            {PIPELINE_STATE_CTE}
            SELECT {RUN_SELECT}, r.pipeline_run_id
            FROM metadata.pipeline_runs r
            JOIN pipeline_state ps ON ps.pipeline_id = r.pipeline_id
            WHERE {' AND '.join(conditions)}
            ORDER BY r.started_at DESC, r.pipeline_run_id DESC{limit_clause}
        """
        return await self._fetchall(query, parameters)

    async def get_validation_history(
        self, filters: AggregationFilters, *, evaluated_from: datetime,
        evaluated_to: datetime,
    ) -> list[dict[str, Any]]:
        scope, parameters = self._pipeline_scope(filters)
        parameters.extend([evaluated_from, evaluated_to])
        query = f"""
            {PIPELINE_STATE_CTE}
            SELECT x.validation_execution_id, x.result_status,
                   x.effective_severity, x.evaluated_at,
                   c.check_key, c.check_name, c.validation_check_id,
                   ps.pipeline_key, ps.pipeline_name, ps.operational_status
            FROM metadata.validation_executions x
            JOIN metadata.validation_checks c USING (validation_check_id)
            JOIN metadata.pipeline_runs r USING (pipeline_run_id)
            JOIN pipeline_state ps ON ps.pipeline_id = r.pipeline_id
            WHERE r.corvetra_run_id IS NOT NULL AND {scope}
              AND x.evaluated_at >= %s AND x.evaluated_at < %s
            ORDER BY x.evaluated_at, x.validation_execution_id
        """
        return await self._fetchall(query, parameters)

    async def get_events(
        self, filters: AggregationFilters, *, occurred_from: datetime | None = None,
        occurred_to: datetime | None = None, limit: int | None = None,
    ) -> list[dict[str, Any]]:
        conditions: list[str] = []
        parameters: list[object] = []
        for expression, value in (
            ("e.environment_key = %s", filters.environment),
            ("p.pipeline_key = %s", filters.pipeline),
            ("s.source_key = %s", filters.source),
            ("te.occurred_at >= %s", occurred_from),
            ("te.occurred_at < %s", occurred_to),
        ):
            if value is not None:
                conditions.append(expression)
                parameters.append(value)
        limit_clause = " LIMIT %s" if limit is not None else ""
        if limit is not None:
            parameters.append(limit)
        query = f"""
            SELECT te.event_key, te.occurred_at, te.event_level AS level,
                   te.stage_name AS stage, te.platform_code, te.vendor_code,
                   te.rule_code, te.event_message AS message,
                   jsonb_build_object('environment_key', e.environment_key,
                                      'name', e.environment_name) AS environment,
                   CASE WHEN p.pipeline_id IS NULL THEN NULL ELSE jsonb_build_object(
                       'pipeline_key', p.pipeline_key, 'name', p.pipeline_name,
                       'operational_status', ps.operational_status) END AS pipeline,
                   CASE WHEN s.data_source_id IS NULL THEN NULL ELSE jsonb_build_object(
                       'source_key', s.source_key, 'name', s.source_name,
                       'source_type', s.source_type,
                       'operational_status', s.operational_status) END AS source,
                   CASE WHEN r.corvetra_run_id IS NULL THEN NULL ELSE jsonb_build_object(
                       'corvetra_run_id', r.corvetra_run_id, 'status', r.run_status,
                       'stage', r.stage_name, 'started_at', r.started_at,
                       'completed_at', r.completed_at,
                       'duration_seconds', CASE WHEN r.completed_at IS NULL THEN NULL ELSE
                           EXTRACT(EPOCH FROM r.completed_at-r.started_at)::double precision END,
                       'platform_code', r.platform_code, 'vendor_code', r.vendor_code,
                       'rule_code', r.rule_code) END AS run
            FROM metadata.technical_events te
            JOIN metadata.environments e ON e.environment_id = te.environment_id
            LEFT JOIN metadata.pipelines p ON p.pipeline_id = te.pipeline_id
            LEFT JOIN metadata.data_sources s ON s.data_source_id = te.data_source_id
            LEFT JOIN metadata.pipeline_runs r ON r.pipeline_run_id = te.pipeline_run_id
            LEFT JOIN ({PIPELINE_STATE_CTE} SELECT * FROM pipeline_state) ps
              ON ps.pipeline_id = p.pipeline_id
            WHERE {' AND '.join(conditions) if conditions else 'TRUE'}
            ORDER BY te.occurred_at DESC, te.technical_event_id DESC{limit_clause}
        """
        return await self._fetchall(query, parameters)

    async def _fetchall(self, query: str, parameters: list[object]) -> list[dict[str, Any]]:
        async with self._pool.connection() as connection:
            async with connection.cursor(row_factory=dict_row) as cursor:
                await cursor.execute(query, parameters)
                return await cursor.fetchall()
