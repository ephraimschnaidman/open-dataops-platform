import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "platform"))

from api.auth_dependencies import get_current_active_user  # noqa: E402
from api.main import app  # noqa: E402
from api.repositories.pipelines import PipelineFilters, escape_like  # noqa: E402
from api.routes.pipelines import get_pipeline_service  # noqa: E402
from api.schemas.core_resources import PaginationMetadata  # noqa: E402
from api.schemas.pipelines import PipelineDetail, PipelineListItem, PipelineListResponse  # noqa: E402
from api.services.pipelines import PipelineNotFoundError, PipelineService  # noqa: E402
from tests.api_auth_test_helpers import ACTIVE_TEST_USER  # noqa: E402

NOW = datetime(2026, 8, 10, 14, 41, 3, tzinfo=timezone.utc)


def pipeline_item(**overrides):
    value = {
        "pipeline_key": "events-processing",
        "name": "Events Processing",
        "environment": {"environment_key": "production", "name": "Production"},
        "source": {
            "source_key": "events-kafka", "name": "Events Kafka",
            "source_type": "KAFKA", "operational_status": "DISCONNECTED",
        },
        "is_enabled": True,
        "operational_status": "FAILED",
        "latest_run": {
            "corvetra_run_id": "run_01J94EVT18", "status": "FAILED",
            "stage": "EXTRACT", "started_at": NOW, "completed_at": NOW,
            "duration_seconds": 0.0, "platform_code": "PIPELINE_EXECUTION_FAILED",
            "vendor_code": "SASL_AUTHENTICATION_FAILED", "rule_code": None,
        },
        "current_issue": {
            "alert_key": "ALT-1042", "title": "Pipeline execution failing",
            "severity": "CRITICAL", "status": "OPEN",
            "platform_code": "PIPELINE_EXECUTION_FAILED",
            "vendor_code": "SASL_AUTHENTICATION_FAILED", "rule_code": None,
            "message": "failure", "detected_at": NOW, "last_seen_at": NOW,
            "acknowledged_at": None, "resolved_at": None,
        },
    }
    value.update(overrides)
    return value


class StubService:
    def __init__(self):
        self.arguments = None
        self.error = None
        self.list_result = PipelineListResponse(
            items=[PipelineListItem.model_validate(pipeline_item())],
            pagination=PaginationMetadata(limit=50, offset=0, total=1, returned_count=1),
        )
        self.detail_result = PipelineDetail.model_validate({
            **pipeline_item(), "airflow_dag_id": "corvetra_demo__events_processing",
            "recent_runs": [pipeline_item()["latest_run"]],
            "validation_summary": {"total": 0, "passed": 0, "failed": 0,
                "not_evaluated": 0, "blocking_failed": 0, "warning_failed": 0,
                "last_evaluated_at": None},
            "active_alerts": [pipeline_item()["current_issue"]],
            "technical_evidence_count": 5,
        })

    async def list_pipelines(self, **arguments):
        self.arguments = arguments
        if self.error:
            raise self.error
        return self.list_result

    async def get_pipeline(self, key):
        self.arguments = key
        if self.error:
            raise self.error
        return self.detail_result


class StubRepository:
    def __init__(self, row=None):
        self.row = row

    async def get_pipeline(self, key):
        return self.row


class PipelineApiTests(unittest.TestCase):
    def setUp(self):
        self.service = StubService()
        app.dependency_overrides[get_pipeline_service] = lambda: self.service
        app.dependency_overrides[get_current_active_user] = lambda: ACTIVE_TEST_USER
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.client.close()

    def test_list_is_first_class_pipeline_and_defaults(self):
        response = self.client.get("/api/v1/pipelines")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["items"][0]["pipeline_key"], "events-processing")
        self.assertNotIn("pipeline_run_id", response.json()["items"][0])
        self.assertEqual(self.service.arguments["limit"], 50)

    def test_filters_and_pagination(self):
        response = self.client.get(
            "/api/v1/pipelines?environment=production&operational_status=FAILED"
            "&source=events-kafka&enabled=true&search=Events&limit=10&offset=2"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.service.arguments["filters"], PipelineFilters(
            environment="production", operational_status="FAILED",
            source="events-kafka", enabled=True, search="Events",
        ))
        self.assertEqual((self.service.arguments["limit"], self.service.arguments["offset"]), (10, 2))

    def test_invalid_filter_pagination_and_identifier_are_422(self):
        for path in (
            "/api/v1/pipelines?operational_status=BROKEN",
            "/api/v1/pipelines?limit=101",
            "/api/v1/pipelines?search=",
            "/api/v1/pipelines/Not_Valid",
        ):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 422)

    def test_detail_and_exact_404(self):
        response = self.client.get("/api/v1/pipelines/events-processing")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["technical_evidence_count"], 5)
        self.service.error = PipelineNotFoundError()
        response = self.client.get("/api/v1/pipelines/missing")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "Pipeline not found"})

    def test_database_failure_is_sanitized(self):
        self.service.error = RuntimeError("postgresql://user:secret@database")
        response = self.client.get("/api/v1/pipelines")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"detail": "Database unavailable"})
        self.assertNotIn("secret", response.text)

    def test_models_forbid_extra_and_control_status(self):
        with self.assertRaises(ValidationError):
            PipelineListItem.model_validate({**pipeline_item(), "schedule": "daily"})
        with self.assertRaises(ValidationError):
            PipelineListItem.model_validate(pipeline_item(operational_status="BROKEN"))

    def test_literal_search_escaping(self):
        self.assertEqual(escape_like(r"a%b_c\d"), r"a\%b\_c\\d")


class PipelineServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_unknown_pipeline_raises_not_found(self):
        with self.assertRaises(PipelineNotFoundError):
            await PipelineService(StubRepository()).get_pipeline("missing")


if __name__ == "__main__":
    unittest.main()
