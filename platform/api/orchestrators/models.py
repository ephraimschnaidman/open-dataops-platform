from __future__ import annotations

from datetime import datetime

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
    status: str = Field(min_length=1)
    logical_date: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class DagRunPage(OrchestratorModel):
    items: tuple[DagRun, ...]
    pagination: Pagination
