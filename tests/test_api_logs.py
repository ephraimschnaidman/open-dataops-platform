import os
import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "platform"))

from api.auth_dependencies import get_current_active_user  # noqa: E402
from api.main import app  # noqa: E402
from api.services.logs import REDACTED, redact_sensitive_details  # noqa: E402
from api.routes.logs import get_log_service  # noqa: E402
from tests.api_auth_test_helpers import ACTIVE_TEST_USER  # noqa: E402


class LogRedactionAndValidationTests(unittest.TestCase):
    def test_recursive_redaction_handles_common_separators(self):
        value = {"credential": "x", "nested": [{"API-Key": "y", "safe_token_count": 3}],
                 "private_key": "z", "message": "keep"}
        result = redact_sensitive_details(value)
        self.assertEqual(result["credential"], REDACTED)
        self.assertEqual(result["nested"][0]["API-Key"], REDACTED)
        self.assertEqual(result["private_key"], REDACTED)
        self.assertEqual(result["nested"][0]["safe_token_count"], 3)
        self.assertEqual(result["message"], "keep")

    def test_invalid_filters_are_422(self):
        app.dependency_overrides[get_current_active_user] = lambda: ACTIVE_TEST_USER
        client = TestClient(app)
        for path in (
            "/api/v1/logs?level=TRACE", "/api/v1/logs?sort=sideways",
            "/api/v1/logs?occurred_from=2026-08-10T00:00:00",
            "/api/v1/logs?occurred_from=2026-08-11T00:00:00Z&occurred_to=2026-08-10T00:00:00Z",
            "/api/v1/logs/bad_event",
        ):
            self.assertEqual(client.get(path).status_code, 422)
        app.dependency_overrides.clear(); client.close()

    def test_database_failure_is_sanitized(self):
        class ErrorService:
            async def list_logs(self, **arguments):
                raise RuntimeError("postgres password secret")
        app.dependency_overrides[get_current_active_user] = lambda: ACTIVE_TEST_USER
        app.dependency_overrides[get_log_service] = lambda: ErrorService()
        client = TestClient(app)
        response = client.get("/api/v1/logs")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"detail": "Database unavailable"})
        self.assertNotIn("secret", response.text)
        app.dependency_overrides.clear(); client.close()


@unittest.skipUnless(os.getenv("RUN_OPERATIONAL_API_INTEGRATION") == "1", "live PostgreSQL required")
class LogIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.dependency_overrides[get_current_active_user] = lambda: ACTIVE_TEST_USER
        cls.client = TestClient(app); cls.client.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.client.__exit__(None, None, None); app.dependency_overrides.clear()

    def test_filters_repeatable_levels_and_ordering(self):
        all_logs = self.client.get("/api/v1/logs")
        self.assertEqual(all_logs.status_code, 200)
        self.assertEqual(all_logs.json()["pagination"]["total"], 6)
        levels = self.client.get("/api/v1/logs?level=ERROR&level=WARNING&pipeline=events-processing").json()["items"]
        self.assertEqual({item["level"] for item in levels}, {"ERROR", "WARNING"})
        oldest = self.client.get("/api/v1/logs?alert=ALT-1042&sort=oldest").json()["items"]
        self.assertEqual([item["event_key"] for item in oldest], ["evt-005", "evt-004", "evt-003", "evt-002", "evt-001"])
        newest = self.client.get("/api/v1/logs?alert=ALT-1042&sort=newest").json()["items"]
        self.assertEqual([item["event_key"] for item in newest], list(reversed([item["event_key"] for item in oldest])))
        billing = self.client.get("/api/v1/logs?check=order-id-unique&rule_code=CHECK_UNIQUENESS_VIOLATION").json()["items"]
        self.assertEqual(billing[0]["event_key"], "evt-007")

    def test_event_detail_extracts_and_redacts_evidence(self):
        body = self.client.get("/api/v1/logs/evt-001").json()
        self.assertEqual(body["details"]["credential"], REDACTED)
        self.assertNotIn("interpretation", body["details"])
        self.assertNotIn("stack_trace", body["details"])
        self.assertIn("authentication attempts", body["interpretation"])
        self.assertIn("AuthenticationError", body["stack_trace"])
        self.assertEqual(body["alert"]["alert_key"], "ALT-1042")

    def test_unknown_event_is_exact_404(self):
        response = self.client.get("/api/v1/logs/evt-999")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "Log event not found"})
