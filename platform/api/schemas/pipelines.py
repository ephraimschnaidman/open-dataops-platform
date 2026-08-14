from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from api.schemas.core_resources import (
    ApiErrorResponse,
    AlertSummary,
    DataSourceSummary,
    EnvironmentSummary,
    PaginationMetadata,
    PipelineOperationalStatus,
    RunSummary,
    ValidationSummary,
)


class PipelineListItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pipeline_key: str
    name: str
    environment: EnvironmentSummary
    source: DataSourceSummary
    is_enabled: bool
    operational_status: PipelineOperationalStatus
    latest_run: RunSummary | None
    current_issue: AlertSummary | None


class PipelineDetail(PipelineListItem):
    airflow_dag_id: str
    recent_runs: list[RunSummary]
    validation_summary: ValidationSummary
    active_alerts: list[AlertSummary]
    technical_evidence_count: int


class PipelineListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[PipelineListItem]
    pagination: PaginationMetadata


PipelinePaginationMetadata = PaginationMetadata
PipelineErrorResponse = ApiErrorResponse
