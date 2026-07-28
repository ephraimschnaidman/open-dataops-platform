from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SchemaSnapshotResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    snapshot_id: UUID
    pipeline_run_id: UUID
    table_schema: str
    table_name: str
    column_name: str
    ordinal_position: int = Field(gt=0)
    data_type: str
    is_nullable: bool
    measured_at: datetime
    created_at: datetime


class SchemaSnapshotPaginationMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    limit: int = Field(ge=1, le=500)
    offset: int = Field(ge=0)
    total: int = Field(ge=0)
    returned_count: int = Field(ge=0)


class SchemaSnapshotListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[SchemaSnapshotResponse]
    pagination: SchemaSnapshotPaginationMetadata


class SchemaSnapshotErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    detail: str
