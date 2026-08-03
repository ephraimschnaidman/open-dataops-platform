import asyncio
import base64
import logging
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "platform"))

from api.config import Settings  # noqa: E402
from api.orchestrators.airflow import (  # noqa: E402
    AIRFLOW_TIMEOUT,
    AirflowClient,
    create_airflow_http_client,
)
from api.orchestrators.base import (  # noqa: E402
    OrchestratorAuthenticationError,
    OrchestratorConflictError,
    OrchestratorInvalidResponseError,
    OrchestratorNotFoundError,
    OrchestratorPermissionError,
    OrchestratorUnavailableError,
)
from api.orchestrators.models import (  # noqa: E402
    Dag, DagPage, DagRunPage, TriggerWorkflowRequest, WorkflowOperation,
)
from api.main import lifespan  # noqa: E402


def make_settings(**overrides):
    values = {
        "jwt_secret_key": "airflow-client-test-secret-longer-than-32-characters",
        "jwt_issuer": "test-issuer",
        "jwt_audience": "test-audience",
        "airflow_api_url": "https://airflow.test/api/v1",
        "airflow_api_username": "api-user",
        "airflow_api_password": "highly-secret-password",
        "airflow_api_verify_tls": True,
    }
    values.update(overrides)
    return Settings(**values)


def dag_payload(**overrides):
    values = {
        "dag_id": "daily_sales",
        "description": "Daily sales pipeline",
        "is_active": True,
        "is_paused": False,
        "owners": ["data-platform"],
        "tags": [{"name": "production"}],
        "fileloc": "/private/airflow/path.py",
    }
    values.update(overrides)
    return values


def run_payload(**overrides):
    values = {
        "dag_id": "daily_sales",
        "dag_run_id": "scheduled__2026-08-01T00:00:00+00:00",
        "state": "success",
        "logical_date": "2026-08-01T00:00:00Z",
        "start_date": "2026-08-01T00:01:00Z",
        "end_date": "2026-08-01T00:02:00Z",
        "conf": {"private": "not exposed"},
    }
    values.update(overrides)
    return values


def task_payload(**overrides):
    values = {
        "dag_id": "daily_sales",
        "dag_run_id": "scheduled/run",
        "task_id": "load/orders",
        "state": "success",
        "try_number": 1,
        "map_index": -1,
        "start_date": "2026-08-01T00:01:00Z",
        "end_date": "2026-08-01T00:02:00Z",
        "duration": 60.0,
        "operator": "PythonOperator",
        "queued_when": "2026-08-01T00:00:30Z",
        "hostname": "internal-worker",
        "executor_config": {"secret": True},
    }
    values.update(overrides)
    return values


