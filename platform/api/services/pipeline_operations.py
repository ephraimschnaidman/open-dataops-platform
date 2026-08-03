from __future__ import annotations

from api.orchestrators.base import OrchestratorClient
from api.orchestrators.models import Dag, DagPage, DagRun, DagRunPage, TaskInstancePage, TaskLog


class PipelineOperationsService:
    def __init__(self, orchestrator: OrchestratorClient) -> None:
        self._orchestrator = orchestrator

    async def list_dags(
        self, *, limit: int, offset: int, paused: bool | None = None,
        active: bool | None = None, tag: str | None = None
    ) -> DagPage:
        return await self._orchestrator.list_dags(
            limit=limit, offset=offset, paused=paused, active=active, tag=tag
        )

    async def get_dag(self, dag_id: str) -> Dag:
        return await self._orchestrator.get_dag(dag_id)

    async def list_dag_runs(
        self,
        *,
        dag_id: str | None,
        limit: int,
        offset: int,
        start_date_gte: str | None = None,
        start_date_lte: str | None = None,
    ) -> DagRunPage:
        return await self._orchestrator.list_dag_runs(
            dag_id=dag_id,
            limit=limit,
            offset=offset,
            start_date_gte=start_date_gte,
            start_date_lte=start_date_lte,
        )

    async def get_dag_run(self, *, dag_id: str, run_id: str) -> DagRun:
        return await self._orchestrator.get_dag_run(dag_id=dag_id, run_id=run_id)

    async def list_task_instances(
        self, *, dag_id: str, run_id: str, limit: int, offset: int
    ) -> TaskInstancePage:
        return await self._orchestrator.list_task_instances(
            dag_id=dag_id, run_id=run_id, limit=limit, offset=offset
        )

    async def get_task_log(
        self, *, dag_id: str, run_id: str, task_id: str, try_number: int, map_index: int
    ) -> TaskLog:
        return await self._orchestrator.get_task_log(
            dag_id=dag_id,
            run_id=run_id,
            task_id=task_id,
            try_number=try_number,
            map_index=map_index,
        )
