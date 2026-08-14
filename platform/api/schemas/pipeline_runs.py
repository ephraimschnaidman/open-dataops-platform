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
    ValidationExecutionSummary,
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
