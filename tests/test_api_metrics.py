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
from api.repositories.metrics import MetricFilters  # noqa: E402
from api.routes.metrics import get_metric_service  # noqa: E402
from api.schemas.metrics import (  # noqa: E402
    MetricListResponse,
    MetricPaginationMetadata,
    MetricResponse,
)
from api.services.metrics import MetricService  # noqa: E402
from tests.api_auth_test_helpers import ACTIVE_TEST_USER  # noqa: E402

METRIC_ID = UUID("11111111-1111-4111-8111-111111111111")
PIPELINE_RUN_ID = UUID("22222222-2222-4222-8222-222222222222")
NOW = datetime(2026, 7, 28, 12, 0, tzinfo=timezone.utc)


def metric_data(**overrides):
    values = {
        "metric_id": METRIC_ID,
        "pipeline_run_id": PIPELINE_RUN_ID,
        "table_schema": "raw",
        "table_name": "orders",
        "row_count": 42,
        "freshness_column": "created_at",
        "max_freshness_value": NOW,
        "measured_at": NOW,
        "created_at": NOW,
    }
    values.update(overrides)
    return values


class StubMetricService:
    def __init__(self):
        self.result = MetricListResponse(
            items=[MetricResponse(**metric_data())],
            pagination=MetricPaginationMetadata(
                limit=50,
                offset=0,
                total=1,
                returned_count=1,
            ),
        )
        self.error = None
        self.arguments = None

    async def list_metrics(self, **arguments):
        self.arguments = arguments
        if self.error:
            raise self.error
        return self.result


class StubMetricRepository:
    def __init__(self, rows=None, total=0):
        self.rows = [] if rows is None else rows
        self.total = total
        self.arguments = None

    async def list_metrics(self, **arguments):
        self.arguments = arguments
        return self.rows, self.total


class MetricApiRouteTests(unittest.TestCase):
    def setUp(self):
        self.service = StubMetricService()
        app.dependency_overrides[get_metric_service] = lambda: self.service
        app.dependency_overrides[get_current_active_user] = (
            lambda: ACTIVE_TEST_USER
        )
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.client.close()

    def test_metric_list_success(self):
        response = self.client.get("/api/v1/metrics")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["items"][0]["metric_id"], str(METRIC_ID))
        self.assertEqual(response.json()["items"][0]["row_count"], 42)

    def test_empty_result(self):
        self.service.result = MetricListResponse(
            items=[],
            pagination=MetricPaginationMetadata(
                limit=50,
                offset=0,
                total=0,
                returned_count=0,
            ),
        )

        response = self.client.get("/api/v1/metrics")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["items"], [])
        self.assertEqual(response.json()["pagination"]["total"], 0)
        self.assertEqual(response.json()["pagination"]["returned_count"], 0)

    def test_pagination_parameters(self):
        response = self.client.get("/api/v1/metrics?limit=25&offset=50")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.service.arguments["limit"], 25)
        self.assertEqual(self.service.arguments["offset"], 50)

    def test_pipeline_run_id_filter(self):
        response = self.client.get(
            f"/api/v1/metrics?pipeline_run_id={PIPELINE_RUN_ID}"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.service.arguments["filters"].pipeline_run_id,
            PIPELINE_RUN_ID,
        )

    def test_table_schema_filter(self):
        response = self.client.get("/api/v1/metrics?table_schema=raw")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.service.arguments["filters"].table_schema, "raw")

    def test_table_name_filter(self):
        response = self.client.get("/api/v1/metrics?table_name=orders")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.service.arguments["filters"].table_name, "orders")

    def test_combined_filters(self):
        response = self.client.get(
            "/api/v1/metrics"
            f"?pipeline_run_id={PIPELINE_RUN_ID}"
            "&table_schema=raw&table_name=orders"
        )

        filters = self.service.arguments["filters"]
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            filters,
            MetricFilters(
                pipeline_run_id=PIPELINE_RUN_ID,
                table_schema="raw",
                table_name="orders",
            ),
        )

    def test_invalid_limit_returns_422(self):
        for limit in ("0", "101"):
            with self.subTest(limit=limit):
                response = self.client.get(f"/api/v1/metrics?limit={limit}")
                self.assertEqual(response.status_code, 422)

    def test_invalid_offset_returns_422(self):
        response = self.client.get("/api/v1/metrics?offset=-1")

        self.assertEqual(response.status_code, 422)

    def test_invalid_pipeline_run_id_returns_422(self):
        response = self.client.get(
            "/api/v1/metrics?pipeline_run_id=not-a-uuid"
        )

        self.assertEqual(response.status_code, 422)

    def test_database_error_returns_safe_503(self):
        self.service.error = RuntimeError("SELECT secret FROM hidden")

        response = self.client.get("/api/v1/metrics")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"detail": "Database unavailable"})
        self.assertNotIn("SELECT", response.text)

    def test_latest_true_is_passed_to_service(self):
        response = self.client.get("/api/v1/metrics?latest=true")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.service.arguments["latest"])

    def test_response_schema_rejects_invalid_row_count(self):
        with self.assertRaises(ValidationError):
            MetricResponse(**metric_data(row_count=-1))


class MetricServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_service_builds_validated_pagination_and_nullable_fields(self):
        repository = StubMetricRepository(
            rows=[
                metric_data(
                    freshness_column=None,
                    max_freshness_value=None,
                )
            ],
            total=7,
        )

        result = await MetricService(repository).list_metrics(
            limit=2,
            offset=4,
            filters=MetricFilters(table_schema="raw"),
            latest=True,
        )

        self.assertEqual(result.pagination.limit, 2)
        self.assertEqual(result.pagination.offset, 4)
        self.assertEqual(result.pagination.total, 7)
        self.assertEqual(result.pagination.returned_count, 1)
        self.assertIsNone(result.items[0].freshness_column)
        self.assertIsNone(result.items[0].max_freshness_value)
        self.assertTrue(repository.arguments["latest"])


if __name__ == "__main__":
    unittest.main()
