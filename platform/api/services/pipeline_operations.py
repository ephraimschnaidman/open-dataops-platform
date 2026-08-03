from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from api.orchestrators.base import (
    OrchestratorClient, OrchestratorOperationUnsupportedError,
)
from api.orchestrators.models import (
    Dag, DagPage, DagRun, DagRunPage, TaskInstancePage, TaskLog,
    TriggerWorkflowRequest, WorkflowOperation,
)


class PipelineOperationsService:
    def __init__(self, orchestrator: OrchestratorClient) -> None:
        self._orchestrator = orchestrator

    async def trigger_workflow(
        self,
        *,
        dag_id: str,
        run_id: str | None,
        logical_date: datetime | None,
        conf: dict[str, Any] | None,
    ) -> WorkflowOperation:
        effective_run_id = run_id or self._generate_run_id()
        return await self._orchestrator.trigger_workflow(
            dag_id=dag_id,
            request=TriggerWorkflowRequest(
                run_id=effective_run_id,
                logical_date=logical_date,
                conf=conf,
            ),
        )

    async def retry_run(self, *, dag_id: str, run_id: str) -> WorkflowOperation:
        raise OrchestratorOperationUnsupportedError(
            "Retry is not supported by the configured orchestrator"
        )

    async def cancel_run(self, *, dag_id: str, run_id: str) -> WorkflowOperation:
        raise OrchestratorOperationUnsupportedError(
            "Cancellation is not supported by the configured orchestrator"
        )

    @staticmethod
    def _generate_run_id() -> str:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        return f"platform__manual__{timestamp}__{uuid4().hex}"

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
