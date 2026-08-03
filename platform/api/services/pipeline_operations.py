from __future__ import annotations

from api.orchestrators.base import OrchestratorClient
from api.orchestrators.models import Dag, DagPage, DagRunPage


class PipelineOperationsService:
    def __init__(self, orchestrator: OrchestratorClient) -> None:
        self._orchestrator = orchestrator

    async def list_dags(self, *, limit: int, offset: int) -> DagPage:
        return await self._orchestrator.list_dags(limit=limit, offset=offset)

    async def get_dag(self, dag_id: str) -> Dag:
        return await self._orchestrator.get_dag(dag_id)

    async def list_dag_runs(
        self,
        *,
        dag_id: str,
        limit: int,
        offset: int,
    ) -> DagRunPage:
        return await self._orchestrator.list_dag_runs(
            dag_id=dag_id,
            limit=limit,
            offset=offset,
        )
