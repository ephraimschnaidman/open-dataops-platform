from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

VALIDATION_ROOT = Path(__file__).resolve().parents[1] / "scripts" / "validation"
sys.path.insert(0, str(VALIDATION_ROOT))

from framework.airflow import (  # noqa: E402
    AirflowClient, parse_dag_runs, parse_dag_runs_json, parse_task_states,
)
from framework.api import percentile  # noqa: E402
from framework.command import CommandTimeoutError, run_command  # noqa: E402
from framework.docker import parse_container_state  # noqa: E402
from framework.models import (  # noqa: E402
    AirflowDagRun, AirflowTaskState, ContainerState, ValidationResult,
    ValidationStatus,
)
from framework.reporting import write_report  # noqa: E402
from framework.timing import WaitTimeoutError  # noqa: E402
from scenarios.scheduler_interruption import (  # noqa: E402
    SchedulerInterruptionConfig, execute,
)
from scenarios.postgres_interruption import (  # noqa: E402
    EXPECTED_TIER_B_COUNTS, PostgresInterruptionConfig,
    execute as execute_postgres, validate_tier_b_counts,
)


class CommandTests(unittest.TestCase):
    @patch("framework.command.subprocess.run")
    def test_command_result_captures_warning_with_zero_exit(self, mocked_run):
        mocked_run.return_value = subprocess.CompletedProcess(
            ["airflow"], 0, "success\n", "FutureWarning: deprecated setting\n"
        )
        result = run_command(["airflow", "dags", "list"])
        self.assertEqual(result.return_code, 0)
        self.assertEqual(result.stdout, "success\n")
        self.assertIn("FutureWarning", result.stderr)
        self.assertGreaterEqual(result.duration_seconds, 0)
        self.assertEqual(result.command, ["airflow", "dags", "list"])
        self.assertFalse(mocked_run.call_args.kwargs["shell"])

    @patch("framework.command.subprocess.run")
    def test_timeout_is_typed_and_preserves_output(self, mocked_run):
        mocked_run.side_effect = subprocess.TimeoutExpired(
            ["docker"], 2, output="partial", stderr="waiting"
        )
        with self.assertRaises(CommandTimeoutError) as raised:
            run_command(["docker", "inspect", "x"], timeout=2)
        self.assertEqual(raised.exception.result.stdout, "partial")
        self.assertEqual(raised.exception.result.stderr, "waiting")


class ParsingTests(unittest.TestCase):
    def test_json_dag_run_exactly_preserves_regression_run_id(self):
        run_id = "validation__20260806T194207.040060Z__cb34dc98"
        output = (
            "[info] Airflow is starting\nFutureWarning: configuration changed\n"
            '[{"dag_id":"ecommerce_pipeline","run_id":"' + run_id + '",'
            '"state":"success","execution_date":"2026-08-06T19:42:10+00:00"},'
            '{"dag_id":"ecommerce_pipeline","run_id":'
            '"manual__2026-08-06T18:58:05.123456+00:00","state":"success"}]\n'
        )
        runs = parse_dag_runs_json(output)
        self.assertEqual(runs[0].run_id, run_id)
        self.assertEqual(
            runs[1].run_id, "manual__2026-08-06T18:58:05.123456+00:00"
        )

    def test_dag_run_table_ignores_warnings_and_variable_widths(self):
        output = """FutureWarning: ignored
[2026-08-06 19:45:00] INFO | scheduler reconnected
+--------------------+-------------------+---------+--------------------------+
| dag_id             | run_id            | state   | execution_date           |
+--------------------+-------------------+---------+--------------------------+
| ecommerce_pipeline | validation__abc   | running | 2026-08-06T10:00:00+00:00 |
+--------------------+-------------------+---------+--------------------------+
"""
        self.assertEqual(
            parse_dag_runs(output),
            [AirflowDagRun("ecommerce_pipeline", "validation__abc", "running", "2026-08-06T10:00:00+00:00")],
        )

    def test_task_state_table_supports_expected_states(self):
        output = """| dag_id | execution_date | task_id | state |
| ecommerce_pipeline | date | run_dbt | upstream_failed |
| ecommerce_pipeline | date | collect | none |
"""
        states = parse_task_states(output, "ecommerce_pipeline", "run-x")
        self.assertEqual([value.state for value in states], ["upstream_failed", "none"])
        self.assertEqual(states[0].run_id, "run-x")

    def test_docker_health_parsing(self):
        payload = json.dumps([{"Name": "/scheduler", "State": {
            "Status": "running", "Running": True, "Health": {"Status": "healthy"}
        }}])
        self.assertEqual(
            parse_container_state(payload),
            ContainerState("scheduler", "running", "healthy", True),
        )

    def test_nearest_rank_percentile_behavior_is_preserved(self):
        self.assertEqual(percentile([1, 2, 3, 4, 100], .95), 100)
        self.assertEqual(percentile([], .99), 0)

    @patch("framework.airflow.wait_until")
    def test_terminal_wait_retries_temporarily_missing_exact_run(self, mocked_wait):
        run_id = "validation__20260806T194207.040060Z__cb34dc98"

        class SequentialDocker:
            def __init__(self):
                self.outputs = ["[]", json.dumps([{
                    "dag_id": "ecommerce_pipeline", "run_id": run_id,
                    "state": "success",
                }])]

            def compose_exec(self, service, command):
                self.assertions = (service, command)
                return SimpleNamespace(stdout=self.outputs.pop(0))

        def poll_twice(predicate, *args, **kwargs):
            self.assertIsNone(predicate())
            return predicate()

        mocked_wait.side_effect = poll_twice
        docker = SequentialDocker()
        result = AirflowClient(docker).wait_for_dag_terminal_state(
            "ecommerce_pipeline", run_id, 10
        )
        self.assertEqual(result.run_id, run_id)
        self.assertEqual(docker.assertions[1][-2:], ["--output", "json"])

    def test_task_state_command_preserves_punctuation_rich_run_id(self):
        run_id = "manual__2026-08-06T19:42:07.040060+00:00__cb34dc98"

        class CapturingDocker:
            def compose_exec(self, service, command):
                self.command = command
                return SimpleNamespace(stdout=(
                    "dag_id | task_id | state\n"
                    "ecommerce_pipeline | run_dbt | success\n"
                ))

        docker = CapturingDocker()
        states = AirflowClient(docker).get_task_states("ecommerce_pipeline", run_id)
        self.assertEqual(states[0].state, "success")
        self.assertEqual(docker.command[-1], run_id)


