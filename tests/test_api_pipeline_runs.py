import sys
import os
import unittest
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from fastapi.testclient import TestClient
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "platform"))

from api.auth_dependencies import get_current_active_user  # noqa: E402
from api.main import app  # noqa: E402
from api.repositories.pipeline_runs import PipelineRunFilters, PipelineRunRepository  # noqa: E402
from api.routes.pipeline_runs import get_pipeline_run_service  # noqa: E402
from api.schemas.core_resources import PaginationMetadata  # noqa: E402
from api.schemas.pipeline_runs import PipelineRunDetail, PipelineRunListItem, PipelineRunListResponse  # noqa: E402
from api.services.pipeline_runs import PipelineRunNotFoundError  # noqa: E402
from tests.api_auth_test_helpers import ACTIVE_TEST_USER  # noqa: E402

NOW = datetime(2026, 8, 10, 13, 28, tzinfo=timezone.utc)
RUN_UUID = UUID("3807f462-fee5-520a-8b10-8a1afa657fc2")


def run_item(**overrides):
    value = {
        "corvetra_run_id": "run_01J97BIL02",
        "pipeline": {"pipeline_key": "billing-reconciliation", "name": "Billing Reconciliation", "operational_status": "WARNING"},
        "source": {"source_key": "billing-postgres", "name": "Billing PostgreSQL", "source_type": "POSTGRESQL", "operational_status": "WARNING"},
        "environment": {"environment_key": "production", "name": "Production"},
        "status": "FAILED", "stage": "VALIDATE", "started_at": NOW,
        "completed_at": NOW, "duration_seconds": 0.0,
        "platform_code": "VALIDATION_CHECK_FAILED", "vendor_code": None,
        "rule_code": "CHECK_UNIQUENESS_VIOLATION", "active_alert_count": 1,
    }
    value.update(overrides)
    return value


def alert():
    return {
        "alert_key": "ALT-1040", "title": "Order ID unique failed",
        "severity": "WARNING", "status": "OPEN",
        "platform_code": "VALIDATION_CHECK_FAILED", "vendor_code": None,
        "rule_code": "CHECK_UNIQUENESS_VIOLATION", "message": "duplicates",
        "detected_at": NOW, "last_seen_at": NOW,
        "acknowledged_at": None, "resolved_at": None,
    }


def validation():
    return {
        "check_key": "order-id-unique", "name": "Order ID unique", "type": "UNIQUE",
        "dataset_name": "orders", "column_name": "order_id", "result": "FAILED",
        "severity": "BLOCKING", "platform_code": "VALIDATION_CHECK_FAILED",
        "rule_code": "CHECK_UNIQUENESS_VIOLATION", "vendor_code": None,
        "actual": "318 duplicates", "expected": "0 duplicates",
        "message": "318 duplicate order_id values were detected.", "evaluated_at": NOW,
    }


class StubService:
    def __init__(self):
        self.arguments = None
        self.error = None
        self.list_result = PipelineRunListResponse(
            items=[PipelineRunListItem.model_validate(run_item())],
            pagination=PaginationMetadata(limit=50, offset=0, total=5, returned_count=1),
        )
        self.detail_result = PipelineRunDetail.model_validate({
            **run_item(), "airflow": {"dag_id": "corvetra_demo__billing_reconciliation", "airflow_run_id": "corvetra_seed__run_01J97BIL02"},
            "alerts": [alert()],
            "validation_summary": {"total": 2, "passed": 1, "failed": 1,
                "not_evaluated": 0, "blocking_failed": 1, "warning_failed": 0,
                "last_evaluated_at": NOW},
            "validation_executions": [validation()], "technical_evidence_count": 1,
            "technical_evidence": [{"event_key": "evt-007", "occurred_at": NOW,
                "level": "ERROR", "stage": "VALIDATE", "platform_code": "VALIDATION_CHECK_FAILED",
                "vendor_code": None, "rule_code": "CHECK_UNIQUENESS_VIOLATION", "message": "duplicates"}],
        })

    async def list_pipeline_runs(self, **arguments):
        self.arguments = arguments
        if self.error:
            raise self.error
        return self.list_result

    async def get_pipeline_run(self, key):
        if self.error:
            raise self.error
        return self.detail_result


class RecordingResult:
    async def fetchone(self):
        return (0,)


