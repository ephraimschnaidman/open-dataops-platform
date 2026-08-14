from __future__ import annotations

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from api.schemas.core_resources import (
    DataSourceOperationalStatus,
    EnvironmentSummary,
    PaginationMetadata,
    PipelineOperationalStatus,
    RunSummary,
    SourceType,
    TechnicalEvidenceSummary,
    ValidationSummary,
)


class DataSourceListItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_key: str
    name: str
    source_type: SourceType
    environment: EnvironmentSummary
    operational_status: DataSourceOperationalStatus
    connected_pipeline_count: int = Field(ge=0)
    last_observed_at: AwareDatetime | None


class ConnectedPipelineSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pipeline_key: str
    name: str
    is_enabled: bool
    operational_status: PipelineOperationalStatus
    latest_run: RunSummary | None


class DataSourceDetail(DataSourceListItem):
    connected_pipelines: list[ConnectedPipelineSummary]
    validation_summary: ValidationSummary
    active_alert_count: int = Field(ge=0)
    recent_evidence: list[TechnicalEvidenceSummary]


class DataSourceListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[DataSourceListItem]
    pagination: PaginationMetadata
