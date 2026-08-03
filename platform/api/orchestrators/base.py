from __future__ import annotations

from abc import ABC, abstractmethod

from .models import Dag, DagPage, DagRunPage


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
    async def list_dags(self, *, limit: int, offset: int) -> DagPage:
        raise NotImplementedError

    @abstractmethod
    async def get_dag(self, dag_id: str) -> Dag:
        raise NotImplementedError

    @abstractmethod
    async def list_dag_runs(
        self,
        *,
        dag_id: str,
        limit: int,
        offset: int,
    ) -> DagRunPage:
        raise NotImplementedError
