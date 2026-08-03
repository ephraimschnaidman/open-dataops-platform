from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class OperationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class PaginationResponse(OperationResponse):
    limit: int = Field(ge=1, le=100)
    offset: int = Field(ge=0)
    total: int = Field(ge=0)
    returned_count: int = Field(ge=0)


class DagResponse(OperationResponse):
    dag_id: str
    display_name: str | None
    description: str | None
    is_paused: bool
    is_active: bool
    owners: tuple[str, ...]
    tags: tuple[str, ...]


class DagListResponse(OperationResponse):
    items: tuple[DagResponse, ...]
    pagination: PaginationResponse


class DagRunResponse(OperationResponse):
    dag_id: str
    run_id: str
    state: str
    logical_date: datetime | None
    start_date: datetime | None
    end_date: datetime | None
    data_interval_start: datetime | None
    data_interval_end: datetime | None
    run_type: str | None
    externally_triggered: bool | None


class DagRunListResponse(OperationResponse):
    items: tuple[DagRunResponse, ...]
    pagination: PaginationResponse


class TriggerDagRequest(OperationResponse):
    run_id: str | None = Field(default=None, min_length=1, max_length=250)
    logical_date: datetime | None = None
    conf: dict[str, Any] | None = None


class WorkflowOperationResponse(OperationResponse):
    operation_id: str
    dag_id: str
    run_id: str
    state: str
    logical_date: datetime | None
    start_date: datetime | None
    externally_triggered: bool | None


class TaskInstanceResponse(OperationResponse):
    dag_id: str
    run_id: str
    task_id: str
    state: str | None
    try_number: int
    map_index: int
    start_date: datetime | None
    end_date: datetime | None
    duration: float | None
    operator: str | None
    queued_when: datetime | None


class TaskInstanceListResponse(OperationResponse):
    items: tuple[TaskInstanceResponse, ...]
    pagination: PaginationResponse


class TaskLogResponse(OperationResponse):
    dag_id: str
    run_id: str
    task_id: str
    try_number: int
    map_index: int
    content: str


class OperationsErrorResponse(OperationResponse):
    detail: str
