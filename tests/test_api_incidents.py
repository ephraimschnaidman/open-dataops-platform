import sys
import unittest
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "platform"))

from api.main import app  # noqa: E402
from api.repositories.incidents import IncidentFilters  # noqa: E402
from api.routes.incidents import get_incident_service  # noqa: E402
from api.schemas.incidents import (  # noqa: E402
    IncidentContextResponse,
    IncidentDetailResponse,
    IncidentListResponse,
    IncidentResponse,
    PaginationMetadata,
)
from api.services.incidents import (  # noqa: E402
    IncidentNotFoundError,
    IncidentService,
)

INCIDENT_ID = UUID("11111111-1111-4111-8111-111111111111")
PIPELINE_RUN_ID = UUID("22222222-2222-4222-8222-222222222222")
CONTEXT_ID = UUID("33333333-3333-4333-8333-333333333333")
NOW = datetime(2026, 7, 28, 12, 0, tzinfo=timezone.utc)


def incident_data(**overrides):
    values = {
        "incident_id": INCIDENT_ID,
        "pipeline_run_id": PIPELINE_RUN_ID,
        "incident_type": "STALE_DATA",
        "severity": "HIGH",
        "table_schema": "raw",
        "table_name": "orders",
        "column_name": "created_at",
        "expected_value": "<= 24 hours",
        "observed_value": "30 hours",
        "incident_message": "Data is stale",
        "incident_status": "OPEN",
        "detected_at": NOW,
        "resolved_at": None,
        "created_at": NOW,
        "updated_at": NOW,
    }
    values.update(overrides)
    return values


def context_data():
    return {
        "context_id": CONTEXT_ID,
        "incident_id": INCIDENT_ID,
        "context_version": "stale_data_v1",
        "qualified_table": "raw.orders",
        "evaluation_status": "EXCEEDED_THRESHOLD",
        "severity": "HIGH",
        "expected_freshness_hours": Decimal("24"),
        "observed_freshness_hours": Decimal("30"),
        "recommended_action_code": (
            "INVESTIGATE_UPSTREAM_INGESTION_AND_VERIFY_THRESHOLD"
        ),
        "generated_at": NOW,
        "created_at": NOW,
        "updated_at": NOW,
        "change_type": None,
        "affected_column": None,
    }


class StubIncidentService:
    def __init__(self):
        self.list_result = IncidentListResponse(
            items=[IncidentResponse(**incident_data())],
            pagination=PaginationMetadata(
                limit=50,
                offset=0,
                total=1,
                returned_count=1,
            ),
        )
        self.detail_result = IncidentDetailResponse(
            **incident_data(),
            incident_context=None,
        )
        self.list_error = None
        self.detail_error = None
        self.list_arguments = None

    async def list_incidents(self, **arguments):
        self.list_arguments = arguments
        if self.list_error:
            raise self.list_error
        return self.list_result

    async def get_incident(self, incident_id):
        if self.detail_error:
            raise self.detail_error
        return self.detail_result


class StubIncidentRepository:
    def __init__(self, incident=None, context=None, rows=None, total=0):
        self.incident = incident
        self.context = context
        self.rows = [] if rows is None else rows
        self.total = total
        self.list_arguments = None

    async def list_incidents(self, **arguments):
        self.list_arguments = arguments
        return self.rows, self.total

    async def get_incident(self, incident_id):
        return self.incident

    async def get_incident_context(self, incident_id):
        return self.context


