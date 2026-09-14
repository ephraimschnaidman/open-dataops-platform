from __future__ import annotations

from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


Percentage = Annotated[Decimal, Field(ge=0, le=100, max_digits=5, decimal_places=2)]
EmailAddress = Annotated[
    str,
    Field(
        min_length=3,
        max_length=254,
        pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$",
    ),
]


class NotificationSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool
    recipients: list[EmailAddress] = Field(max_length=100)
    severity: Literal["CRITICAL_ONLY", "CRITICAL_AND_WARNING"]
    notify_resolved: bool

    @model_validator(mode="after")
    def require_recipient_when_enabled(self) -> "NotificationSettings":
        if self.enabled and not self.recipients:
            raise ValueError("At least one recipient is required when email notifications are enabled")
        return self


class HealthThreshold(BaseModel):
    model_config = ConfigDict(extra="forbid")

    healthy: Percentage
    warning: Percentage

    @model_validator(mode="after")
    def healthy_must_exceed_warning(self) -> "HealthThreshold":
        if self.healthy <= self.warning:
            raise ValueError("Healthy threshold must be higher than warning threshold")
        return self


class OperationalDefaults(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pipeline: HealthThreshold
    schedule: HealthThreshold
    source: HealthThreshold
    runtime_warning: Percentage
    freshness_hours: Decimal = Field(gt=0, le=8760, max_digits=7, decimal_places=2)
    validation_severity: Literal["WARNING", "BLOCKING"]
    blocking_alerts: bool
    warning_alerts: bool


class GeneralSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspace_name: str = Field(min_length=1, max_length=100)
    workspace_id: str
    default_environment: str
    timezone: str
    date_time_display: Literal["LOCAL_WORKSPACE_TIME"]


class GeneralSettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workspace_name: str = Field(min_length=1, max_length=100)
    default_environment: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    timezone: Literal[
        "America/New_York", "America/Chicago", "America/Los_Angeles", "UTC"
    ]


class EnvironmentSetting(BaseModel):
    model_config = ConfigDict(extra="forbid")

    environment_key: str
    name: str
    description: str | None
    status: Literal["ACTIVE"]
    resources: int = Field(ge=0)
    pipelines: int = Field(ge=0)
    sources: int = Field(ge=0)
    other: int = Field(ge=0)
    created_at: str
    is_default: bool


class EnvironmentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    environment_key: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=63)
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)


class SettingsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    general: GeneralSettings
    environments: list[EnvironmentSetting]
    notifications: NotificationSettings
    operational_defaults: OperationalDefaults


class SettingsErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    detail: str
    code: str
