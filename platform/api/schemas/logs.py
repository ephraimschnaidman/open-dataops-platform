from __future__ import annotations

from typing import Any

from pydantic import AwareDatetime, BaseModel, ConfigDict

from api.schemas.alerts import ValidationExecutionReference
from api.schemas.core_resources import (
    AlertStatus, AlertSummary, DataSourceSummary, EnvironmentSummary, EventLevel,
    PaginationMetadata, PipelineSummary, RunSummary, StageName,
    ValidationExecutionSummary,
)


class RelatedAlertReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    alert_key: str
    status: AlertStatus


class LogEventListItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_key: str
    occurred_at: AwareDatetime
    level: EventLevel
    message: str
    environment: EnvironmentSummary
    pipeline: PipelineSummary | None
    run: RunSummary | None
    source: DataSourceSummary | None
    stage: StageName | None
    platform_code: str | None
    vendor_code: str | None
    rule_code: str | None
    related_alert: RelatedAlertReference | None
    related_validation: ValidationExecutionReference | None


class LogEventDetail(LogEventListItem):
    details: dict[str, Any]
    interpretation: str | None
    stack_trace: str | None
    alert: AlertSummary | None
    validation_execution: ValidationExecutionSummary | None


class LogEventListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[LogEventListItem]
    pagination: PaginationMetadata
