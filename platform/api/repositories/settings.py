from __future__ import annotations

from typing import Any

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool


class SettingsRepository:
    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool

    async def get_settings(self) -> dict[str, Any]:
        settings_query = """
            SELECT w.workspace_name, w.workspace_key AS workspace_id,
                   e.environment_key AS default_environment, w.timezone,
                   w.notification_enabled, w.notification_recipients,
                   w.notification_severity, w.notify_resolved,
                   w.pipeline_healthy, w.pipeline_warning,
                   w.schedule_healthy, w.schedule_warning,
                   w.source_healthy, w.source_warning,
                   w.runtime_warning, w.freshness_hours,
                   w.validation_severity, w.blocking_alerts, w.warning_alerts
            FROM metadata.workspace_settings w
            JOIN metadata.environments e
              ON e.environment_id = w.default_environment_id
            WHERE w.workspace_key = 'workspace_01J4X8K97B'
        """
        environments_query = """
            SELECT e.environment_key, e.environment_name AS name, e.description,
                   'ACTIVE' AS status, e.created_at,
                   (e.environment_id = w.default_environment_id) AS is_default,
                   COUNT(DISTINCT p.pipeline_id)::int AS pipelines,
                   COUNT(DISTINCT s.data_source_id)::int AS sources,
                   COUNT(DISTINCT v.validation_check_id)::int AS other
            FROM metadata.environments e
            CROSS JOIN metadata.workspace_settings w
            LEFT JOIN metadata.data_sources s ON s.environment_id = e.environment_id
            LEFT JOIN metadata.pipelines p ON p.environment_id = e.environment_id
            LEFT JOIN metadata.validation_checks v ON v.pipeline_id = p.pipeline_id
            WHERE w.workspace_key = 'workspace_01J4X8K97B'
            GROUP BY e.environment_id, w.default_environment_id
            ORDER BY e.created_at, e.environment_key
        """
        async with self._pool.connection() as connection:
            async with connection.cursor(row_factory=dict_row) as cursor:
                await cursor.execute(settings_query)
                settings = await cursor.fetchone()
                await cursor.execute(environments_query)
                environments = await cursor.fetchall()
        if settings is None:
            raise RuntimeError("Workspace settings row is missing")
        return {**settings, "environments": environments}

    async def update_notifications(self, values: dict[str, Any]) -> None:
        async with self._pool.connection() as connection:
            result = await connection.execute(
                """
                UPDATE metadata.workspace_settings
                SET notification_enabled = %s, notification_recipients = %s,
                    notification_severity = %s, notify_resolved = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE workspace_key = 'workspace_01J4X8K97B'
                RETURNING workspace_key
                """,
                (values["enabled"], values["recipients"], values["severity"], values["notify_resolved"]),
            )
            if await result.fetchone() is None:
                raise RuntimeError("Workspace settings row is missing")

    async def update_operational_defaults(self, values: dict[str, Any]) -> None:
        async with self._pool.connection() as connection:
            result = await connection.execute(
                """
                UPDATE metadata.workspace_settings SET
                    pipeline_healthy = %s, pipeline_warning = %s,
                    schedule_healthy = %s, schedule_warning = %s,
                    source_healthy = %s, source_warning = %s,
                    runtime_warning = %s, freshness_hours = %s,
                    validation_severity = %s, blocking_alerts = %s,
                    warning_alerts = %s, updated_at = CURRENT_TIMESTAMP
                WHERE workspace_key = 'workspace_01J4X8K97B'
                RETURNING workspace_key
                """,
                (
                    values["pipeline"]["healthy"], values["pipeline"]["warning"],
                    values["schedule"]["healthy"], values["schedule"]["warning"],
                    values["source"]["healthy"], values["source"]["warning"],
                    values["runtime_warning"], values["freshness_hours"],
                    values["validation_severity"], values["blocking_alerts"], values["warning_alerts"],
                ),
            )
            if await result.fetchone() is None:
                raise RuntimeError("Workspace settings row is missing")

    async def update_general(self, values: dict[str, Any]) -> bool:
        query = """
            UPDATE metadata.workspace_settings w
            SET workspace_name = %s, default_environment_id = e.environment_id,
                timezone = %s, updated_at = CURRENT_TIMESTAMP
            FROM metadata.environments e
            WHERE w.workspace_key = 'workspace_01J4X8K97B'
              AND e.environment_key = %s
            RETURNING w.workspace_key
        """
        async with self._pool.connection() as connection:
            result = await connection.execute(
                query, (values["workspace_name"], values["timezone"], values["default_environment"])
            )
            return await result.fetchone() is not None

    async def create_environment(self, values: dict[str, Any]) -> None:
        async with self._pool.connection() as connection:
            await connection.execute(
                """
                INSERT INTO metadata.environments
                    (environment_id, environment_key, environment_name, description)
                VALUES (gen_random_uuid(), %s, %s, %s)
                """,
                (values["environment_key"], values["name"], values["description"]),
            )

    async def delete_environment(self, environment_key: str) -> str:
        async with self._pool.connection() as connection:
            async with connection.transaction():
                row = await (
                    await connection.execute(
                        """
                        SELECT e.environment_id,
                               e.environment_id = w.default_environment_id AS is_default,
                               (SELECT COUNT(*) FROM metadata.data_sources s
                                WHERE s.environment_id = e.environment_id)
                               + (SELECT COUNT(*) FROM metadata.pipelines p
                                  WHERE p.environment_id = e.environment_id)
                               + (SELECT COUNT(*) FROM metadata.technical_events t
                                  WHERE t.environment_id = e.environment_id) AS resources
                        FROM metadata.environments e
                        CROSS JOIN metadata.workspace_settings w
                        WHERE e.environment_key = %s
                          AND w.workspace_key = 'workspace_01J4X8K97B'
                        FOR UPDATE OF e, w
                        """,
                        (environment_key,),
                    )
                ).fetchone()
                if row is None:
                    return "NOT_FOUND"
                if row[1]:
                    return "DEFAULT"
                if row[2] > 0:
                    return "IN_USE"
                await connection.execute(
                    "DELETE FROM metadata.environments WHERE environment_id = %s", (row[0],)
                )
                return "DELETED"
