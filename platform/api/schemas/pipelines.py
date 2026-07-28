from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PipelineResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pipeline_run_id: UUID
    dag_id: str
    airflow_run_id: str
    started_at: datetime
    completed_at: datetime | None
    run_status: str
    created_at: datetime


class PipelinePaginationMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    limit: int = Field(ge=1, le=100)
    offset: int = Field(ge=0)
    total: int = Field(ge=0)
    returned_count: int = Field(ge=0)


class PipelineListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[PipelineResponse]
    pagination: PipelinePaginationMetadata


class PipelineErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    detail: str