class RecordingCursor:
    def __init__(self, connection): self.connection = connection
    async def __aenter__(self): return self
    async def __aexit__(self, *args): return False
    async def execute(self, query, parameters):
        self.connection.query = query
        self.connection.parameters = parameters
    async def fetchall(self): return []


class RecordingConnection:
    async def execute(self, query, parameters):
        self.count_query, self.count_parameters = query, parameters
        return RecordingResult()
    def cursor(self, row_factory=None): return RecordingCursor(self)


class Context:
    def __init__(self, value): self.value = value
    async def __aenter__(self): return self.value
    async def __aexit__(self, *args): return False


class RecordingPool:
    def __init__(self): self.connection_instance = RecordingConnection()
    def connection(self): return Context(self.connection_instance)


class PipelineRunApiTests(unittest.TestCase):
    def setUp(self):
        self.service = StubService()
        app.dependency_overrides[get_pipeline_run_service] = lambda: self.service
        app.dependency_overrides[get_current_active_user] = lambda: ACTIVE_TEST_USER
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.client.close()

    def test_list_all_filters_and_canonical_only_contract(self):
        path = ("/api/v1/pipeline-runs?pipeline=billing-reconciliation&environment=production"
                "&status=FAILED&stage=VALIDATE&source=billing-postgres"
                "&started_from=2026-08-10T00:00:00Z&started_to=2026-08-11T00:00:00Z"
                "&search=Billing&limit=5&offset=1")
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["items"][0]["corvetra_run_id"], "run_01J97BIL02")
        filters = self.service.arguments["filters"]
        self.assertEqual((filters.pipeline, filters.environment, filters.status, filters.stage, filters.source),
                         ("billing-reconciliation", "production", "FAILED", "VALIDATE", "billing-postgres"))
        self.assertIsNotNone(filters.started_from.tzinfo)

    def test_billing_detail_story(self):
        response = self.client.get("/api/v1/pipeline-runs/run_01J97BIL02")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["alerts"][0]["alert_key"], "ALT-1040")
        self.assertEqual(body["validation_executions"][0]["actual"], "318 duplicates")
        self.assertEqual(body["validation_executions"][0]["expected"], "0 duplicates")
        self.assertEqual(body["technical_evidence"][0]["event_key"], "evt-007")

    def test_invalid_filter_identifier_timezone_and_range_are_422(self):
        for path in (
            "/api/v1/pipeline-runs?status=UNKNOWN",
            "/api/v1/pipeline-runs?stage=UNKNOWN",
            "/api/v1/pipeline-runs?started_from=2026-08-10T00:00:00",
            "/api/v1/pipeline-runs?started_from=2026-08-11T00:00:00Z&started_to=2026-08-10T00:00:00Z",
            "/api/v1/pipeline-runs/3807f462-fee5-520a-8b10-8a1afa657fc2",
        ):
            with self.subTest(path=path): self.assertEqual(self.client.get(path).status_code, 422)

    def test_exact_404_and_sanitized_503(self):
        self.service.error = PipelineRunNotFoundError()
        response = self.client.get("/api/v1/pipeline-runs/run_MISSING")
        self.assertEqual(response.json(), {"detail": "Pipeline run not found"})
        self.service.error = RuntimeError("postgres secret")
        response = self.client.get("/api/v1/pipeline-runs")
        self.assertEqual(response.json(), {"detail": "Database unavailable"})
        self.assertNotIn("secret", response.text)

    def test_schema_is_strict(self):
        with self.assertRaises(ValidationError):
            PipelineRunListItem.model_validate({**run_item(), "pipeline_run_id": RUN_UUID})


class PipelineRunRepositoryTests(unittest.IsolatedAsyncioTestCase):
    async def test_queries_require_canonical_ids_are_parameterized_and_ordered(self):
        pool = RecordingPool()
        filters = PipelineRunFilters(pipeline="billing-reconciliation", search="%_")
        await PipelineRunRepository(pool).list_pipeline_runs(limit=10, offset=20, filters=filters)
        connection = pool.connection_instance
        self.assertIn("r.corvetra_run_id IS NOT NULL", connection.count_query)
        self.assertIn("ORDER BY r.started_at DESC, r.pipeline_run_id DESC", connection.query)
        self.assertNotIn("billing-reconciliation", connection.query)
        self.assertEqual(connection.count_parameters, ["billing-reconciliation", r"%\%\_%", r"%\%\_%"])
        self.assertEqual(connection.parameters[-2:], [10, 20])


