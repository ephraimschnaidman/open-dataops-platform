from __future__ import annotations

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from api.schemas.core_resources import (
    AlertSeverity, AlertStatus, DataSourceSummary, EnvironmentSummary,
    PaginationMetadata, PipelineSummary, RunSummary, TechnicalEvidenceSummary,
    ValidationExecutionSummary, ValidationResult, ValidationSeverity,
)


class ValidationExecutionReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    check_key: str
    name: str
    result: ValidationResult
    severity: ValidationSeverity
    evaluated_at: AwareDatetime


class AlertListItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    alert_key: str
    title: str
    severity: AlertSeverity
    status: AlertStatus
    platform_code: str
    vendor_code: str | None
    rule_code: str | None
    message: str
    detected_at: AwareDatetime
    last_seen_at: AwareDatetime
    acknowledged_at: AwareDatetime | None
    resolved_at: AwareDatetime | None
    pipeline: PipelineSummary
    run: RunSummary
    source: DataSourceSummary
    environment: EnvironmentSummary
    validation_execution: ValidationExecutionReference | None


class AlertDetail(AlertListItem):
    validation_execution: ValidationExecutionSummary | None
    technical_evidence_count: int = Field(ge=0)
    recent_technical_evidence: list[TechnicalEvidenceSummary]


class AlertListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[AlertListItem]
    pagination: PaginationMetadata
