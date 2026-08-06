from __future__ import annotations

import json
import os
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
from framework.dataset import (  # noqa: E402
    copy_validation_dataset, mutate_csv_value, parse_dbt_failure_evidence,
    verify_csv_mutation, write_airflow_dataset_override,
)
from framework.models import (  # noqa: E402
    AirflowDagRun, AirflowTaskState, ApiResponse, ContainerState, ValidationResult,
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
from scenarios.pipeline_recovery import (  # noqa: E402
    InvalidInputConfig, evaluate_invalid_task_states,
    execute as execute_invalid_input,
)
from framework.idempotency import (  # noqa: E402
    MART_KEYS, RAW_KEYS, analyze_metadata_growth,
)
from scenarios.retry_idempotency import (  # noqa: E402
    RetryIdempotencyConfig, execute as execute_retry_idempotency,
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


class DatasetHelperTests(unittest.TestCase):
    def make_dataset(self, root):
        root = Path(root)
        root.mkdir()
        for name in (
            "customers.csv", "products.csv", "orders.csv", "order_items.csv",
            "web_events.csv",
        ):
            (root / name).write_text("id\n1\n", encoding="utf-8")
        (root / "payments.csv").write_text(
            "payment_id,payment_method\nPAY1,card\nPAY2,paypal\n",
            encoding="utf-8",
        )
        return root

    def test_temporary_dataset_copy_does_not_mutate_original(self):
        with tempfile.TemporaryDirectory() as directory:
            source = self.make_dataset(Path(directory) / "source")
            original = (source / "payments.csv").read_bytes()
            copied = copy_validation_dataset(source, Path(directory) / "copy")
            mutation = mutate_csv_value(
                copied / "payments.csv", "payment_method", "bank_transfer"
            )
            self.assertEqual(mutation["mutation_count"], 1)
            self.assertEqual((source / "payments.csv").read_bytes(), original)
            self.assertEqual(
                verify_csv_mutation(
                    copied / "payments.csv", "payment_method", "bank_transfer"
                ), 1,
            )

    def test_mutation_verification_rejects_zero_or_multiple_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "payments.csv"
            path.write_text(
                "payment_method\nbank_transfer\nbank_transfer\n", encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "found 2"):
                verify_csv_mutation(path, "payment_method", "bank_transfer")

    def test_temporary_compose_override_is_narrow(self):
        with tempfile.TemporaryDirectory() as directory:
            path = write_airflow_dataset_override(
                Path(directory) / "override.yml",
                "/opt/airflow/runtime/validation/work/invalid_input_x/tier_b",
            )
            value = path.read_text(encoding="utf-8")
            self.assertIn("airflow-scheduler", value)
            self.assertIn("airflow-webserver", value)
            self.assertEqual(value.count("ECOMMERCE_DATA_DIR"), 2)
            self.assertNotIn("postgres:", value)

    def test_dbt_failure_log_parser_extracts_concise_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            log = Path(directory) / "attempt=1.log"
            name = "accepted_values_stg_payments_payment_method__card__paypal__apple_pay"
            log.write_text(
                f"Failure in test {name}\nGot 1 result, configured to fail\n"
                "Done. PASS=107 WARN=0 ERROR=2 SKIP=0 TOTAL=109\n",
                encoding="utf-8",
            )
            evidence = parse_dbt_failure_evidence([log])
            self.assertEqual(evidence["test_names"], [name])
            self.assertEqual(len(evidence["excerpts"]), 3)


class InvalidInputSharedState:
    def __init__(self):
        self.standard_recreates = 0
        self.invalid_recreates = 0


class InvalidInputDocker:
    def __init__(self, shared=None, invalid=False, override=None):
        self.shared = shared or InvalidInputSharedState()
        self.invalid = invalid
        self.override = override

    def with_additional_compose_files(self, paths):
        return InvalidInputDocker(self.shared, True, Path(paths[0]))

    def recreate_services(self, services):
        if self.invalid:
            self.shared.invalid_recreates += 1
        else:
            self.shared.standard_recreates += 1

    def wait_for_service_healthy(self, service, timeout):
        return ContainerState(service, "running", "healthy", True)

    def compose_environment_value(self, service, name):
        if not self.invalid:
            return "/opt/open-dataops/domains/ecommerce/validation_data/tier_b"
        line = next(
            value.strip() for value in self.override.read_text(encoding="utf-8").splitlines()
            if "ECOMMERCE_DATA_DIR:" in value
        )
        return line.split(": ", 1)[1]


class InvalidInputPostgres:
    def __init__(self, mismatch=False):
        self.mismatch = mismatch

    def wait_for_postgres_ready(self, timeout):
        return True

    def table_row_counts(self, tables):
        counts = {table: EXPECTED_TIER_B_COUNTS[table] for table in tables}
        if self.mismatch:
            counts["raw.orders"] -= 1
        return counts

    def database_size(self):
        return "229 MB"


class InvalidInputApi:
    def wait_for_health(self, timeout):
        return True


class InvalidInputAirflow:
    def __init__(self, invalid, behavior):
        self.invalid = invalid
        self.behavior = behavior

    def wait_for_scheduler_healthy(self, timeout):
        return ContainerState("scheduler", "running", "healthy", True)

    def trigger_dag(self, dag_id):
        run_id = "validation__invalid" if self.invalid else "validation__recovery"
        return AirflowDagRun(dag_id, run_id, "queued")

    def wait_for_dag_terminal_state(self, dag_id, run_id, timeout):
        if self.invalid and self.behavior == "timeout":
            raise WaitTimeoutError("invalid DAG timeout")
        return AirflowDagRun(
            dag_id, run_id, "failed" if self.invalid else "success"
        )

    def get_task_states(self, dag_id, run_id):
        if not self.invalid:
            return successful_task_states(dag_id, run_id)
        if self.behavior == "unexpected":
            return successful_task_states(dag_id, run_id, "failed")
        values = {
            "bootstrap_raw_data": "success", "run_dbt": "success",
            "test_dbt": "failed", "collect_dbt_metadata": "upstream_failed",
            "collect_data_health_metrics": "upstream_failed",
            "detect_data_incidents": "upstream_failed",
        }
        return [AirflowTaskState(dag_id, run_id, task, state)
                for task, state in values.items()]


class InvalidInputScenarioTests(unittest.TestCase):
    def make_source(self, root):
        return DatasetHelperTests().make_dataset(root)

    def execute_case(self, behavior="expected", mismatch=False):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        source = self.make_source(root / "source")
        log_root = root / "logs"
        task_log = (
            log_root / "dag_id=ecommerce_pipeline" / "run_id=validation__invalid"
            / "task_id=test_dbt" / "attempt=1.log"
        )
        task_log.parent.mkdir(parents=True)
        task_log.write_text(
            "Failure in test accepted_values_stg_payments_payment_method__card__paypal__apple_pay\n"
            "Got 1 result, configured to fail\n"
            "Done. PASS=108 WARN=0 ERROR=1 SKIP=0 TOTAL=109\n",
            encoding="utf-8",
        )
        docker = InvalidInputDocker()
        result, report = execute_invalid_input(
            InvalidInputConfig(
                timeout=.01, report_dir=root / "reports",
                source_dataset=source, work_root=root / "work",
                runtime_log_root=log_root,
            ),
            docker, InvalidInputPostgres(mismatch), InvalidInputApi(),
            lambda client: InvalidInputAirflow(client.invalid, behavior),
        )
        return result, report, docker

    def test_expected_failed_dag_and_successful_recovery_are_pass(self):
        result, report, docker = self.execute_case()
        self.assertEqual(result.status, ValidationStatus.PASS)
        self.assertEqual(result.details["observed_failed_task"], ["test_dbt"])
        self.assertTrue(result.details["downstream_blocked"])
        self.assertEqual(result.details["recovery_run_final_state"], "success")
        self.assertTrue(result.details["recovery_dbt_tests_passed"])
        self.assertTrue(result.details["tier_b_restored"])
        self.assertEqual(docker.shared.standard_recreates, 1)
        self.assertTrue(report.exists())
        self.assertIn(str(report), result.artifacts)

    def test_unexpected_task_failure_is_fail(self):
        result, _, _ = self.execute_case(behavior="unexpected")
        self.assertEqual(result.status, ValidationStatus.FAIL)
        self.assertFalse(result.details["matches_expected_behavior"])

    def test_row_count_mismatch_is_fail(self):
        result, _, _ = self.execute_case(mismatch=True)
        self.assertEqual(result.status, ValidationStatus.FAIL)
        self.assertFalse(result.details["tier_b_count_validation"]["matches"])

    def test_timeout_restores_tier_b_in_safety_path(self):
        result, _, docker = self.execute_case(behavior="timeout")
        self.assertEqual(result.status, ValidationStatus.ERROR)
        self.assertTrue(result.details["tier_b_restored"])
        self.assertEqual(docker.shared.standard_recreates, 1)
        self.assertEqual(docker.shared.invalid_recreates, 1)


def idempotency_snapshot(index=0, same_run_duplicate=False):
    row_counts = {table: EXPECTED_TIER_B_COUNTS[table] for table in RAW_KEYS}
    row_counts.update({table: position + 1 for position, table in enumerate(MART_KEYS)})
    duplicate_checks = {
        "pipeline_runs": int(same_run_duplicate), "dbt_node_results": 0,
        "table_health_metrics": 0, "data_incidents": 0,
    }
    return {
        "row_counts": row_counts,
        "raw_duplicate_checks": {table: 0 for table in RAW_KEYS},
        "mart_duplicate_checks": {table: 0 for table in MART_KEYS},
        "metadata_counts": {
            "metadata.pipeline_runs": 10 + index,
            "metadata.dbt_node_results": 1000 + index * 20,
            "metadata.table_health_metrics": 100 + index * 16,
            "metadata.data_incidents": 2,
            "metadata.open_data_incidents": 1,
        },
        "metadata_same_run_duplicate_checks": duplicate_checks,
        "open_incident_condition_groups": 0,
        "latest_successful_run_id": f"run-{index}",
    }


class IdempotencyAnalysisTests(unittest.TestCase):
    def test_stable_repeated_counts_and_expected_append_only_growth(self):
        analysis = analyze_metadata_growth(
            idempotency_snapshot(0), idempotency_snapshot(1),
            idempotency_snapshot(2),
        )
        self.assertEqual(analysis["classification"], "expected_append_only_history")
        self.assertEqual(analysis["first_run_delta"]["metadata.pipeline_runs"], 1)

    def test_same_run_metadata_duplication_is_unexpected(self):
        analysis = analyze_metadata_growth(
            idempotency_snapshot(0), idempotency_snapshot(1),
            idempotency_snapshot(2, same_run_duplicate=True),
        )
        self.assertEqual(analysis["classification"], "unexpected_growth")


class RetryDocker:
    def __init__(self, final_health="healthy"):
        self.final_health = final_health

    def wait_for_service_healthy(self, service, timeout):
        return ContainerState(service, "running", self.final_health, True)

    def compose_environment_value(self, service, name):
        return "/opt/open-dataops/domains/ecommerce/validation_data/tier_b"


class RetryAirflow:
    def __init__(self, duplicate_run_count=1, timeout=False):
        self.trigger_count = 0
        self.duplicate_run_count = duplicate_run_count
        self.timeout = timeout

    def wait_for_scheduler_healthy(self, timeout):
        return ContainerState("scheduler", "running", "healthy", True)

    def trigger_dag(self, dag_id):
        self.trigger_count += 1
        return AirflowDagRun(dag_id, f"valid-{self.trigger_count}", "queued")

    def wait_for_dag_terminal_state(self, dag_id, run_id, timeout):
        if self.timeout:
            raise WaitTimeoutError("valid run timeout")
        return AirflowDagRun(dag_id, run_id, "success")

    def get_task_states(self, dag_id, run_id):
        return successful_task_states(dag_id, run_id)

    def list_dag_runs(self, dag_id):
        return [AirflowDagRun(dag_id, "api-run-placeholder", "queued")]

    def get_dag_run(self, dag_id, run_id):
        return AirflowDagRun(
            dag_id, run_id, "failed" if run_id == "failed-run" else "success"
        )


class RetryApi:
    def __init__(self, airflow, password="validation-secret"):
        self.airflow = airflow
        self.password = password
        self.api_run_id = None

    def wait_for_health(self, timeout):
        return True

    def authenticate(self, username, password):
        if password != self.password:
            raise RuntimeError("bad credentials")
        return "jwt-super-secret"

    def trigger_dag_operation(self, dag_id, run_id, token):
        self.api_run_id = run_id
        self.airflow.list_dag_runs = lambda dag: [
            AirflowDagRun(dag, run_id, "queued")
            for _ in range(self.airflow.duplicate_run_count)
        ]
        calls = getattr(self, "calls", 0) + 1
        self.calls = calls
        return ApiResponse(
            201 if calls == 1 else 409,
            {"run_id": run_id} if calls == 1 else {"detail": "Pipeline operation conflict"},
        )


class RetryPostgres:
    def database_size(self):
        return "229 MB"


class RetryIdempotencyScenarioTests(unittest.TestCase):
    def execute_case(self, duplicate_run_count=1, final_health="healthy", timeout=False):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        airflow = RetryAirflow(duplicate_run_count, timeout)
        api = RetryApi(airflow)
        snapshots = [idempotency_snapshot(i) for i in (0, 1, 2, 3)]
        invalid_result = ValidationResult(
            "invalid_input", ValidationStatus.PASS, "start", "end", 1, "ok",
            details={
                "invalid_run_id": "failed-run", "invalid_run_final_state": "failed",
                "recovery_run_id": "recovery-run", "recovery_run_final_state": "success",
            },
        )
        with patch.dict(os.environ, {
            "VALIDATION_API_USERNAME": "operator",
            "VALIDATION_API_PASSWORD": "validation-secret",
        }, clear=False), patch(
            "scenarios.retry_idempotency.capture_database_snapshot",
            side_effect=snapshots,
        ), patch(
            "scenarios.retry_idempotency.execute_invalid_input",
            return_value=(invalid_result, Path(directory.name) / "invalid.json"),
        ):
            result, report = execute_retry_idempotency(
                RetryIdempotencyConfig(timeout=.01, report_dir=directory.name),
                RetryDocker(final_health), airflow, RetryPostgres(), api,
                lambda client: airflow,
            )
        return result, report

    def test_complete_retry_idempotency_contract_passes_and_redacts_credentials(self):
        result, report = self.execute_case()
        self.assertEqual(result.status, ValidationStatus.PASS)
        self.assertTrue(result.details["raw_counts_stable"])
        self.assertTrue(result.details["mart_counts_stable"])
        self.assertTrue(result.details["duplicate_trigger_protection_result"])
        self.assertTrue(result.details["failed_run_history_preserved"])
        serialized = report.read_text(encoding="utf-8")
        self.assertNotIn("validation-secret", serialized)
        self.assertNotIn("jwt-super-secret", serialized)

    def test_unintended_second_api_run_is_fail(self):
        result, _ = self.execute_case(duplicate_run_count=2)
        self.assertEqual(result.status, ValidationStatus.FAIL)
        self.assertFalse(result.details["duplicate_trigger_protection_result"])

    def test_unhealthy_final_service_is_fail(self):
        result, _ = self.execute_case(final_health="unhealthy")
        self.assertEqual(result.status, ValidationStatus.FAIL)

    def test_timeout_is_error(self):
        result, _ = self.execute_case(timeout=True)
        self.assertEqual(result.status, ValidationStatus.ERROR)

    def test_missing_credentials_is_clear_error(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ, {}, clear=True
        ):
            result, _ = execute_retry_idempotency(
                RetryIdempotencyConfig(report_dir=directory), RetryDocker(),
                RetryAirflow(), RetryPostgres(), RetryApi(RetryAirflow()),
            )
        self.assertEqual(result.status, ValidationStatus.ERROR)
        self.assertIn("VALIDATION_API_USERNAME", result.errors[0])


if __name__ == "__main__":
    unittest.main()