class AirflowClientTests(unittest.IsolatedAsyncioTestCase):
    async def asyncTearDown(self):
        client = getattr(self, "http_client", None)
        if client is not None and not client.is_closed:
            await client.aclose()

    def build_client(self, handler, **settings_overrides):
        self.http_client = create_airflow_http_client(
            make_settings(**settings_overrides),
            transport=httpx.MockTransport(handler),
        )
        return AirflowClient(self.http_client)

    async def test_trigger_posts_once_and_maps_neutral_operation(self):
        seen = []

        def handler(request):
            seen.append(request)
            return httpx.Response(
                200,
                json=run_payload(
                    dag_run_id="caller/run",
                    state="queued",
                    external_trigger=True,
                    hostname="private-worker",
                ),
            )

        result = await self.build_client(handler).trigger_workflow(
            dag_id="folder/dag",
            request=TriggerWorkflowRequest(
                run_id="caller/run",
                logical_date="2026-08-01T00:00:00Z",
                conf={"password": "do-not-log"},
            ),
        )
        self.assertEqual(len(seen), 1)
        request = seen[0]
        self.assertEqual(request.method, "POST")
        self.assertIn("folder%2Fdag/dagRuns", str(request.url))
        self.assertEqual(
            request.read().decode(),
            '{"dag_run_id":"caller/run","logical_date":"2026-08-01T00:00:00+00:00","conf":{"password":"do-not-log"}}',
        )
        self.assertIsInstance(result, WorkflowOperation)
        self.assertEqual(result.operation_id, "caller/run")
        self.assertEqual(result.run_id, "caller/run")
        self.assertTrue(result.externally_triggered)
        self.assertFalse(hasattr(result, "conf"))
        self.assertFalse(hasattr(result, "hostname"))

    async def test_trigger_conf_and_unsafe_run_id_do_not_appear_in_logs(self):
        client = self.build_client(
            lambda _: httpx.Response(
                200,
                json=run_payload(
                    dag_run_id="run/with newline\n", state="queued"
                ),
            )
        )
        with self.assertLogs("api.orchestrators.airflow", level=logging.INFO) as captured:
            await client.trigger_workflow(
                dag_id="daily_sales",
                request=TriggerWorkflowRequest(
                    run_id="run/with newline\n", conf={"token": "super-secret-value"}
                ),
            )
        output = " ".join(captured.output)
        self.assertNotIn("super-secret-value", output)
        self.assertNotIn("\n", output)

    async def test_trigger_failures_are_safe_and_never_retried(self):
        cases = (
            (404, OrchestratorNotFoundError),
            (409, OrchestratorConflictError),
            (503, OrchestratorUnavailableError),
        )
        for status_code, expected in cases:
            calls = 0

            def handler(_, code=status_code):
                nonlocal calls
                calls += 1
                return httpx.Response(code, json={"detail": "upstream-secret"})

            with self.subTest(status_code=status_code):
                client = self.build_client(handler)
                with self.assertRaises(expected) as raised:
                    await client.trigger_workflow(
                        dag_id="daily_sales",
                        request=TriggerWorkflowRequest(run_id="caller-run"),
                    )
                self.assertEqual(calls, 1)
                self.assertNotIn("upstream-secret", str(raised.exception))
                await self.http_client.aclose()

    async def test_trigger_timeout_is_safe_and_not_retried(self):
        calls = 0

        def handler(_):
            nonlocal calls
            calls += 1
            raise httpx.ReadTimeout("slow")

        client = self.build_client(handler)
        with self.assertRaises(OrchestratorUnavailableError):
            await client.trigger_workflow(
                dag_id="daily_sales",
                request=TriggerWorkflowRequest(run_id="caller-run"),
            )
        self.assertEqual(calls, 1)

    async def test_list_dags_generates_url_auth_and_neutral_pagination(self):
        seen = {}

        def handler(request):
            seen["request"] = request
            return httpx.Response(
                200,
                json={"dags": [dag_payload()], "total_entries": 7},
            )

        result = await self.build_client(handler).list_dags(limit=25, offset=50)
        request = seen["request"]
        self.assertEqual(
            str(request.url),
            "https://airflow.test/api/v1/dags?limit=25&offset=50",
        )
        expected = base64.b64encode(b"api-user:highly-secret-password").decode()
        self.assertEqual(request.headers["Authorization"], f"Basic {expected}")
        self.assertIsInstance(result, DagPage)
        self.assertIsInstance(result.items[0], Dag)
        self.assertEqual(result.pagination.total, 7)
        self.assertEqual(result.pagination.returned_count, 1)
        self.assertFalse(hasattr(result.items[0], "fileloc"))

    async def test_get_dag_encodes_identifier_and_maps_response(self):
        seen = {}

        def handler(request):
            seen["url"] = str(request.url)
            return httpx.Response(200, json=dag_payload(dag_id="folder/dag"))

        result = await self.build_client(handler).get_dag("folder/dag")
        self.assertEqual(
            seen["url"], "https://airflow.test/api/v1/dags/folder%2Fdag"
        )
        self.assertEqual(result.dag_id, "folder/dag")
        self.assertEqual(result.tags, ("production",))

    async def test_list_dag_runs_maps_names_and_pagination(self):
        def handler(request):
            self.assertEqual(request.url.params["limit"], "10")
            self.assertEqual(request.url.params["offset"], "20")
            return httpx.Response(
                200,
                json={"dag_runs": [run_payload()], "total_entries": 3},
            )

        result = await self.build_client(handler).list_dag_runs(
            dag_id="daily_sales", limit=10, offset=20
        )
        self.assertIsInstance(result, DagRunPage)
        self.assertEqual(result.items[0].run_id, run_payload()["dag_run_id"])
        self.assertEqual(result.items[0].state, "success")
        self.assertFalse(hasattr(result.items[0], "conf"))

    async def test_invalid_json_and_missing_fields_are_translated(self):
        cases = (
            lambda _: httpx.Response(200, content=b"not-json"),
            lambda _: httpx.Response(200, json={"dags": [{}], "total_entries": 1}),
            lambda _: httpx.Response(200, json={"dags": []}),
        )
        for handler in cases:
            with self.subTest(handler=handler):
                client = self.build_client(handler)
                with self.assertRaises(OrchestratorInvalidResponseError):
                    await client.list_dags(limit=10, offset=0)
                await self.http_client.aclose()

    async def test_http_statuses_are_translated_without_problem_body(self):
        cases = {
            401: OrchestratorAuthenticationError,
            403: OrchestratorPermissionError,
            404: OrchestratorNotFoundError,
            409: OrchestratorConflictError,
            500: OrchestratorUnavailableError,
            503: OrchestratorUnavailableError,
        }
        for status_code, expected in cases.items():
            with self.subTest(status_code=status_code):
                client = self.build_client(
                    lambda _, code=status_code: httpx.Response(
                        code, json={"detail": "airflow-internal-secret"}
                    )
                )
                with self.assertRaises(expected) as raised:
                    await client.get_dag("daily_sales")
                self.assertNotIn("airflow-internal-secret", str(raised.exception))
                await self.http_client.aclose()

    async def test_timeout_and_connection_failures_are_translated_once(self):
        for exception in (
            httpx.ReadTimeout("slow"),
            httpx.ConnectError("cannot connect"),
        ):
            calls = 0

            def handler(request):
                nonlocal calls
                calls += 1
                raise exception

            with self.subTest(exception=type(exception).__name__):
                client = self.build_client(handler)
                with self.assertRaises(OrchestratorUnavailableError):
                    await client.list_dags(limit=10, offset=0)
                self.assertEqual(calls, 1)
                await self.http_client.aclose()

    async def test_get_run_and_task_instances_encode_ids_and_map_neutrally(self):
        seen = []

        def handler(request):
            seen.append(str(request.url))
            if str(request.url).endswith("dagRuns/run%2Fone"):
                return httpx.Response(200, json=run_payload(dag_run_id="run/one"))
            return httpx.Response(
                200, json={"task_instances": [task_payload()], "total_entries": 1}
            )

        client = self.build_client(handler)
        run = await client.get_dag_run(dag_id="folder/dag", run_id="run/one")
        tasks = await client.list_task_instances(
            dag_id="folder/dag", run_id="scheduled/run", limit=10, offset=2
        )
        self.assertEqual(run.run_id, "run/one")
        self.assertIn("folder%2Fdag", seen[0])
        self.assertIn("scheduled%2Frun", seen[1])
        self.assertEqual(tasks.pagination.returned_count, 1)
        self.assertFalse(hasattr(tasks.items[0], "hostname"))
        self.assertFalse(hasattr(tasks.items[0], "executor_config"))

    async def test_task_log_encodes_all_ids_and_generates_validated_query(self):
        seen = {}

        def handler(request):
            seen["request"] = request
            return httpx.Response(200, text="safe log content")

        result = await self.build_client(handler).get_task_log(
            dag_id="folder/dag", run_id="run/id", task_id="task/id",
            try_number=2, map_index=3,
        )
        request = seen["request"]
        self.assertIn("folder%2Fdag", str(request.url))
        self.assertIn("run%2Fid", str(request.url))
        self.assertIn("task%2Fid/logs/2", str(request.url))
        self.assertEqual(request.url.params["full_content"], "true")
        self.assertEqual(request.url.params["map_index"], "3")
        self.assertEqual(request.headers["Accept"], "text/plain")
        self.assertEqual(result.content, "safe log content")

    async def test_task_log_rejects_non_text_response_without_exposing_body(self):
        client = self.build_client(
            lambda _: httpx.Response(
                200, json={"content": "internal log", "file_token": "secret"}
            )
        )
        with self.assertRaises(OrchestratorInvalidResponseError) as raised:
            await client.get_task_log(
                dag_id="dag", run_id="run", task_id="task",
                try_number=1, map_index=-1,
            )
        self.assertNotIn("internal log", str(raised.exception))
        self.assertNotIn("secret", str(raised.exception))

    async def test_shutdown_closes_shared_http_client(self):
        client = self.build_client(
            lambda _: httpx.Response(200, json=dag_payload())
        )
        self.assertFalse(self.http_client.is_closed)
        await client.aclose()
        self.assertTrue(self.http_client.is_closed)

    async def test_credentials_do_not_leak_to_logs_or_exception(self):
        client = self.build_client(
            lambda _: (_ for _ in ()).throw(httpx.ConnectError("offline"))
        )
        with self.assertLogs(
            "api.orchestrators.airflow", level=logging.WARNING
        ) as captured:
            with self.assertRaises(OrchestratorUnavailableError) as raised:
                await client.get_dag("daily_sales")
        output = " ".join([*captured.output, str(raised.exception)])
        self.assertNotIn("api-user", output)
        self.assertNotIn("highly-secret-password", output)


