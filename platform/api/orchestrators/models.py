from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class OrchestratorModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Pagination(OrchestratorModel):
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)
    total: int = Field(ge=0)
    returned_count: int = Field(ge=0)


class Dag(OrchestratorModel):
    dag_id: str = Field(min_length=1)
    display_name: str | None = None
    description: str | None = None
    is_active: bool
    is_paused: bool
    owners: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()


class DagPage(OrchestratorModel):
    items: tuple[Dag, ...]
    pagination: Pagination


class DagRun(OrchestratorModel):
    dag_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    state: str = Field(min_length=1)
    logical_date: datetime | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    data_interval_start: datetime | None = None
    data_interval_end: datetime | None = None
    run_type: str | None = None
    externally_triggered: bool | None = None


class TriggerWorkflowRequest(OrchestratorModel):
    run_id: str = Field(min_length=1, max_length=250)
    logical_date: datetime | None = None
    conf: dict[str, Any] | None = None


class WorkflowOperation(OrchestratorModel):
    operation_id: str = Field(min_length=1)
    dag_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    state: str = Field(min_length=1)
    logical_date: datetime | None = None
    start_date: datetime | None = None
    externally_triggered: bool | None = None


class DagRunPage(OrchestratorModel):
    items: tuple[DagRun, ...]
    pagination: Pagination


class TaskInstance(OrchestratorModel):
    dag_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    task_id: str = Field(min_length=1)
    state: str | None = None
    try_number: int = Field(ge=0)
    map_index: int = Field(ge=-1)
    start_date: datetime | None = None
    end_date: datetime | None = None
    duration: float | None = Field(default=None, ge=0)
    operator: str | None = None
    queued_when: datetime | None = None


class TaskInstancePage(OrchestratorModel):
    items: tuple[TaskInstance, ...]
    pagination: Pagination


class TaskLog(OrchestratorModel):
    dag_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    task_id: str = Field(min_length=1)
    try_number: int = Field(ge=1)
    map_index: int = Field(ge=-1)
    content: str