class IncidentApiRouteTests(unittest.TestCase):
    def setUp(self):
        self.service = StubIncidentService()
        app.dependency_overrides[get_incident_service] = lambda: self.service
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.client.close()

    def test_incident_list_success(self):
        response = self.client.get("/api/v1/incidents")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["items"][0]["incident_id"], str(INCIDENT_ID))

    def test_incident_list_empty_result(self):
        self.service.list_result = IncidentListResponse(
            items=[],
            pagination=PaginationMetadata(
                limit=50,
                offset=0,
                total=0,
                returned_count=0,
            ),
        )

        response = self.client.get("/api/v1/incidents")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["items"], [])
        self.assertEqual(response.json()["pagination"]["total"], 0)

    def test_pagination_parameters_are_passed_to_service(self):
        response = self.client.get("/api/v1/incidents?limit=25&offset=50")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.service.list_arguments["limit"], 25)
        self.assertEqual(self.service.list_arguments["offset"], 50)

    def test_supported_filters_are_passed_to_service(self):
        query = (
            "?incident_status=OPEN&severity=HIGH&incident_type=STALE_DATA"
            "&table_schema=raw&table_name=orders"
            f"&pipeline_run_id={PIPELINE_RUN_ID}"
        )

        response = self.client.get(f"/api/v1/incidents{query}")

        filters = self.service.list_arguments["filters"]
        self.assertEqual(response.status_code, 200)
        self.assertEqual(filters.incident_status, "OPEN")
        self.assertEqual(filters.severity, "HIGH")
        self.assertEqual(filters.incident_type, "STALE_DATA")
        self.assertEqual(filters.table_schema, "raw")
        self.assertEqual(filters.table_name, "orders")
        self.assertEqual(filters.pipeline_run_id, PIPELINE_RUN_ID)

    def test_invalid_limit_returns_422(self):
        for limit in ("0", "101"):
            with self.subTest(limit=limit):
                response = self.client.get(f"/api/v1/incidents?limit={limit}")
                self.assertEqual(response.status_code, 422)

    def test_invalid_offset_returns_422(self):
        response = self.client.get("/api/v1/incidents?offset=-1")

        self.assertEqual(response.status_code, 422)

    def test_incident_detail_success_without_context(self):
        response = self.client.get(f"/api/v1/incidents/{INCIDENT_ID}")

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["incident_context"])

    def test_incident_detail_success_with_context(self):
        self.service.detail_result = IncidentDetailResponse(
            **incident_data(),
            incident_context=IncidentContextResponse(**context_data()),
        )

        response = self.client.get(f"/api/v1/incidents/{INCIDENT_ID}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["incident_context"]["context_id"],
            str(CONTEXT_ID),
        )

    def test_nonexistent_incident_returns_safe_404(self):
        self.service.detail_error = IncidentNotFoundError()

        response = self.client.get(f"/api/v1/incidents/{INCIDENT_ID}")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "Incident not found"})

    def test_invalid_incident_uuid_returns_422(self):
        response = self.client.get("/api/v1/incidents/not-a-uuid")

        self.assertEqual(response.status_code, 422)

    def test_database_errors_return_safe_503(self):
        self.service.list_error = RuntimeError("SELECT secret FROM hidden")

        response = self.client.get("/api/v1/incidents")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"detail": "Database unavailable"})
        self.assertNotIn("SELECT", response.text)


class IncidentServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_list_builds_pagination_from_repository_result(self):
        repository = StubIncidentRepository(
            rows=[incident_data()],
            total=7,
        )
        service = IncidentService(repository)

        result = await service.list_incidents(
            limit=2,
            offset=4,
            filters=IncidentFilters(severity="HIGH"),
        )

        self.assertEqual(len(result.items), 1)
        self.assertEqual(result.pagination.limit, 2)
        self.assertEqual(result.pagination.offset, 4)
        self.assertEqual(result.pagination.total, 7)
        self.assertEqual(result.pagination.returned_count, 1)

    async def test_detail_composes_matching_context(self):
        service = IncidentService(
            StubIncidentRepository(
                incident=incident_data(),
                context=context_data(),
            )
        )

        result = await service.get_incident(INCIDENT_ID)

        self.assertIsNotNone(result.incident_context)
        self.assertEqual(result.incident_context.context_id, CONTEXT_ID)

    async def test_detail_without_context_is_valid(self):
        service = IncidentService(
            StubIncidentRepository(incident=incident_data(), context=None)
        )

        result = await service.get_incident(INCIDENT_ID)

        self.assertIsNone(result.incident_context)


if __name__ == "__main__":
    unittest.main()
