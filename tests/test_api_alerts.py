import os
import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "platform"))

from api.auth_dependencies import get_current_active_user  # noqa: E402
from api.main import app  # noqa: E402
from api.routes.alerts import get_alert_service  # noqa: E402
from api.services.alerts import AlertNotFoundError  # noqa: E402
from tests.api_auth_test_helpers import ACTIVE_TEST_USER  # noqa: E402


class ErrorService:
    error = RuntimeError("postgresql://user:secret@database")
    async def list_alerts(self, **arguments): raise self.error
    async def get_alert(self, key): raise self.error


class AlertRouteSafetyTests(unittest.TestCase):
    def setUp(self):
        app.dependency_overrides[get_current_active_user] = lambda: ACTIVE_TEST_USER
        app.dependency_overrides[get_alert_service] = lambda: ErrorService()
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear(); self.client.close()

    def test_range_identifier_and_filters_are_validated(self):
        for path in (
            "/api/v1/alerts?status=BAD", "/api/v1/alerts?severity=BAD",
            "/api/v1/alerts?activity_from=2026-08-10T00:00:00",
            "/api/v1/alerts?activity_from=2026-08-11T00:00:00Z&activity_to=2026-08-10T00:00:00Z",
            "/api/v1/alerts/not-an-alert",
        ):
            self.assertEqual(self.client.get(path).status_code, 422)

    def test_database_failure_is_sanitized(self):
        response = self.client.get("/api/v1/alerts")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"detail": "Database unavailable"})
        self.assertNotIn("secret", response.text)


@unittest.skipUnless(os.getenv("RUN_OPERATIONAL_API_INTEGRATION") == "1", "live PostgreSQL required")
class AlertIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.dependency_overrides[get_current_active_user] = lambda: ACTIVE_TEST_USER
        cls.client = TestClient(app); cls.client.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.client.__exit__(None, None, None); app.dependency_overrides.clear()

    def test_list_filters_pagination_and_canonical_lifecycle(self):
        response = self.client.get("/api/v1/alerts?limit=2&offset=0")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["pagination"], {"limit": 2, "offset": 0, "total": 3, "returned_count": 2})
        active = self.client.get("/api/v1/alerts?status=ACTIVE").json()["items"]
        self.assertEqual({item["alert_key"] for item in active}, {"ALT-1042", "ALT-1040"})
        resolved = self.client.get("/api/v1/alerts?status=RESOLVED&severity=WARNING&pipeline=customer-ingestion").json()["items"]
        self.assertEqual(resolved[0]["alert_key"], "ALT-1037")
        searched = self.client.get("/api/v1/alerts?search=SASL_AUTHENTICATION_FAILED").json()["items"]
        self.assertEqual(searched[0]["alert_key"], "ALT-1042")

    def test_events_and_billing_details(self):
        events = self.client.get("/api/v1/alerts/ALT-1042")
        self.assertEqual(events.status_code, 200)
        body = events.json()
        self.assertEqual((body["pipeline"]["name"], body["source"]["name"], body["environment"]["name"]),
                         ("Events Processing", "Events Kafka", "Production"))
        self.assertEqual(body["run"]["corvetra_run_id"], "run_01J94EVT18")
        self.assertEqual([item["event_key"] for item in body["recent_technical_evidence"]],
                         ["evt-005", "evt-004", "evt-003", "evt-002", "evt-001"])
        billing = self.client.get("/api/v1/alerts/ALT-1040").json()
        self.assertEqual(billing["validation_execution"]["check_key"], "order-id-unique")
        self.assertEqual(billing["technical_evidence_count"], 1)
        resolved = self.client.get("/api/v1/alerts/ALT-1037").json()
        self.assertEqual((resolved["status"], resolved["technical_evidence_count"]), ("RESOLVED", 0))

    def test_unknown_alert_is_exact_404(self):
        response = self.client.get("/api/v1/alerts/ALT-9999")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "Alert not found"})
