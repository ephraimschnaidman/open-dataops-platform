import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "platform"))

from api.auth_dependencies import get_current_active_user  # noqa: E402
from api.main import app  # noqa: E402
from api.repositories.data_sources import DataSourceFilters  # noqa: E402
from api.routes.data_sources import get_data_source_service  # noqa: E402
from api.schemas.core_resources import PaginationMetadata  # noqa: E402
from api.schemas.data_sources import DataSourceDetail, DataSourceListItem, DataSourceListResponse  # noqa: E402
from api.services.data_sources import DataSourceNotFoundError  # noqa: E402
from tests.api_auth_test_helpers import ACTIVE_TEST_USER  # noqa: E402

NOW = datetime(2026, 8, 10, 14, 42, tzinfo=timezone.utc)


def source_item(**overrides):
    value = {
        "source_key": "events-kafka", "name": "Events Kafka", "source_type": "KAFKA",
        "environment": {"environment_key": "production", "name": "Production"},
        "operational_status": "DISCONNECTED", "connected_pipeline_count": 1,
        "last_observed_at": NOW,
    }
    value.update(overrides)
    return value


class StubService:
    def __init__(self):
        self.arguments = None
        self.error = None
        self.list_result = DataSourceListResponse(
            items=[DataSourceListItem.model_validate(source_item())],
            pagination=PaginationMetadata(limit=50, offset=0, total=1, returned_count=1),
        )
        self.detail_result = DataSourceDetail.model_validate({
            **source_item(),
            "connected_pipelines": [{
                "pipeline_key": "events-processing", "name": "Events Processing",
                "is_enabled": True, "operational_status": "FAILED", "latest_run": None,
            }],
            "validation_summary": {"total": 0, "passed": 0, "failed": 0,
                "not_evaluated": 0, "blocking_failed": 0, "warning_failed": 0,
                "last_evaluated_at": None},
            "active_alert_count": 1, "recent_evidence": [],
        })

    async def list_data_sources(self, **arguments):
        self.arguments = arguments
        if self.error:
            raise self.error
        return self.list_result

    async def get_data_source(self, key):
        if self.error:
            raise self.error
        return self.detail_result


class DataSourceApiTests(unittest.TestCase):
    def setUp(self):
        self.service = StubService()
        app.dependency_overrides[get_data_source_service] = lambda: self.service
        app.dependency_overrides[get_current_active_user] = lambda: ACTIVE_TEST_USER
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.client.close()

    def test_list_and_all_filters(self):
        response = self.client.get(
            "/api/v1/data-sources?environment=production&operational_status=DISCONNECTED"
            "&source_type=KAFKA&search=Events&limit=5&offset=1"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["items"][0]["name"], "Events Kafka")
        self.assertEqual(self.service.arguments["filters"], DataSourceFilters(
            environment="production", operational_status="DISCONNECTED",
            source_type="KAFKA", search="Events",
        ))

    def test_detail_404_validation_and_sanitized_503(self):
        self.assertEqual(self.client.get("/api/v1/data-sources/events-kafka").status_code, 200)
        self.service.error = DataSourceNotFoundError()
        response = self.client.get("/api/v1/data-sources/missing")
        self.assertEqual(response.json(), {"detail": "Data source not found"})
        self.service.error = RuntimeError("secret")
        response = self.client.get("/api/v1/data-sources")
        self.assertEqual(response.json(), {"detail": "Database unavailable"})
        self.assertNotIn("secret", response.text)

    def test_invalid_values_and_identifier_are_422(self):
        for path in (
            "/api/v1/data-sources?source_type=MYSQL",
            "/api/v1/data-sources?operational_status=BROKEN",
            "/api/v1/data-sources?offset=-1",
            "/api/v1/data-sources/Bad_Key",
        ):
            self.assertEqual(self.client.get(path).status_code, 422)

    def test_schema_forbids_sensitive_extra_fields(self):
        with self.assertRaises(ValidationError):
            DataSourceListItem.model_validate({**source_item(), "connection_string": "secret"})


if __name__ == "__main__":
    unittest.main()