class ReportingTests(unittest.TestCase):
    def test_json_reports_are_valid_and_unique(self):
        result = ValidationResult(
            "sample", ValidationStatus.PASS, "2026-08-06T10:00:00Z",
            "2026-08-06T10:00:01Z", 1.0, "ok",
        )
        with tempfile.TemporaryDirectory() as directory:
            first = write_report(result, directory)
            second = write_report(result, directory)
            self.assertNotEqual(first, second)
            self.assertEqual(json.loads(first.read_text(encoding="utf-8"))["status"], "PASS")


class FakeDocker:
    def __init__(self):
        self.started = []
    def stop_service(self, service):
        raise AssertionError("scheduler should not be stopped before task is running")
    def start_service(self, service):
        self.started.append(service)


class TimingOutAirflow:
    def wait_for_scheduler_healthy(self, timeout):
        return SimpleNamespace(health="healthy")
    def trigger_dag(self, dag_id):
        return AirflowDagRun(dag_id, "validation__timeout", "queued")
    def wait_for_task_state(self, *args, **kwargs):
        raise WaitTimeoutError("target task timeout")
    def get_dag_run(self, dag_id, run_id):
        return AirflowDagRun(dag_id, run_id, "running")
    def list_dag_runs(self, dag_id):
        return [AirflowDagRun(dag_id, "validation__timeout", "running")]
    def get_task_states(self, dag_id, run_id):
        return [AirflowTaskState(dag_id, run_id, "run_dbt", "queued")]


class ScenarioTests(unittest.TestCase):
    def test_target_task_timeout_produces_error_report_and_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            result, path = execute(
                SchedulerInterruptionConfig(timeout=.01, interruption_seconds=0, report_dir=directory),
                FakeDocker(), TimingOutAirflow(),
            )
            self.assertEqual(result.status, ValidationStatus.ERROR)
            self.assertIn("WaitTimeoutError", result.errors[0])
            self.assertEqual(result.details["last_observed_dag_state"], "running")
            self.assertTrue(path.exists())


def successful_task_states(dag_id, run_id, run_dbt="success"):
    values = {
        "bootstrap_raw_data": "success", "run_dbt": run_dbt,
        "test_dbt": "success" if run_dbt == "success" else "upstream_failed",
        "collect_dbt_metadata": "success" if run_dbt == "success" else "upstream_failed",
        "collect_data_health_metrics": "success" if run_dbt == "success" else "upstream_failed",
        "detect_data_incidents": "success" if run_dbt == "success" else "upstream_failed",
    }
    return [AirflowTaskState(dag_id, run_id, task, state)
            for task, state in values.items()]


class PostgresScenarioDocker:
    def __init__(self):
        self.health_calls = []

    def wait_for_service_healthy(self, service, timeout):
        self.health_calls.append(service)
        return ContainerState(service, "running", "healthy", True)


class PostgresScenarioApi:
    def wait_for_health(self, timeout):
        return True


class PostgresScenarioClient:
    def __init__(self, readiness=None):
        self.readiness = list(readiness or [True, True, True])
        self.start_calls = 0
        self.stop_calls = 0

    def wait_for_postgres_ready(self, timeout):
        value = self.readiness.pop(0)
        if isinstance(value, Exception):
            raise value
        return value

    def stop_postgres(self):
        self.stop_calls += 1

    def start_postgres(self):
        self.start_calls += 1

    def table_row_counts(self, tables):
        return {table: EXPECTED_TIER_B_COUNTS.get(table, 1) for table in tables}

    def database_size(self):
        return "512 MB"


