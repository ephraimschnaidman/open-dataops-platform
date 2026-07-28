from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class IncidentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    incident_id: UUID
    pipeline_run_id: UUID
    incident_type: str
    severity: str
    table_schema: str
    table_name: str
    column_name: str | None
    expected_value: str | None
    observed_value: str | None
    incident_message: str
    incident_status: str
    detected_at: datetime
    resolved_at: datetime | None
    created_at: datetime
    updated_at: datetime


class IncidentContextResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    context_id: UUID
    incident_id: UUID
    context_version: str
    qualified_table: str
    evaluation_status: str
    severity: str
    expected_freshness_hours: Decimal | None
    observed_freshness_hours: Decimal | None
    recommended_action_code: str
    generated_at: datetime
    created_at: datetime
    updated_at: datetime
    change_type: str | None
    affected_column: str | None


class IncidentDetailResponse(IncidentResponse):
    incident_context: IncidentContextResponse | None


class PaginationMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    limit: int = Field(ge=1, le=100)
    offset: int = Field(ge=0)
    total: int = Field(ge=0)
    returned_count: int = Field(ge=0)


class IncidentListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[IncidentResponse]
    pagination: PaginationMetadata


class ApiErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    detail: str
