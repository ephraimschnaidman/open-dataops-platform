import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "platform"))

from api.orchestrators.base import OrchestratorClient  # noqa: E402
from api.orchestrators.models import (  # noqa: E402
    Dag,
    DagPage,
    DagRun, DagRunPage, TaskInstancePage, TaskLog,
    Pagination, WorkflowOperation,
)
from api.services.pipeline_operations import PipelineOperationsService  # noqa: E402


class StubOrchestratorClient(OrchestratorClient):
    def __init__(self):
        self.call = None
        self.dag = Dag(
            dag_id="daily_sales", is_active=True, is_paused=False
        )

    async def trigger_workflow(self, *, dag_id, request):
        self.call = ("trigger_workflow", dag_id, request)
        return WorkflowOperation(
            operation_id=request.run_id,
            dag_id=dag_id,
            run_id=request.run_id,
            state="queued",
            logical_date=request.logical_date,
            externally_triggered=True,
        )

    async def list_dags(self, *, limit, offset, paused=None, active=None, tag=None):
        self.call = ("list_dags", limit, offset)
        return DagPage(
            items=(self.dag,),
            pagination=Pagination(
                limit=limit, offset=offset, total=1, returned_count=1
            ),
        )

    async def get_dag(self, dag_id):
        self.call = ("get_dag", dag_id)
        return self.dag

    async def list_dag_runs(
        self, *, dag_id, limit, offset, start_date_gte=None, start_date_lte=None
    ):
        self.call = ("list_dag_runs", dag_id, limit, offset)
        return DagRunPage(
            items=(),
            pagination=Pagination(
                limit=limit, offset=offset, total=0, returned_count=0
            ),
        )

    async def get_dag_run(self, *, dag_id, run_id):
        self.call = ("get_dag_run", dag_id, run_id)
        return DagRun(dag_id=dag_id, run_id=run_id, state="success")

    async def list_task_instances(self, *, dag_id, run_id, limit, offset):
        self.call = ("list_task_instances", dag_id, run_id, limit, offset)
        return TaskInstancePage(
            items=(), pagination=Pagination(
                limit=limit, offset=offset, total=0, returned_count=0
            )
        )

    async def get_task_log(
        self, *, dag_id, run_id, task_id, try_number, map_index
    ):
        self.call = ("get_task_log", dag_id, run_id, task_id, try_number, map_index)
        return TaskLog(
            dag_id=dag_id, run_id=run_id, task_id=task_id,
            try_number=try_number, map_index=map_index, content="ok"
        )


class PipelineOperationsServiceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.orchestrator = StubOrchestratorClient()
        self.service = PipelineOperationsService(self.orchestrator)

    async def test_list_dags_delegates_to_orchestrator_abstraction(self):
        result = await self.service.list_dags(limit=10, offset=5)
        self.assertEqual(self.orchestrator.call, ("list_dags", 10, 5))
        self.assertEqual(result.items[0].dag_id, "daily_sales")

    async def test_get_dag_delegates_to_orchestrator_abstraction(self):
        result = await self.service.get_dag("daily_sales")
        self.assertEqual(self.orchestrator.call, ("get_dag", "daily_sales"))
        self.assertEqual(result, self.orchestrator.dag)

    async def test_list_dag_runs_delegates_to_orchestrator_abstraction(self):
        await self.service.list_dag_runs(
            dag_id="daily_sales", limit=25, offset=50
        )
        self.assertEqual(
            self.orchestrator.call,
            ("list_dag_runs", "daily_sales", 25, 50),
        )

    async def test_phase_three_methods_delegate(self):
        await self.service.get_dag_run(dag_id="dag", run_id="run")
        self.assertEqual(self.orchestrator.call, ("get_dag_run", "dag", "run"))
        await self.service.list_task_instances(
            dag_id="dag", run_id="run", limit=20, offset=5
        )
        self.assertEqual(
            self.orchestrator.call, ("list_task_instances", "dag", "run", 20, 5)
        )
        await self.service.get_task_log(
            dag_id="dag", run_id="run", task_id="task", try_number=2, map_index=-1
        )
        self.assertEqual(
            self.orchestrator.call,
            ("get_task_log", "dag", "run", "task", 2, -1),
        )

    async def test_trigger_preserves_caller_run_id_and_neutral_request(self):
        result = await self.service.trigger_workflow(
            dag_id="daily_sales",
            run_id="caller-run",
            logical_date=None,
            conf={"region": "us"},
        )
        operation, dag_id, request = self.orchestrator.call
        self.assertEqual((operation, dag_id), ("trigger_workflow", "daily_sales"))
        self.assertEqual(request.run_id, "caller-run")
        self.assertEqual(request.conf, {"region": "us"})
        self.assertEqual(result.operation_id, "caller-run")

    async def test_trigger_generates_clear_platform_run_id(self):
        await self.service.trigger_workflow(
            dag_id="daily_sales", run_id=None, logical_date=None, conf=None
        )
        generated = self.orchestrator.call[2].run_id
        self.assertRegex(
            generated,
            r"^platform__manual__\d{8}T\d{12}Z__[0-9a-f]{32}$",
        )

    async def test_retry_and_cancel_are_capability_driven_unsupported(self):
        from api.orchestrators.base import OrchestratorOperationUnsupportedError

        with self.assertRaises(OrchestratorOperationUnsupportedError):
            await self.service.retry_run(dag_id="daily_sales", run_id="run")
        with self.assertRaises(OrchestratorOperationUnsupportedError):
            await self.service.cancel_run(dag_id="daily_sales", run_id="run")


if __name__ == "__main__":
    unittest.main()
