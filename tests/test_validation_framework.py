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


if __name__ == "__main__":
    unittest.main()
