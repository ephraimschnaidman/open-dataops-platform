import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "platform"))

from api.auth_dependencies import get_current_active_user  # noqa: E402
from api.dependencies import get_pipeline_operations_service  # noqa: E402
from api.main import app  # noqa: E402
from api.orchestrators.base import (  # noqa: E402
    OrchestratorConflictError, OrchestratorInvalidResponseError,
    OrchestratorNotFoundError, OrchestratorOperationUnsupportedError,
    OrchestratorUnavailableError,
)
from api.orchestrators.models import (  # noqa: E402
    Dag, DagPage, DagRun, DagRunPage, Pagination, TaskInstance,
    TaskInstancePage, TaskLog, WorkflowOperation,
)
from api.schemas.auth import CurrentUser  # noqa: E402

NOW = datetime(2026, 8, 1, tzinfo=timezone.utc)


def user(*roles):
    return CurrentUser(
        user_id=UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
        username="operations.test", is_active=True, roles=list(roles)
    )


class StubService:
    def __init__(self):
        self.error = None
        self.arguments = None
        self.dag = Dag(
            dag_id="ecommerce_pipeline", display_name="Ecommerce Pipeline",
            description="Demo", is_active=True, is_paused=False,
            owners=("platform",), tags=("ecommerce",),
        )
        self.run = DagRun(
            dag_id="ecommerce_pipeline", run_id="scheduled/run", state="success",
            logical_date=NOW, start_date=NOW, end_date=NOW,
            data_interval_start=NOW, data_interval_end=NOW,
            run_type="scheduled", externally_triggered=False,
        )
        self.task = TaskInstance(
            dag_id="ecommerce_pipeline", run_id="scheduled/run", task_id="load",
            state="success", try_number=1, map_index=-1,
        )
        self.write_calls = 0

    async def trigger_workflow(self, **kwargs):
        self.write_calls += 1
        run_id = kwargs["run_id"] or "platform__manual__generated"
        return self._result(WorkflowOperation(
            operation_id=run_id,
            dag_id=kwargs["dag_id"],
            run_id=run_id,
            state="queued",
            logical_date=kwargs["logical_date"],
            externally_triggered=True,
        ), kwargs)

    async def retry_run(self, **kwargs):
        self.write_calls += 1
        return self._result(None, kwargs)

    async def cancel_run(self, **kwargs):
        self.write_calls += 1
        return self._result(None, kwargs)

    def _result(self, result, arguments):
        self.arguments = arguments
        if self.error:
            raise self.error
        return result

    async def list_dags(self, **kwargs):
        return self._result(DagPage(
            items=(self.dag,), pagination=Pagination(
                limit=kwargs["limit"], offset=kwargs["offset"], total=1,
                returned_count=1,
            )), kwargs)

    async def get_dag(self, dag_id):
        return self._result(self.dag, {"dag_id": dag_id})

    async def list_dag_runs(self, **kwargs):
        return self._result(DagRunPage(
            items=(self.run,), pagination=Pagination(
                limit=kwargs["limit"], offset=kwargs["offset"], total=1,
                returned_count=1,
            )), kwargs)

    async def get_dag_run(self, **kwargs):
        return self._result(self.run, kwargs)

    async def list_task_instances(self, **kwargs):
        return self._result(TaskInstancePage(
            items=(self.task,), pagination=Pagination(
                limit=kwargs["limit"], offset=kwargs["offset"], total=1,
                returned_count=1,
            )), kwargs)

    async def get_task_log(self, **kwargs):
        return self._result(TaskLog(content="hello", **kwargs), kwargs)


