import os
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "platform"))

from api.auth_dependencies import get_current_active_user  # noqa: E402
from api.main import app  # noqa: E402
from api.routes.validation import get_validation_service  # noqa: E402
from api.schemas.validation import ValidationListItem  # noqa: E402
from tests.api_auth_test_helpers import ACTIVE_TEST_USER  # noqa: E402

NOW = datetime(2026, 8, 10, tzinfo=timezone.utc)


def not_evaluated_item():
    return {
        "check_key": "warehouse-customer-check", "name": "Warehouse customer check",
        "type": "CUSTOM", "dataset_name": "customers", "column_name": "customer_id",
        "result": "NOT_EVALUATED", "severity": "BLOCKING",
        "platform_code": "VALIDATION_EXECUTION_FAILED", "rule_code": None,
        "vendor_code": "SNOWFLAKE_QUERY_CONNECTION_RESET", "actual": None,
        "expected": "0 nulls", "message": "query failed", "evaluated_at": NOW,
        "stage": "VALIDATE",
        "run": {"corvetra_run_id": "run_FIXTURE", "status": "FAILED", "stage": "VALIDATE",
            "started_at": NOW, "completed_at": NOW, "duration_seconds": 0,
            "platform_code": "VALIDATION_EXECUTION_FAILED", "vendor_code": "SNOWFLAKE_QUERY_CONNECTION_RESET", "rule_code": None},
        "pipeline": {"pipeline_key": "warehouse-sync", "name": "Warehouse Sync", "operational_status": "FAILED"},
        "source": {"source_key": "analytics-warehouse", "name": "Production Warehouse", "source_type": "SNOWFLAKE", "operational_status": "HEALTHY"},
        "environment": {"environment_key": "production", "name": "Production"},
    }


class ValidationSchemaAndRouteTests(unittest.TestCase):
    def test_not_evaluated_contract_and_strict_schema(self):
        self.assertEqual(ValidationListItem.model_validate(not_evaluated_item()).result, "NOT_EVALUATED")
        with self.assertRaises(ValidationError):
            ValidationListItem.model_validate({**not_evaluated_item(), "dbt_node": "raw"})

    def test_invalid_ranges_and_ambiguous_detail_are_rejected(self):
        app.dependency_overrides[get_current_active_user] = lambda: ACTIVE_TEST_USER
        app.dependency_overrides[get_validation_service] = lambda: object()
        client = TestClient(app)
        for path in (
            "/api/v1/validation?result=BAD",
            "/api/v1/validation?evaluated_from=2026-08-10T00:00:00",
            "/api/v1/validation?evaluated_from=2026-08-11T00:00:00Z&evaluated_to=2026-08-10T00:00:00Z",
            "/api/v1/validation/order-id-unique",
        ):
            self.assertIn(client.get(path).status_code, (404, 422))
        app.dependency_overrides.clear(); client.close()

    def test_database_failure_is_sanitized(self):
        class ErrorService:
            async def list_validation(self, **arguments):
                raise RuntimeError("SELECT secret FROM hidden")
        app.dependency_overrides[get_current_active_user] = lambda: ACTIVE_TEST_USER
        app.dependency_overrides[get_validation_service] = lambda: ErrorService()
        client = TestClient(app)
        response = client.get("/api/v1/validation")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"detail": "Database unavailable"})
        self.assertNotIn("secret", response.text)
        app.dependency_overrides.clear(); client.close()


@unittest.skipUnless(os.getenv("RUN_OPERATIONAL_API_INTEGRATION") == "1", "live PostgreSQL required")
class ValidationIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.dependency_overrides[get_current_active_user] = lambda: ACTIVE_TEST_USER
        cls.client = TestClient(app); cls.client.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.client.__exit__(None, None, None); app.dependency_overrides.clear()

    def test_latest_results_and_filters(self):
        response = self.client.get("/api/v1/validation")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["pagination"]["total"], 4)
        failed = self.client.get("/api/v1/validation?result=FAILED&severity=WARNING&pipeline=customer-ingestion").json()["items"]
        self.assertEqual(failed[0]["check_key"], "customer-email-null-rate")
        passed = self.client.get("/api/v1/validation?run=run_01J92CING8&check_type=NOT_NULL").json()["items"]
        self.assertEqual((passed[0]["check_key"], passed[0]["result"]), ("customer-id-not-null", "PASSED"))

    def test_billing_composite_detail(self):
        response = self.client.get("/api/v1/validation/order-id-unique/runs/run_01J97BIL02")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual((body["name"], body["result"], body["severity"]), ("Order ID unique", "FAILED", "BLOCKING"))
        self.assertEqual((body["actual"], body["expected"]), ("318 duplicates", "0 duplicates"))
        self.assertEqual(body["related_alerts"][0]["alert_key"], "ALT-1040")
        self.assertEqual(body["technical_evidence"][0]["event_key"], "evt-007")
        self.assertEqual(body["run"]["corvetra_run_id"], "run_01J97BIL02")

    def test_unknown_composite_identity_is_exact_404(self):
        response = self.client.get("/api/v1/validation/order-id-unique/runs/run_MISSING")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "Validation execution not found"})
