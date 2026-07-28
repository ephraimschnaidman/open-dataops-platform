import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from fastapi.testclient import TestClient
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "platform"))

from api.main import app  # noqa: E402
from api.repositories.pipelines import PipelineFilters, PipelineRepository  # noqa: E402
from api.routes.pipelines import get_pipeline_service  # noqa: E402
from api.schemas.pipelines import (  # noqa: E402
    PipelineListResponse,
    PipelinePaginationMetadata,
    PipelineResponse,
)
from api.services.pipelines import PipelineService  # noqa: E402

PIPELINE_RUN_ID = UUID("22222222-2222-4222-8222-222222222222")
NOW = datetime(2026, 7, 28, 12, 0, tzinfo=timezone.utc)


def pipeline_data(**overrides):
    values = {
        "pipeline_run_id": PIPELINE_RUN_ID,
        "dag_id": "ecommerce_pipeline",
        "airflow_run_id": "scheduled__2026-07-28T12:00:00+00:00",
        "started_at": NOW,
        "completed_at": NOW,
        "run_status": "SUCCESS",
        "created_at": NOW,
    }
    values.update(overrides)
    return values


class StubService:
    def __init__(self):
        self.result = PipelineListResponse(
            items=[PipelineResponse(**pipeline_data())],
            pagination=PipelinePaginationMetadata(
                limit=50, offset=0, total=1, returned_count=1
            ),
        )
        self.error = None
        self.arguments = None

    async def list_pipelines(self, **arguments):
        self.arguments = arguments
        if self.error:
            raise self.error
        return self.result


class StubRepository:
    def __init__(self, rows=None, total=0):
        self.rows = [] if rows is None else rows
        self.total = total
        self.arguments = None

    async def list_pipelines(self, **arguments):
        self.arguments = arguments
        return self.rows, self.total


class RecordingResult:
    async def fetchone(self):
        return (0,)


class RecordingCursor:
    def __init__(self, connection):
        self.connection = connection

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        return False

    async def execute(self, query, parameters):
        self.connection.list_query = query
        self.connection.list_parameters = parameters

    async def fetchall(self):
        return []


class RecordingConnection:
    async def execute(self, query, parameters):
        self.count_query = query
        self.count_parameters = parameters
        return RecordingResult()

    def cursor(self, row_factory=None):
        return RecordingCursor(self)


class ConnectionContext:
    def __init__(self, connection):
        self.connection = connection

    async def __aenter__(self):
        return self.connection

    async def __aexit__(self, exc_type, exc_value, traceback):
        return False


class RecordingPool:
    def __init__(self):
        self.connection_instance = RecordingConnection()

    def connection(self):
        return ConnectionContext(self.connection_instance)