class AirflowHttpConfigurationTests(unittest.TestCase):
    def test_timeout_values_are_explicit(self):
        self.assertEqual(AIRFLOW_TIMEOUT.connect, 5.0)
        self.assertEqual(AIRFLOW_TIMEOUT.read, 15.0)
        self.assertEqual(AIRFLOW_TIMEOUT.write, 10.0)
        self.assertEqual(AIRFLOW_TIMEOUT.pool, 5.0)

    def test_tls_and_redirect_configuration_are_forwarded(self):
        with patch("api.orchestrators.airflow.httpx.AsyncClient") as constructor:
            create_airflow_http_client(
                make_settings(airflow_api_verify_tls=False)
            )
        arguments = constructor.call_args.kwargs
        self.assertFalse(arguments["verify"])
        self.assertFalse(arguments["follow_redirects"])
        self.assertEqual(arguments["timeout"], AIRFLOW_TIMEOUT)


class ApplicationLifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def test_lifespan_registers_and_closes_one_shared_client(self):
        class Pool:
            def __init__(self):
                self.open_calls = 0
                self.close_calls = 0

            async def open(self, *, wait):
                self.open_calls += 1

            async def close(self):
                self.close_calls += 1

        pool = Pool()
        http_client = httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda _: httpx.Response(200, json={})
            )
        )
        application = SimpleNamespace(
            state=SimpleNamespace(settings=make_settings())
        )
        with (
            patch("api.main.create_database_pool", return_value=pool),
            patch(
                "api.main.create_airflow_http_client",
                return_value=http_client,
            ) as client_factory,
        ):
            async with lifespan(application):
                self.assertIs(application.state.airflow_http_client, http_client)
                self.assertIsInstance(
                    application.state.orchestrator_client, AirflowClient
                )
                client_factory.assert_called_once_with(application.state.settings)
                self.assertEqual(pool.open_calls, 1)
                self.assertFalse(http_client.is_closed)

        self.assertTrue(http_client.is_closed)
        self.assertEqual(pool.close_calls, 1)


if __name__ == "__main__":
    unittest.main()
