import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "platform"))

from api.auth_dependencies import get_current_active_user  # noqa: E402
from api.main import app  # noqa: E402
from api.repositories.aggregations import AggregationFilters  # noqa: E402
from api.routes.health_metrics import get_health_metrics_service  # noqa: E402
from api.services.aggregations import AggregationService  # noqa: E402
from tests.aggregation_test_fixtures import NOW, StubAggregationRepository  # noqa: E402
from tests.api_auth_test_helpers import ACTIVE_TEST_USER  # noqa: E402


class HealthMetricServiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.repository = StubAggregationRepository()
        self.service = AggregationService(self.repository, clock=lambda: NOW)

    async def test_exact_canonical_metrics_and_no_fabricated_history(self):
        result = await self.service.get_health_metrics(
            window="7d", filters=AggregationFilters(environment="production")
        )
        self.assertEqual(result.metrics.pipeline_success_rate.value, 40.0)
        self.assertEqual(result.metrics.pipeline_success_rate.sample_count, 5)
        self.assertAlmostEqual(result.metrics.average_runtime.value, 181.8824, places=4)
        self.assertEqual(result.metrics.validation_pass_rate.value, 50.0)
        self.assertEqual(result.metrics.validation_pass_rate.denominator, 4)
        self.assertEqual(result.metrics.source_availability.availability, "UNSUPPORTED")
        self.assertEqual(result.metrics.freshness_compliance.availability, "UNSUPPORTED")
        self.assertEqual(result.metrics.schedule_adherence.availability, "UNSUPPORTED")
        self.assertEqual(result.metrics.pipeline_success_rate.previous.availability,
                         "INSUFFICIENT_DATA")
        self.assertIsNone(result.metrics.pipeline_success_rate.delta)
        self.assertTrue(result.metrics.pipeline_success_rate.points)
        self.assertEqual(len(result.metrics.pipeline_success_rate.points), 2)
        self.assertTrue(all(point.sample_count > 0
                            for point in result.metrics.pipeline_success_rate.points))

    async def test_not_evaluated_is_not_passed(self):
        original = self.repository.get_validation_history

        async def with_not_evaluated(filters, *, evaluated_from, evaluated_to):
            rows = await original(filters, evaluated_from=evaluated_from, evaluated_to=evaluated_to)
            rows.append({**rows[0], "validation_execution_id": "not-evaluated",
                         "result_status": "NOT_EVALUATED"})
            return rows

        self.repository.get_validation_history = with_not_evaluated
        result = await self.service.get_health_metrics(window="7d", filters=AggregationFilters())
        self.assertEqual(result.metrics.validation_pass_rate.value, 50.0)
        self.assertEqual(result.metrics.validation_pass_rate.denominator, 4)
        item = next(row for row in result.validation_quality if row.check_key == "order-id-unique")
        self.assertEqual(item.not_evaluated, 1)
        self.assertEqual(item.pass_rate.denominator, 1)

    async def test_empty_history_is_typed_insufficient_not_zero_percent(self):
        self.repository.get_runs = lambda *args, **kwargs: _async([])
        self.repository.get_validation_history = lambda *args, **kwargs: _async([])
        result = await self.service.get_health_metrics(window="24h", filters=AggregationFilters())
        self.assertEqual(result.metrics.pipeline_success_rate.availability,
                         "INSUFFICIENT_DATA")
        self.assertIsNone(result.metrics.pipeline_success_rate.value)
        self.assertEqual(result.metrics.average_runtime.availability,
                         "INSUFFICIENT_DATA")
        self.assertEqual(result.metrics.validation_pass_rate.availability,
                         "INSUFFICIENT_DATA")


async def _async(value):
    return value


class HealthMetricRouteTests(unittest.TestCase):
    def setUp(self):
        self.repository = StubAggregationRepository()
        app.dependency_overrides[get_health_metrics_service] = lambda: AggregationService(
            self.repository, clock=lambda: NOW
        )
        app.dependency_overrides[get_current_active_user] = lambda: ACTIVE_TEST_USER
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear(); self.client.close()

    def test_ranges_scopes_and_invalid_scope(self):
        for window in ("24h", "7d", "30d", "90d"):
            self.assertEqual(self.client.get(f"/api/v1/health-metrics?window={window}").status_code, 200)
        response = self.client.get(
            "/api/v1/health-metrics?environment=production&pipeline=events-processing"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["scope"]["pipeline"], "events-processing")
        self.assertEqual(self.client.get(
            "/api/v1/health-metrics?pipeline=events-processing&source=events-kafka"
        ).status_code, 422)

    def test_sanitized_503(self):
        self.repository.error = RuntimeError("postgresql://secret")
        response = self.client.get("/api/v1/health-metrics")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"detail": "Database unavailable"})


if __name__ == "__main__":
    unittest.main()
