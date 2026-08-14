import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "platform"))

from api.auth_dependencies import get_current_active_user  # noqa: E402
from api.main import app  # noqa: E402
from api.repositories.aggregations import AggregationFilters  # noqa: E402
from api.repositories.aggregations import AggregationRepository  # noqa: E402
from api.routes.monitoring import get_monitoring_service  # noqa: E402
from api.schemas.aggregations import AggregationMetric  # noqa: E402
from api.services.aggregations import AggregationService  # noqa: E402
from tests.aggregation_test_fixtures import NOW, StubAggregationRepository  # noqa: E402
from tests.api_auth_test_helpers import ACTIVE_TEST_USER  # noqa: E402


class MonitoringServiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.repository = StubAggregationRepository()
        self.service = AggregationService(self.repository, clock=lambda: NOW)

    async def test_canonical_state_metrics_and_issue_deduplication(self):
        result = await self.service.get_monitoring(
            window="24h", filters=AggregationFilters(environment="production")
        )
        self.assertEqual(result.overall_state, "CRITICAL")
        self.assertEqual(
            [(item.name, item.operational_status) for item in result.pipeline_health.items],
            [("Events Processing", "FAILED"), ("Billing Reconciliation", "WARNING"),
             ("Customer Ingestion", "HEALTHY")],
        )
        self.assertEqual(
            [(item.name, item.operational_status) for item in result.source_health.items],
            [("Events Kafka", "DISCONNECTED"), ("Billing PostgreSQL", "WARNING"),
             ("Production Warehouse", "HEALTHY")],
        )
        keys = [item.issue_key for item in result.active_issues.items]
        self.assertEqual(keys.count("ALT-1042"), 1)
        self.assertEqual(keys.count("ALT-1040"), 1)
        self.assertIn("source:billing-postgres:warning", keys)
        self.assertNotIn("source:events-kafka:disconnected", keys)
        self.assertFalse(any(key.startswith("validation:order-id-unique") for key in keys))
        billing = next(item for item in result.validation_conditions.items
                       if item.check_key == "order-id-unique")
        self.assertEqual(billing.represented_by_alert_key, "ALT-1040")
        self.assertEqual((billing.actual, billing.expected), ("318 duplicates", "0 duplicates"))
        self.assertEqual(result.metrics.pipeline_success_rate.value, 50.0)
        self.assertEqual(result.metrics.successful_runs.value, 2.0)
        self.assertEqual(result.metrics.failed_runs.value, 2.0)
        self.assertEqual(result.metrics.schedule_adherence.availability, "UNSUPPORTED")
        self.assertEqual(result.metrics.healthy_sources.denominator, 3)
        self.assertEqual(result.metrics.healthy_sources.numerator, 1)

    async def test_no_resources_is_no_data_and_rates_are_insufficient(self):
        self.repository.get_pipelines = lambda filters: _async([])
        self.repository.get_sources = lambda filters: _async([])
        self.repository.get_active_alerts = lambda filters: _async([])
        self.repository.get_latest_failed_validations = lambda filters: _async([])
        self.repository.get_runs = lambda *args, **kwargs: _async([])
        self.repository.get_events = lambda *args, **kwargs: _async([])
        result = await self.service.get_monitoring(window="1h", filters=AggregationFilters())
        self.assertEqual((result.state_availability, result.overall_state), ("NO_DATA", None))
        self.assertEqual(result.metrics.pipeline_success_rate.availability, "INSUFFICIENT_DATA")
        self.assertEqual(result.metrics.successful_runs.value, 0)

    async def test_warning_healthy_and_disabled_only_state_precedence(self):
        self.repository.get_pipelines = lambda filters: _async([])
        self.repository.get_sources = lambda filters: _async([
            {"data_source_id": "billing-s", "source_key": "billing-postgres",
             "name": "Billing PostgreSQL", "source_type": "POSTGRESQL",
             "environment": {"environment_key": "production", "name": "Production"},
             "operational_status": "WARNING", "connected_pipeline_count": 0,
             "last_observed_at": None}
        ])
        self.repository.get_active_alerts = lambda filters: _async([])
        self.repository.get_latest_failed_validations = lambda filters: _async([])
        self.repository.get_runs = lambda *args, **kwargs: _async([])
        self.repository.get_events = lambda *args, **kwargs: _async([])
        warning = await self.service.get_monitoring(window="1h", filters=AggregationFilters())
        self.assertEqual(warning.overall_state, "WARNING")

        self.repository.get_sources = lambda filters: _async([
            {"data_source_id": "healthy-s", "source_key": "analytics-warehouse",
             "name": "Production Warehouse", "source_type": "SNOWFLAKE",
             "environment": {"environment_key": "production", "name": "Production"},
             "operational_status": "HEALTHY", "connected_pipeline_count": 0,
             "last_observed_at": None}
        ])
        healthy = await self.service.get_monitoring(window="1h", filters=AggregationFilters())
        self.assertEqual(healthy.overall_state, "HEALTHY")

        self.repository.get_sources = lambda filters: _async([
            {"data_source_id": "disabled-s", "source_key": "customer-sqlserver",
             "name": "Legacy SQL Server", "source_type": "SQL_SERVER",
             "environment": {"environment_key": "development", "name": "Development"},
             "operational_status": "DISABLED", "connected_pipeline_count": 0,
             "last_observed_at": None}
        ])
        disabled = await self.service.get_monitoring(window="1h", filters=AggregationFilters())
        self.assertEqual((disabled.state_availability, disabled.overall_state), ("NO_DATA", None))

    def test_repository_scope_is_parameterized(self):
        where, parameters = AggregationRepository._pipeline_scope(AggregationFilters(
            environment="production", pipeline="events-processing"
        ))
        self.assertEqual(parameters, ["production", "events-processing"])
        self.assertNotIn("production", where)
        self.assertNotIn("events-processing", where)


async def _async(value):
    return value


class MonitoringRouteTests(unittest.TestCase):
    def setUp(self):
        repository = StubAggregationRepository()
        self.service = AggregationService(repository, clock=lambda: NOW)
        app.dependency_overrides[get_monitoring_service] = lambda: self.service
        app.dependency_overrides[get_current_active_user] = lambda: ACTIVE_TEST_USER
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear(); self.client.close()

    def test_route_filters_and_validation(self):
        response = self.client.get("/api/v1/monitoring?window=24h&environment=production")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["scope"]["environment"], "production")
        for path in (
            "/api/v1/monitoring?window=90d",
            "/api/v1/monitoring?environment=Not_Valid",
            "/api/v1/monitoring?pipeline=events-processing&source=events-kafka",
        ):
            self.assertEqual(self.client.get(path).status_code, 422)

    def test_sanitized_503(self):
        repository = StubAggregationRepository(); repository.error = RuntimeError("secret")
        app.dependency_overrides[get_monitoring_service] = lambda: AggregationService(repository)
        response = self.client.get("/api/v1/monitoring")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"detail": "Database unavailable"})
        self.assertNotIn("secret", response.text)

    def test_schema_forbids_extra(self):
        with self.assertRaises(ValidationError):
            AggregationMetric.model_validate({
                "availability": "AVAILABLE", "unit": "COUNT", "value": 1,
                "sample_count": 1, "previous": {"availability": "AVAILABLE", "value": 0,
                "sample_count": 1}, "delta": 1, "points": [], "reason": None,
                "fabricated": "value",
            })


if __name__ == "__main__":
    unittest.main()