@unittest.skipUnless(
    os.getenv("RUN_CORE_API_INTEGRATION") == "1",
    "Set RUN_CORE_API_INTEGRATION=1 to run live core-resource API tests",
)
class CoreResourceApiIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.dependency_overrides[get_current_active_user] = lambda: ACTIVE_TEST_USER
        cls.client = TestClient(app)
        cls.client.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.client.__exit__(None, None, None)
        app.dependency_overrides.clear()

    def test_canonical_counts_statuses_and_legacy_omission(self):
        sources = self.client.get("/api/v1/data-sources")
        pipelines = self.client.get("/api/v1/pipelines")
        runs = self.client.get("/api/v1/pipeline-runs")
        self.assertEqual((sources.status_code, pipelines.status_code, runs.status_code), (200, 200, 200))
        self.assertEqual(sources.json()["pagination"]["total"], 4)
        self.assertEqual(runs.json()["pagination"]["total"], 5)
        self.assertTrue(all(item["corvetra_run_id"] for item in runs.json()["items"]))
        by_run_id = {item["corvetra_run_id"]: item for item in runs.json()["items"]}
        self.assertEqual(set(by_run_id), {
            "run_01J94EVT18", "run_01J97BIL02", "run_01J92CING8",
            "run_01J92CVAL9", "run_01JA7OLD40",
        })
        self.assertEqual((by_run_id["run_01J92CING8"]["status"], by_run_id["run_01J92CING8"]["stage"]), ("SUCCESS", "LOAD"))
        self.assertEqual(by_run_id["run_01J92CVAL9"]["rule_code"], "CHECK_NULL_RATE_THRESHOLD")
        self.assertEqual((by_run_id["run_01JA7OLD40"]["status"], by_run_id["run_01JA7OLD40"]["stage"]), ("FAILED", "EXTRACT"))
        statuses = {item["name"]: item["operational_status"] for item in pipelines.json()["items"]}
        self.assertEqual(statuses, {
            "Billing Reconciliation": "WARNING",
            "Customer Ingestion": "HEALTHY",
            "Events Processing": "FAILED",
        })

    def test_events_and_billing_details(self):
        source = self.client.get("/api/v1/data-sources/events-kafka")
        pipeline = self.client.get("/api/v1/pipelines/billing-reconciliation")
        events = self.client.get("/api/v1/pipeline-runs/run_01J94EVT18")
        billing = self.client.get("/api/v1/pipeline-runs/run_01J97BIL02")
        self.assertEqual(
            (source.status_code, pipeline.status_code, events.status_code, billing.status_code),
            (200, 200, 200, 200),
        )
        self.assertEqual(source.json()["connected_pipelines"][0]["operational_status"], "FAILED")
        self.assertEqual(len(source.json()["recent_evidence"]), 5)
        self.assertEqual(pipeline.json()["operational_status"], "WARNING")
        self.assertEqual(pipeline.json()["active_alerts"][0]["alert_key"], "ALT-1040")
        events_body = events.json()
        self.assertEqual(events_body["source"]["name"], "Events Kafka")
        self.assertEqual(events_body["alerts"][0]["alert_key"], "ALT-1042")
        self.assertEqual(events_body["technical_evidence_count"], 5)
        self.assertEqual(len(events_body["technical_evidence"]), 5)
        self.assertEqual(
            [item["occurred_at"] for item in events_body["technical_evidence"]],
            sorted(item["occurred_at"] for item in events_body["technical_evidence"]),
        )
        billing_body = billing.json()
        execution = next(item for item in billing_body["validation_executions"] if item["check_key"] == "order-id-unique")
        self.assertEqual((execution["result"], execution["severity"]), ("FAILED", "BLOCKING"))
        self.assertEqual((execution["actual"], execution["expected"]), ("318 duplicates", "0 duplicates"))
        self.assertEqual(billing_body["alerts"][0]["alert_key"], "ALT-1040")
        self.assertEqual(billing_body["technical_evidence"][0]["event_key"], "evt-007")


if __name__ == "__main__":
    unittest.main()
