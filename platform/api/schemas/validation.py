from __future__ import annotations

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from api.schemas.core_resources import (
    AlertSummary, DataSourceSummary, EnvironmentSummary, PaginationMetadata,
    PipelineSummary, RunSummary, StageName, TechnicalEvidenceSummary,
    ValidationExecutionSummary, ValidationResult, ValidationSeverity,
)


class ValidationListItem(ValidationExecutionSummary):
    stage: StageName
    run: RunSummary
    pipeline: PipelineSummary
    source: DataSourceSummary
    environment: EnvironmentSummary


class ValidationExecutionHistoryItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    corvetra_run_id: str
    result: ValidationResult
    severity: ValidationSeverity
    actual: str | None
    expected: str | None
    platform_code: str
    vendor_code: str | None
    rule_code: str | None
    evaluated_at: AwareDatetime


class ValidationExecutionDetail(ValidationListItem):
    related_alerts: list[AlertSummary]
    technical_evidence_count: int = Field(ge=0)
    technical_evidence: list[TechnicalEvidenceSummary]
    recent_executions: list[ValidationExecutionHistoryItem]


class ValidationListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[ValidationListItem]
    pagination: PaginationMetadata
