from __future__ import annotations

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from api.schemas.core_resources import (
    AlertSummary,
    DataSourceSummary,
    EnvironmentSummary,
    PaginationMetadata,
    PipelineSummary,
    RunStatus,
    StageName,
    TechnicalEvidenceSummary,
    ValidationResult,
    ValidationSeverity,
    ValidationCheckType,
    ValidationSummary,
)


class PipelineRunListItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    corvetra_run_id: str
    pipeline: PipelineSummary
    source: DataSourceSummary
    environment: EnvironmentSummary
    status: RunStatus
    stage: StageName | None
    started_at: AwareDatetime
    completed_at: AwareDatetime | None
    duration_seconds: float | None = Field(ge=0)
    platform_code: str | None
    vendor_code: str | None
    rule_code: str | None
    active_alert_count: int = Field(ge=0)


class AirflowIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dag_id: str
    airflow_run_id: str


class ValidationExecutionSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    check_key: str
    name: str
    type: ValidationCheckType
    dataset_name: str
    column_name: str | None
    result: ValidationResult
    severity: ValidationSeverity
    platform_code: str
    rule_code: str | None
    vendor_code: str | None
    actual: str | None
    expected: str | None
    message: str
    evaluated_at: AwareDatetime


class PipelineRunDetail(PipelineRunListItem):
    airflow: AirflowIdentity
    alerts: list[AlertSummary]
    validation_summary: ValidationSummary
    validation_executions: list[ValidationExecutionSummary]
    technical_evidence_count: int = Field(ge=0)
    technical_evidence: list[TechnicalEvidenceSummary]


class PipelineRunListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[PipelineRunListItem]
    pagination: PaginationMetadata