class PipelineRouteTests(unittest.TestCase):
    def setUp(self):
        self.service = StubService()
        app.dependency_overrides[get_pipeline_service] = lambda: self.service
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.client.close()

    def test_list_success_and_defaults(self):
        response = self.client.get("/api/v1/pipelines")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["items"][0]["pipeline_run_id"],
            str(PIPELINE_RUN_ID),
        )
        self.assertEqual(self.service.arguments["limit"], 50)
        self.assertEqual(self.service.arguments["offset"], 0)

    def test_empty_result(self):
        self.service.result = PipelineListResponse(
            items=[],
            pagination=PipelinePaginationMetadata(
                limit=50, offset=0, total=0, returned_count=0
            ),
        )
        response = self.client.get("/api/v1/pipelines")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["items"], [])
        self.assertEqual(response.json()["pagination"]["total"], 0)
        self.assertEqual(response.json()["pagination"]["returned_count"], 0)

    def test_pagination(self):
        response = self.client.get("/api/v1/pipelines?limit=25&offset=75")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.service.arguments["limit"], 25)
        self.assertEqual(self.service.arguments["offset"], 75)

    def test_each_filter(self):
        cases = {
            "dag_id": ("ecommerce_pipeline", "ecommerce_pipeline"),
            "run_status": ("SUCCESS", "SUCCESS"),
            "pipeline_run_id": (str(PIPELINE_RUN_ID), PIPELINE_RUN_ID),
            "airflow_run_id": ("scheduled__example", "scheduled__example"),
        }
        for name, (query_value, expected) in cases.items():
            with self.subTest(filter=name):
                response = self.client.get(
                    f"/api/v1/pipelines?{name}={query_value}"
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    getattr(self.service.arguments["filters"], name), expected
                )

    def test_combined_filters(self):
        response = self.client.get(
            "/api/v1/pipelines"
            f"?pipeline_run_id={PIPELINE_RUN_ID}&dag_id=ecommerce_pipeline"
            "&run_status=SUCCESS&airflow_run_id=scheduled__example"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.service.arguments["filters"],
            PipelineFilters(
                dag_id="ecommerce_pipeline",
                run_status="SUCCESS",
                pipeline_run_id=PIPELINE_RUN_ID,
                airflow_run_id="scheduled__example",
            ),
        )

    def test_invalid_limit(self):
        for value in ("0", "101"):
            with self.subTest(value=value):
                response = self.client.get(
                    f"/api/v1/pipelines?limit={value}"
                )
                self.assertEqual(response.status_code, 422)

    def test_invalid_offset(self):
        response = self.client.get("/api/v1/pipelines?offset=-1")
        self.assertEqual(response.status_code, 422)

    def test_invalid_pipeline_uuid(self):
        response = self.client.get(
            "/api/v1/pipelines?pipeline_run_id=not-a-uuid"
        )
        self.assertEqual(response.status_code, 422)

    def test_database_failure_is_safe(self):
        self.service.error = RuntimeError("postgresql://user:secret@database")
        response = self.client.get("/api/v1/pipelines")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"detail": "Database unavailable"})
        self.assertNotIn("secret", response.text)

    def test_response_schema_validation_and_nullable_completion(self):
        self.assertIsNone(
            PipelineResponse(**pipeline_data(completed_at=None)).completed_at
        )
        with self.assertRaises(ValidationError):
            PipelineResponse(**pipeline_data(started_at=None))
        with self.assertRaises(ValidationError):
            PipelineResponse(**pipeline_data(duration_seconds=10))


class PipelineServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_service_validates_rows_and_builds_pagination(self):
        repository = StubRepository(rows=[pipeline_data()], total=7)
        result = await PipelineService(repository).list_pipelines(
            limit=1, offset=2, filters=PipelineFilters()
        )
        self.assertEqual(result.pagination.total, 7)
        self.assertEqual(result.pagination.returned_count, 1)
        self.assertIsInstance(result.items[0].pipeline_run_id, UUID)


class PipelineRepositoryTests(unittest.IsolatedAsyncioTestCase):
    async def test_parameterized_filters_and_deterministic_ordering(self):
        pool = RecordingPool()
        filters = PipelineFilters(
            dag_id="ecommerce_pipeline",
            run_status="SUCCESS",
            pipeline_run_id=PIPELINE_RUN_ID,
            airflow_run_id="scheduled__example",
        )
        await PipelineRepository(pool).list_pipelines(
            limit=10, offset=20, filters=filters
        )
        connection = pool.connection_instance
        normalized = " ".join(connection.list_query.split())
        self.assertIn(
            "ORDER BY started_at DESC, pipeline_run_id DESC", normalized
        )
        self.assertNotIn("'ecommerce_pipeline'", connection.list_query)
        expected = [
            "ecommerce_pipeline",
            "SUCCESS",
            PIPELINE_RUN_ID,
            "scheduled__example",
        ]
        self.assertEqual(connection.count_parameters, expected)
        self.assertEqual(connection.list_parameters, [*expected, 10, 20])


if __name__ == "__main__":
    unittest.main()
