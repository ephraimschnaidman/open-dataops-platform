import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "platform"))

from api.orchestrators.base import OrchestratorClient  # noqa: E402
from api.orchestrators.models import (  # noqa: E402
    Dag,
    DagPage,
    DagRunPage,
    Pagination,
)
from api.services.pipeline_operations import PipelineOperationsService  # noqa: E402


class StubOrchestratorClient(OrchestratorClient):
    def __init__(self):
        self.call = None
        self.dag = Dag(
            dag_id="daily_sales", is_active=True, is_paused=False
        )

    async def list_dags(self, *, limit, offset):
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

    async def list_dag_runs(self, *, dag_id, limit, offset):
        self.call = ("list_dag_runs", dag_id, limit, offset)
        return DagRunPage(
            items=(),
            pagination=Pagination(
                limit=limit, offset=offset, total=0, returned_count=0
            ),
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


if __name__ == "__main__":
    unittest.main()
