from __future__ import annotations

from abc import ABC, abstractmethod

from .models import (
    Dag, DagPage, DagRun, DagRunPage, TaskInstancePage, TaskLog,
    TriggerWorkflowRequest, WorkflowOperation,
)


class OrchestratorError(Exception):
    """Base class for safe, platform-neutral orchestration failures."""


class OrchestratorUnavailableError(OrchestratorError):
    pass


class OrchestratorAuthenticationError(OrchestratorError):
    pass


class OrchestratorPermissionError(OrchestratorError):
    pass


class OrchestratorNotFoundError(OrchestratorError):
    pass


class OrchestratorConflictError(OrchestratorError):
    pass


class OrchestratorInvalidResponseError(OrchestratorError):
    pass


class OrchestratorOperationUnsupportedError(OrchestratorError):
    pass


class OrchestratorClient(ABC):
    @abstractmethod
    async def trigger_workflow(
        self, *, dag_id: str, request: TriggerWorkflowRequest
    ) -> WorkflowOperation:
        raise NotImplementedError

    @abstractmethod
    async def list_dags(
        self, *, limit: int, offset: int, paused: bool | None = None,
        active: bool | None = None, tag: str | None = None
    ) -> DagPage:
        raise NotImplementedError

    @abstractmethod
    async def get_dag(self, dag_id: str) -> Dag:
        raise NotImplementedError

    @abstractmethod
    async def list_dag_runs(
        self,
        *,
        dag_id: str | None,
        limit: int,
        offset: int,
        start_date_gte: str | None = None,
        start_date_lte: str | None = None,
    ) -> DagRunPage:
        raise NotImplementedError

    @abstractmethod
    async def get_dag_run(self, *, dag_id: str, run_id: str) -> DagRun:
        raise NotImplementedError

    @abstractmethod
    async def list_task_instances(
        self, *, dag_id: str, run_id: str, limit: int, offset: int
    ) -> TaskInstancePage:
        raise NotImplementedError

    @abstractmethod
    async def get_task_log(
        self,
        *,
        dag_id: str,
        run_id: str,
        task_id: str,
        try_number: int,
        map_index: int,
    ) -> TaskLog:
        raise NotImplementedError
