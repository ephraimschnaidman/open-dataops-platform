import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "platform"))

from api.auth_dependencies import get_current_active_user  # noqa: E402
from api.main import app, create_app  # noqa: E402
from api.routes.dashboard import get_dashboard_service  # noqa: E402
from api.services.aggregations import AggregationService  # noqa: E402
from tests.aggregation_test_fixtures import NOW, StubAggregationRepository  # noqa: E402
from tests.api_auth_test_helpers import ACTIVE_TEST_USER  # noqa: E402
from tests.test_api_authorization import make_settings  # noqa: E402


class DashboardServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_dashboard_is_concise_canonical_projection(self):
        result = await AggregationService(
            StubAggregationRepository(), clock=lambda: NOW
        ).get_dashboard(environment="production")
        self.assertEqual(result.overall_state, "CRITICAL")
        self.assertEqual(result.summary.configured_pipelines, 3)
        self.assertEqual(result.summary.active_alerts.model_dump(),
                         {"total": 2, "critical": 1, "warning": 1})
        self.assertEqual(result.summary.sources, 3)
        self.assertEqual(result.summary.non_disabled_sources, 3)
        self.assertEqual([item.corvetra_run_id for item in result.latest_runs.items][0],
                         "run_01J94EVT18")
        self.assertEqual(result.health_indicators.freshness_compliance.availability,
                         "UNSUPPORTED")
        issue_keys = [item.issue_key for item in result.active_issues.items]
        self.assertEqual(issue_keys.count("ALT-1042"), 1)
        self.assertEqual(issue_keys.count("ALT-1040"), 1)
        self.assertEqual(
            [(item.name, item.operational_status)
             for item in result.pipelines_requiring_attention.items],
            [("Events Processing", "FAILED"), ("Billing Reconciliation", "WARNING")],
        )


class DashboardRouteTests(unittest.TestCase):
    def setUp(self):
        self.repository = StubAggregationRepository()
        app.dependency_overrides[get_dashboard_service] = lambda: AggregationService(
            self.repository, clock=lambda: NOW
        )
        app.dependency_overrides[get_current_active_user] = lambda: ACTIVE_TEST_USER
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear(); self.client.close()

    def test_route_and_sanitized_error(self):
        response = self.client.get("/api/v1/dashboard?environment=production")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["environment"], "production")
        self.assertNotIn("records", response.text)
        self.assertNotIn("trigger", response.text)
        self.repository.error = RuntimeError("secret")
        response = self.client.get("/api/v1/dashboard")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"detail": "Database unavailable"})

    def test_openapi_routes_are_typed_and_secured(self):
        schema = create_app(make_settings()).openapi()
        for path in ("/api/v1/monitoring", "/api/v1/health-metrics", "/api/v1/dashboard"):
            operation = schema["paths"][path]["get"]
            self.assertEqual(operation["security"], [{"OAuth2PasswordBearer": []}])
            self.assertIn("200", operation["responses"])
            self.assertIn("503", operation["responses"])


if __name__ == "__main__":
    unittest.main()
