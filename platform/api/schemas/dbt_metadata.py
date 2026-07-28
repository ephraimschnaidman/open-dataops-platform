from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DbtMetadataResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    result_id: UUID
    pipeline_run_id: UUID
    invocation_id: str
    command_type: str
    node_unique_id: str
    node_name: str
    resource_type: str
    execution_status: str
    execution_time_seconds: float
    message: str | None
    recorded_at: datetime


class DbtMetadataPaginationMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    limit: int = Field(ge=1, le=100)
    offset: int = Field(ge=0)
    total: int = Field(ge=0)
    returned_count: int = Field(ge=0)


class DbtMetadataListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[DbtMetadataResponse]
    pagination: DbtMetadataPaginationMetadata


class DbtMetadataErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    detail: str
