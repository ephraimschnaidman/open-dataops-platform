from __future__ import annotations

from api.repositories.settings import SettingsRepository
from api.schemas.settings import (
    EnvironmentCreate, GeneralSettingsUpdate, NotificationSettings,
    OperationalDefaults, SettingsResponse,
)


class EnvironmentNotFoundError(LookupError):
    pass


class DefaultEnvironmentRequiredError(RuntimeError):
    pass


class EnvironmentInUseError(RuntimeError):
    pass


class SettingsService:
    def __init__(self, repository: SettingsRepository) -> None:
        self._repository = repository

    async def get_settings(self) -> SettingsResponse:
        row = await self._repository.get_settings()
        environments = []
        for environment in row.pop("environments"):
            environment["resources"] = environment["pipelines"] + environment["sources"] + environment["other"]
            environment["created_at"] = environment["created_at"].date().isoformat()
            environments.append(environment)
        return SettingsResponse.model_validate({
            "general": {
                "workspace_name": row["workspace_name"], "workspace_id": row["workspace_id"],
                "default_environment": row["default_environment"], "timezone": row["timezone"],
                "date_time_display": "LOCAL_WORKSPACE_TIME",
            },
            "environments": environments,
            "notifications": {
                "enabled": row["notification_enabled"], "recipients": row["notification_recipients"],
                "severity": row["notification_severity"], "notify_resolved": row["notify_resolved"],
            },
            "operational_defaults": {
                "pipeline": {"healthy": row["pipeline_healthy"], "warning": row["pipeline_warning"]},
                "schedule": {"healthy": row["schedule_healthy"], "warning": row["schedule_warning"]},
                "source": {"healthy": row["source_healthy"], "warning": row["source_warning"]},
                "runtime_warning": row["runtime_warning"], "freshness_hours": row["freshness_hours"],
                "validation_severity": row["validation_severity"], "blocking_alerts": row["blocking_alerts"],
                "warning_alerts": row["warning_alerts"],
            },
        })

    async def update_notifications(self, settings: NotificationSettings) -> NotificationSettings:
        await self._repository.update_notifications(settings.model_dump(mode="json"))
        return settings

    async def update_operational_defaults(self, settings: OperationalDefaults) -> OperationalDefaults:
        await self._repository.update_operational_defaults(settings.model_dump(mode="python"))
        return settings

    async def update_general(self, settings: GeneralSettingsUpdate) -> SettingsResponse:
        if not await self._repository.update_general(settings.model_dump()):
            raise EnvironmentNotFoundError
        return await self.get_settings()

    async def create_environment(self, environment: EnvironmentCreate) -> SettingsResponse:
        await self._repository.create_environment(environment.model_dump())
        return await self.get_settings()

    async def delete_environment(self, environment_key: str) -> None:
        outcome = await self._repository.delete_environment(environment_key)
        if outcome == "NOT_FOUND":
            raise EnvironmentNotFoundError
        if outcome == "DEFAULT":
            raise DefaultEnvironmentRequiredError
        if outcome == "IN_USE":
            raise EnvironmentInUseError
