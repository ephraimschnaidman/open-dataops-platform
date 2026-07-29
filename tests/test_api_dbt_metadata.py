import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from fastapi.testclient import TestClient
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "platform"))

from api.main import app  # noqa: E402
from api.auth_dependencies import get_current_active_user  # noqa: E402
from api.repositories.dbt_metadata import (  # noqa: E402
    DbtMetadataFilters,
    DbtMetadataRepository,
)
from api.routes.dbt_metadata import get_dbt_metadata_service  # noqa: E402
from api.schemas.dbt_metadata import (  # noqa: E402
    DbtMetadataListResponse,
    DbtMetadataPaginationMetadata,
    DbtMetadataResponse,
)
from api.services.dbt_metadata import DbtMetadataService  # noqa: E402
from tests.api_auth_test_helpers import ACTIVE_TEST_USER  # noqa: E402

RESULT_ID = UUID("11111111-1111-4111-8111-111111111111")
PIPELINE_RUN_ID = UUID("22222222-2222-4222-8222-222222222222")
NOW = datetime(2026, 7, 28, 12, 0, tzinfo=timezone.utc)


def metadata_data(**overrides):
    values = {
        "result_id": RESULT_ID,
        "pipeline_run_id": PIPELINE_RUN_ID,
        "invocation_id": "dbt-invocation-1",
        "command_type": "run",
        "node_unique_id": "model.open_dataops.stg_orders",
        "node_name": "stg_orders",
        "resource_type": "model",
        "execution_status": "success",
        "execution_time_seconds": 1.25,
        "message": None,
        "recorded_at": NOW,
    }
    values.update(overrides)
    return values


class StubService:
    def __init__(self):
        self.result = DbtMetadataListResponse(
            items=[DbtMetadataResponse(**metadata_data())],
            pagination=DbtMetadataPaginationMetadata(
                limit=50, offset=0, total=1, returned_count=1
            ),
        )
        self.error = None
        self.arguments = None

    async def list_dbt_metadata(self, **arguments):
        self.arguments = arguments
        if self.error:
            raise self.error
        return self.result


class StubRepository:
    def __init__(self, rows=None, total=0):
        self.rows = [] if rows is None else rows
        self.total = total
        self.arguments = None

    async def list_dbt_metadata(self, **arguments):
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


class DbtMetadataRouteTests(unittest.TestCase):
    def setUp(self):
        self.service = StubService()
        app.dependency_overrides[get_dbt_metadata_service] = lambda: self.service
        app.dependency_overrides[get_current_active_user] = (
            lambda: ACTIVE_TEST_USER
        )
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.client.close()

    def test_list_success_and_defaults(self):
        response = self.client.get("/api/v1/dbt-metadata")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["items"][0]["result_id"], str(RESULT_ID))
        self.assertEqual(self.service.arguments["limit"], 50)
        self.assertEqual(self.service.arguments["offset"], 0)

    def test_empty_result(self):
        self.service.result = DbtMetadataListResponse(
            items=[],
            pagination=DbtMetadataPaginationMetadata(
                limit=50, offset=0, total=0, returned_count=0
            ),
        )
        response = self.client.get("/api/v1/dbt-metadata")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["items"], [])
        self.assertEqual(response.json()["pagination"]["total"], 0)
        self.assertEqual(response.json()["pagination"]["returned_count"], 0)

    def test_pagination(self):
        response = self.client.get("/api/v1/dbt-metadata?limit=25&offset=75")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.service.arguments["limit"], 25)
        self.assertEqual(self.service.arguments["offset"], 75)

    def test_each_filter(self):
        cases = {
            "pipeline_run_id": (str(PIPELINE_RUN_ID), PIPELINE_RUN_ID),
            "invocation_id": ("dbt-invocation-1", "dbt-invocation-1"),
            "resource_type": ("model", "model"),
            "execution_status": ("success", "success"),
            "node_name": ("stg_orders", "stg_orders"),
        }
        for name, (query_value, expected) in cases.items():
            with self.subTest(filter=name):
                response = self.client.get(
                    f"/api/v1/dbt-metadata?{name}={query_value}"
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    getattr(self.service.arguments["filters"], name), expected
                )

    def test_combined_filters(self):
        response = self.client.get(
            "/api/v1/dbt-metadata"
            f"?pipeline_run_id={PIPELINE_RUN_ID}"
            "&invocation_id=dbt-invocation-1&resource_type=model"
            "&execution_status=success&node_name=stg_orders"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.service.arguments["filters"],
            DbtMetadataFilters(
                pipeline_run_id=PIPELINE_RUN_ID,
                invocation_id="dbt-invocation-1",
                resource_type="model",
                execution_status="success",
                node_name="stg_orders",
            ),
        )

    def test_invalid_limit(self):
        for value in ("0", "101"):
            with self.subTest(value=value):
                self.assertEqual(
                    self.client.get(
                        f"/api/v1/dbt-metadata?limit={value}"
                    ).status_code,
                    422,
                )

    def test_invalid_offset(self):
        response = self.client.get("/api/v1/dbt-metadata?offset=-1")
        self.assertEqual(response.status_code, 422)

    def test_invalid_pipeline_run_uuid(self):
        response = self.client.get(
            "/api/v1/dbt-metadata?pipeline_run_id=not-a-uuid"
        )
        self.assertEqual(response.status_code, 422)

    def test_database_failure_is_safe(self):
        self.service.error = RuntimeError("SELECT password FROM secrets")
        response = self.client.get("/api/v1/dbt-metadata")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"detail": "Database unavailable"})
        self.assertNotIn("SELECT", response.text)

    def test_response_schema_validation(self):
        with self.assertRaises(ValidationError):
            DbtMetadataResponse(**metadata_data(recorded_at=None))
        with self.assertRaises(ValidationError):
            DbtMetadataResponse(**metadata_data(unpersisted_field="no"))


class DbtMetadataServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_service_validates_rows_and_counts_returned_items(self):
        repository = StubRepository(rows=[metadata_data()], total=9)
        result = await DbtMetadataService(repository).list_dbt_metadata(
            limit=1, offset=2, filters=DbtMetadataFilters()
        )
        self.assertEqual(result.pagination.total, 9)
        self.assertEqual(result.pagination.returned_count, 1)
        self.assertIsInstance(result.items[0].result_id, UUID)


class DbtMetadataRepositoryTests(unittest.IsolatedAsyncioTestCase):
    async def test_parameterized_filters_and_deterministic_ordering(self):
        pool = RecordingPool()
        filters = DbtMetadataFilters(
            pipeline_run_id=PIPELINE_RUN_ID,
            invocation_id="invocation",
            resource_type="model",
            execution_status="success",
            node_name="orders",
        )
        await DbtMetadataRepository(pool).list_dbt_metadata(
            limit=10, offset=20, filters=filters
        )
        connection = pool.connection_instance
        normalized = " ".join(connection.list_query.split())
        self.assertIn(
            "ORDER BY recorded_at DESC, result_id DESC", normalized
        )
        self.assertNotIn("'invocation'", connection.list_query)
        self.assertEqual(
            connection.list_parameters,
            [
                PIPELINE_RUN_ID,
                "invocation",
                "model",
                "success",
                "orders",
                10,
                20,
            ],
        )
        self.assertEqual(
            connection.count_parameters,
            [
                PIPELINE_RUN_ID,
                "invocation",
                "model",
                "success",
                "orders",
            ],
        )


if __name__ == "__main__":
    unittest.main()
