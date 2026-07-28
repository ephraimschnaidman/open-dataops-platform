from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MetricResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metric_id: UUID
    pipeline_run_id: UUID
    table_schema: str
    table_name: str
    row_count: int = Field(ge=0)
    freshness_column: str | None
    max_freshness_value: datetime | None
    measured_at: datetime
    created_at: datetime


class MetricPaginationMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    limit: int = Field(ge=1, le=100)
    offset: int = Field(ge=0)
    total: int = Field(ge=0)
    returned_count: int = Field(ge=0)


class MetricListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[MetricResponse]
    pagination: MetricPaginationMetadata


class MetricErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    detail: str