class OperationsRouteTests(unittest.TestCase):
    def setUp(self):
        self.service = StubService()
        app.state.database_pool = None
        app.dependency_overrides[get_pipeline_operations_service] = lambda: self.service
        app.dependency_overrides[get_current_active_user] = lambda: user("ReadOnly")
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.client.close()

    def test_all_six_endpoints_and_public_schemas(self):
        paths = (
            "/api/v1/operations/dags",
            "/api/v1/operations/dags/ecommerce_pipeline",
            "/api/v1/operations/runs",
            "/api/v1/operations/dags/ecommerce_pipeline/runs/scheduled__run",
            "/api/v1/operations/dags/ecommerce_pipeline/runs/scheduled__run/tasks",
            "/api/v1/operations/dags/ecommerce_pipeline/runs/scheduled__run/tasks/load/logs",
        )
        for path in paths:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200, response.text)
                self.assertNotIn("hostname", response.text)
                self.assertNotIn("conf", response.text)

    def test_pagination_filters_and_log_coordinates(self):
        response = self.client.get(
            "/api/v1/operations/dags?limit=25&offset=50&paused=false&active=true&tag=x"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.service.arguments["limit"], 25)
        self.assertEqual(self.service.arguments["tag"], "x")
        response = self.client.get(
            "/api/v1/operations/dags/d/runs/r/tasks/t/logs?try_number=2&map_index=4"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.service.arguments["try_number"], 2)
        self.assertEqual(self.service.arguments["map_index"], 4)

    def test_invalid_queries_return_422(self):
        paths = (
            "/api/v1/operations/dags?limit=0",
            "/api/v1/operations/runs?offset=-1",
            "/api/v1/operations/dags/d/runs/r/tasks/t/logs?try_number=0",
            "/api/v1/operations/dags/d/runs/r/tasks/t/logs?map_index=-2",
            "/api/v1/operations/runs?start_date_gte=2026-08-02T00:00:00Z&start_date_lte=2026-08-01T00:00:00Z",
        )
        for path in paths:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 422)

    def test_rbac_anonymous_allowed_roles_and_no_role(self):
        app.dependency_overrides.pop(get_current_active_user)
        response = self.client.get("/api/v1/operations/dags")
        self.assertEqual(response.status_code, 401)
        for role in ("Admin", "Operator", "ReadOnly"):
            with self.subTest(role=role):
                app.dependency_overrides[get_current_active_user] = lambda role=role: user(role)
                self.assertEqual(self.client.get("/api/v1/operations/dags").status_code, 200)
        app.dependency_overrides[get_current_active_user] = lambda: user()
        self.assertEqual(self.client.get("/api/v1/operations/dags").status_code, 403)

    def test_safe_error_translation(self):
        cases = (
            (OrchestratorNotFoundError("secret"), 404, "Pipeline resource not found"),
            (OrchestratorUnavailableError("secret"), 503, "Pipeline service unavailable"),
            (OrchestratorInvalidResponseError("secret"), 503, "Pipeline service unavailable"),
        )
        for error, code, detail in cases:
            with self.subTest(error=type(error).__name__):
                self.service.error = error
                response = self.client.get("/api/v1/operations/dags/missing")
                self.assertEqual(response.status_code, code)
                self.assertEqual(response.json(), {"detail": detail})
                self.assertNotIn("secret", response.text)

    def test_openapi_declares_security_and_no_ambiguous_run_route(self):
        schema = app.openapi()
        operation = schema["paths"]["/api/v1/operations/dags"]["get"]
        self.assertEqual(operation["security"], [{"OAuth2PasswordBearer": []}])
        self.assertNotIn("/api/v1/operations/runs/{run_id}", schema["paths"])

    def test_admin_and_operator_can_trigger_with_safe_neutral_contract(self):
        for role in ("Admin", "Operator"):
            with self.subTest(role=role):
                app.dependency_overrides[get_current_active_user] = lambda role=role: user(role)
                response = self.client.post(
                    "/api/v1/operations/dags/ecommerce_pipeline/trigger",
                    json={
                        "run_id": "caller-run",
                        "logical_date": "2026-08-01T00:00:00Z",
                        "conf": {"region": "us"},
                    },
                )
                self.assertEqual(response.status_code, 201, response.text)
                self.assertEqual(response.json()["operation_id"], "caller-run")
                self.assertEqual(self.service.arguments["conf"], {"region": "us"})
                self.assertNotIn("conf", response.json())

    def test_write_rbac_blocks_before_service_execution(self):
        paths = (
            "/api/v1/operations/dags/d/trigger",
            "/api/v1/operations/dags/d/runs/r/retry",
            "/api/v1/operations/dags/d/runs/r/cancel",
        )
        for path in paths:
            with self.subTest(path=path, role="ReadOnly"):
                response = self.client.post(path, json={} if path.endswith("trigger") else None)
                self.assertEqual(response.status_code, 403)
                self.assertEqual(response.json(), {"detail": "Insufficient permissions"})
            with self.subTest(path=path, role="anonymous"):
                app.dependency_overrides.pop(get_current_active_user, None)
                response = self.client.post(path, json={} if path.endswith("trigger") else None)
                self.assertEqual(response.status_code, 401)
            app.dependency_overrides[get_current_active_user] = lambda: user("ReadOnly")
        self.assertEqual(self.service.write_calls, 0)

    def test_trigger_validation_and_safe_error_mappings(self):
        app.dependency_overrides[get_current_active_user] = lambda: user("Operator")
        invalid = self.client.post(
            "/api/v1/operations/dags/d/trigger", json={"run_id": ""}
        )
        self.assertEqual(invalid.status_code, 422)
        cases = (
            (OrchestratorNotFoundError("secret"), 404, "Pipeline resource not found"),
            (OrchestratorConflictError("secret"), 409, "Pipeline operation conflict"),
            (OrchestratorUnavailableError("secret"), 503, "Pipeline service unavailable"),
        )
        for error, code, detail in cases:
            with self.subTest(code=code):
                self.service.error = error
                response = self.client.post(
                    "/api/v1/operations/dags/d/trigger", json={}
                )
                self.assertEqual(response.status_code, code)
                self.assertEqual(response.json(), {"detail": detail})

    def test_retry_and_cancel_return_501_for_authorized_writers(self):
        self.service.error = OrchestratorOperationUnsupportedError("not safe")
        for role in ("Admin", "Operator"):
            app.dependency_overrides[get_current_active_user] = lambda role=role: user(role)
            for operation in ("retry", "cancel"):
                response = self.client.post(
                    f"/api/v1/operations/dags/d/runs/r/{operation}"
                )
                self.assertEqual(response.status_code, 501)
                self.assertEqual(
                    response.json(), {"detail": "Pipeline operation not supported"}
                )

    def test_write_openapi_security_request_and_response_schemas(self):
        schema = app.openapi()
        trigger = schema["paths"]["/api/v1/operations/dags/{dag_id}/trigger"]["post"]
        self.assertEqual(trigger["security"], [{"OAuth2PasswordBearer": []}])
        request_ref = trigger["requestBody"]["content"]["application/json"]["schema"]["$ref"]
        request_schema = schema["components"]["schemas"][request_ref.rsplit("/", 1)[-1]]
        self.assertEqual(
            set(request_schema["properties"]), {"run_id", "logical_date", "conf"}
        )
        response_ref = trigger["responses"]["201"]["content"]["application/json"]["schema"]["$ref"]
        response_schema = schema["components"]["schemas"][response_ref.rsplit("/", 1)[-1]]
        self.assertIn("operation_id", response_schema["properties"])


if __name__ == "__main__":
    unittest.main()