class PostgresScenarioAirflow:
    def __init__(self, interrupted_state="success"):
        self.interrupted_state = interrupted_state
        self.triggered = []
        self.terminal_error = None
        self.list_error = None

    def wait_for_scheduler_healthy(self, timeout):
        return ContainerState("scheduler", "running", "healthy", True)

    def trigger_dag(self, dag_id):
        run_id = "validation__interrupted" if not self.triggered else "validation__fresh"
        self.triggered.append(run_id)
        return AirflowDagRun(dag_id, run_id, "queued")

    def wait_for_task_state(self, dag_id, run_id, task_id, expected, timeout):
        return AirflowTaskState(dag_id, run_id, task_id, "running")

    def wait_for_dag_terminal_state(self, dag_id, run_id, timeout):
        if self.terminal_error:
            raise self.terminal_error
        state = self.interrupted_state if run_id.endswith("interrupted") else "success"
        return AirflowDagRun(dag_id, run_id, state)

    def get_task_states(self, dag_id, run_id):
        failed = run_id.endswith("interrupted") and self.interrupted_state == "failed"
        return successful_task_states(dag_id, run_id, "failed" if failed else "success")

    def list_dag_runs(self, dag_id):
        if self.list_error:
            raise self.list_error
        return [AirflowDagRun(dag_id, "validation__interrupted", "running")]


class PostgresInterruptionScenarioTests(unittest.TestCase):
    def execute_case(self, airflow=None, postgres=None):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        return execute_postgres(
            PostgresInterruptionConfig(
                interruption_seconds=0, timeout=.01, report_dir=directory.name
            ),
            PostgresScenarioDocker(), airflow or PostgresScenarioAirflow(),
            postgres or PostgresScenarioClient(), PostgresScenarioApi(),
        )

    def test_successful_postgres_readiness_recovery_passes(self):
        postgres = PostgresScenarioClient()
        result, path = self.execute_case(postgres=postgres)
        self.assertEqual(result.status, ValidationStatus.PASS)
        self.assertTrue(result.details["postgres_readiness_after_recovery"])
        self.assertTrue(result.details["postgres_left_running_healthy"])
        self.assertEqual(postgres.start_calls, 2)
        self.assertTrue(path.exists())

    def test_safety_restart_after_recovery_exception(self):
        postgres = PostgresScenarioClient(
            [True, RuntimeError("readiness lookup failed"), True]
        )
        result, _ = self.execute_case(postgres=postgres)
        self.assertEqual(result.status, ValidationStatus.ERROR)
        self.assertEqual(postgres.start_calls, 2)
        self.assertTrue(result.details["safety_restart_attempted"])
        self.assertTrue(result.details["postgres_left_running_healthy"])

    def test_controlled_dag_failure_is_fail_and_fresh_run_succeeds(self):
        airflow = PostgresScenarioAirflow(interrupted_state="failed")
        result, _ = self.execute_case(airflow=airflow)
        self.assertEqual(result.status, ValidationStatus.FAIL)
        self.assertEqual(result.details["interrupted_dag_final_state"], "failed")
        self.assertTrue(result.details["manual_recovery_required"])
        self.assertEqual(result.details["fresh_recovery_run_state"], "success")
        self.assertTrue(result.details["fresh_recovery_dbt_tests_passed"])
        self.assertEqual(airflow.triggered, ["validation__interrupted", "validation__fresh"])

    def test_task_evidence_survives_failed_dag_run_lookup(self):
        airflow = PostgresScenarioAirflow()
        airflow.terminal_error = RuntimeError("terminal lookup failed")
        airflow.list_error = RuntimeError("listing unavailable")
        result, _ = self.execute_case(airflow=airflow)
        self.assertEqual(result.status, ValidationStatus.ERROR)
        self.assertIn("run_dbt", result.details["last_observed_task_states"])
        self.assertTrue(any("DAG-run evidence" in error for error in result.errors))

    def test_target_task_timeout_is_error_without_stopping_postgres(self):
        airflow = PostgresScenarioAirflow()
        airflow.wait_for_task_state = lambda *args, **kwargs: (_ for _ in ()).throw(
            WaitTimeoutError("run_dbt timeout")
        )
        postgres = PostgresScenarioClient()
        result, _ = self.execute_case(airflow=airflow, postgres=postgres)
        self.assertEqual(result.status, ValidationStatus.ERROR)
        self.assertEqual(postgres.stop_calls, 0)
        self.assertEqual(postgres.start_calls, 0)

    def test_tier_b_row_count_validation_reports_mismatch(self):
        counts = dict(EXPECTED_TIER_B_COUNTS)
        counts["raw.orders"] -= 1
        validation = validate_tier_b_counts(counts)
        self.assertFalse(validation["matches"])
        self.assertEqual(
            validation["mismatches"]["raw.orders"],
            {"expected": 200_000, "actual": 199_999},
        )


if __name__ == "__main__":
    unittest.main()
