from __future__ import annotations

import json
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from framework.airflow import AirflowClient
from framework.api import ApiClient
from framework.dataset import (
    copy_validation_dataset, mutate_csv_value, parse_dbt_failure_evidence,
    resolve_airflow_task_logs, validate_ecommerce_dataset,
    verify_csv_mutation, write_airflow_dataset_override,
)
from framework.docker import DockerClient
from framework.models import AirflowTaskState, ValidationResult, ValidationStatus
from framework.postgres import PostgresClient
from framework.reporting import write_report
from framework.timing import utc_timestamp
from scenarios.postgres_interruption import EXPECTED_TIER_B_COUNTS, validate_tier_b_counts

STANDARD_TIER_B_CONTAINER_PATH = "/opt/open-dataops/domains/ecommerce/validation_data/tier_b"
AIRFLOW_SERVICES = ["airflow-scheduler", "airflow-webserver"]
DOWNSTREAM_TASKS = {
    "collect_dbt_metadata", "collect_data_health_metrics", "detect_data_incidents",
}


@dataclass(frozen=True)
class InvalidInputConfig:
    dag_id: str = "ecommerce_pipeline"
    timeout: float = 600.0
    report_dir: str | Path = "runtime/validation/reports"
    source_dataset: str | Path = "domains/ecommerce/validation_data/tier_b"
    work_root: str | Path = "runtime/validation/work"
    runtime_log_root: str | Path = "runtime/logs/airflow"
    invalid_value: str = "bank_transfer"
    keep_work_directory: bool = False


def _state_map(states: list[AirflowTaskState]) -> dict[str, str]:
    return {task.task_id: task.state for task in states}


def evaluate_invalid_task_states(states: dict[str, str]) -> dict[str, Any]:
    observed_failed = sorted(task for task, state in states.items() if state == "failed")
    expected_prefix = (
        states.get("bootstrap_raw_data") == "success"
        and states.get("run_dbt") == "success"
        and states.get("test_dbt") == "failed"
    )
    downstream_blocked = all(
        states.get(task, "none") not in {"success", "running"}
        for task in DOWNSTREAM_TASKS
    )
    return {
        "expected_failed_task": "test_dbt",
        "observed_failed_task": observed_failed,
        "expected_prefix_states": expected_prefix,
        "downstream_blocked": downstream_blocked,
        "matches_expected_behavior": (
            expected_prefix and downstream_blocked and observed_failed == ["test_dbt"]
        ),
    }


def execute(
    config: InvalidInputConfig,
    docker: DockerClient,
    postgres: PostgresClient,
    api: ApiClient,
    airflow_factory: Callable[[DockerClient], AirflowClient] = AirflowClient,
) -> tuple[ValidationResult, Path]:
    started_at = utc_timestamp()
    started = time.monotonic()
    stamp = started_at.replace(":", "").replace("-", "").replace(".", "")
    work_directory = Path(config.work_root) / f"invalid_input_{stamp}"
    invalid_dataset = work_directory / "tier_b"
    override_path = work_directory / "docker-compose.invalid-input.yml"
    container_dataset_path = f"/opt/airflow/runtime/validation/work/{work_directory.name}/tier_b"
    details: dict[str, Any] = {
        "invalid_dataset_path": str(invalid_dataset),
        "mutation_file": str(invalid_dataset / "payments.csv"),
        "mutation_column": "payment_method",
        "mutation_original_value": None,
        "mutation_invalid_value": config.invalid_value,
        "mutation_count": 0,
        "expected_failed_task": "test_dbt",
        "observed_failed_task": [],
        "dbt_failure_test_names": [],
        "dbt_failure_evidence": [],
        "tier_b_restored": False,
        "scheduler_environment_after_restore": None,
        "recovery_run_id": None,
        "recovery_run_final_state": None,
        "final_row_counts": {},
        "work_directory_retained": config.keep_work_directory,
    }
    errors: list[str] = []
    artifacts: list[str] = []
    status = ValidationStatus.ERROR
    summary = "Invalid-input validation did not complete"
    invalid_services_applied = False
    standard_airflow = airflow_factory(docker)

    def restore_tier_b() -> None:
        nonlocal invalid_services_applied
        docker.recreate_services(AIRFLOW_SERVICES)
        docker.wait_for_service_healthy("airflow-scheduler", config.timeout)
        docker.wait_for_service_healthy("airflow-webserver", config.timeout)
        environment = docker.compose_environment_value(
            "airflow-scheduler", "ECOMMERCE_DATA_DIR"
        )
        details["scheduler_environment_after_restore"] = environment
        if environment != STANDARD_TIER_B_CONTAINER_PATH:
            raise RuntimeError(
                f"Scheduler dataset was not restored: {environment!r}"
            )
        details["tier_b_restored"] = True
        invalid_services_applied = False

    try:
        details["postgres_health_before"] = docker.wait_for_service_healthy(
            "postgres", config.timeout
        ).health
        details["postgres_readiness_before"] = postgres.wait_for_postgres_ready(
            config.timeout
        )
        details["scheduler_health_before"] = standard_airflow.wait_for_scheduler_healthy(
            config.timeout
        ).health
        details["api_health_before"] = api.wait_for_health(config.timeout)
        source_files = validate_ecommerce_dataset(config.source_dataset)
        details["source_dataset_files"] = [path.name for path in source_files]

        copy_validation_dataset(config.source_dataset, invalid_dataset)
        mutation = mutate_csv_value(
            invalid_dataset / "payments.csv", "payment_method", config.invalid_value
        )
        details["mutation_original_value"] = mutation["original_value"]
        details["mutation_count"] = verify_csv_mutation(
            invalid_dataset / "payments.csv", "payment_method", config.invalid_value
        )
        write_airflow_dataset_override(override_path, container_dataset_path)

        invalid_docker = docker.with_additional_compose_files([override_path])
        invalid_airflow = airflow_factory(invalid_docker)
        try:
            invalid_services_applied = True
            invalid_docker.recreate_services(AIRFLOW_SERVICES)
            invalid_docker.wait_for_service_healthy("airflow-scheduler", config.timeout)
            invalid_docker.wait_for_service_healthy("airflow-webserver", config.timeout)
            environment = invalid_docker.compose_environment_value(
                "airflow-scheduler", "ECOMMERCE_DATA_DIR"
            )
            details["scheduler_environment_for_invalid_run"] = environment
            if environment != container_dataset_path:
                raise RuntimeError(
                    f"Scheduler did not resolve the invalid dataset: {environment!r}"
                )

            invalid_run = invalid_airflow.trigger_dag(config.dag_id)
            details["invalid_run_id"] = invalid_run.run_id
            invalid_final = invalid_airflow.wait_for_dag_terminal_state(
                config.dag_id, invalid_run.run_id, config.timeout
            )
            details["invalid_run_final_state"] = invalid_final.state
            invalid_states = invalid_airflow.get_task_states(
                config.dag_id, invalid_run.run_id
            )
            if not invalid_states:
                raise RuntimeError("Airflow returned no invalid-run task states")
            details["invalid_task_states"] = _state_map(invalid_states)
            task_evaluation = evaluate_invalid_task_states(
                details["invalid_task_states"]
            )
            details.update(task_evaluation)

            try:
                log_paths = resolve_airflow_task_logs(
                    config.runtime_log_root, config.dag_id, invalid_run.run_id,
                    "test_dbt",
                )
                if not log_paths:
                    raise FileNotFoundError("No mounted test_dbt task logs were found")
                log_evidence = parse_dbt_failure_evidence(log_paths)
                details["dbt_failure_test_names"] = log_evidence["test_names"]
                details["dbt_failure_evidence"] = log_evidence["excerpts"]
                artifacts.extend(str(path) for path in log_paths)
            except Exception as evidence_error:
                errors.append(
                    f"dbt log evidence collection failed: {type(evidence_error).__name__}: {evidence_error}"
                )
        finally:
            if invalid_services_applied:
                restore_tier_b()

        recovery_run = standard_airflow.trigger_dag(config.dag_id)
        details["recovery_run_id"] = recovery_run.run_id
        recovery_final = standard_airflow.wait_for_dag_terminal_state(
            config.dag_id, recovery_run.run_id, config.timeout
        )
        details["recovery_run_final_state"] = recovery_final.state
        recovery_states = standard_airflow.get_task_states(
            config.dag_id, recovery_run.run_id
        )
        if not recovery_states:
            raise RuntimeError("Airflow returned no recovery-run task states")
        details["recovery_task_states"] = _state_map(recovery_states)
        details["recovery_dbt_tests_passed"] = (
            details["recovery_task_states"].get("test_dbt") == "success"
        )
        counts = postgres.table_row_counts(list(EXPECTED_TIER_B_COUNTS))
        details["final_row_counts"] = counts
        details["tier_b_count_validation"] = validate_tier_b_counts(counts)
        details["database_size"] = postgres.database_size()

        details["postgres_health"] = docker.wait_for_service_healthy(
            "postgres", config.timeout
        ).health
        details["scheduler_health"] = standard_airflow.wait_for_scheduler_healthy(
            config.timeout
        ).health
        details["api_health"] = api.wait_for_health(config.timeout)

        expected_failure_observed = (
            details.get("invalid_run_final_state") == "failed"
            and details.get("matches_expected_behavior", False)
            and any(
                "accepted_values_" in name and "payments_payment_method" in name
                for name in details["dbt_failure_test_names"]
            )
        )
        recovery_passed = (
            details["recovery_run_final_state"] == "success"
            and details["recovery_dbt_tests_passed"]
        )
        final_health = (
            details["postgres_health"] == "healthy"
            and details["scheduler_health"] == "healthy"
            and details["api_health"]
        )
        if errors:
            status = ValidationStatus.ERROR
            summary = "Behavior was observed, but required evidence collection failed"
        elif not expected_failure_observed:
            status = ValidationStatus.FAIL
            summary = "Invalid input did not fail at the expected dbt quality gate"
        elif not recovery_passed:
            status = ValidationStatus.FAIL
            summary = "Invalid input was detected, but the fresh recovery run failed"
        elif not details["tier_b_count_validation"]["matches"]:
            status = ValidationStatus.FAIL
            summary = "Recovery completed, but final Tier B row counts did not match"
        elif not final_health:
            status = ValidationStatus.FAIL
            summary = "Recovery completed, but final platform health was not restored"
        else:
            status = ValidationStatus.PASS
            summary = "Invalid input was rejected and a fresh Tier B run recovered successfully"
    except Exception as exc:
        errors.append(f"{type(exc).__name__}: {exc}")
        status = ValidationStatus.ERROR
        summary = "Invalid-input scenario encountered an orchestration or timeout error"
    finally:
        if invalid_services_applied:
            try:
                restore_tier_b()
                details["safety_restoration_attempted"] = True
            except Exception as restore_error:
                errors.append(
                    f"Tier B safety restoration failed: {type(restore_error).__name__}: {restore_error}"
                )
                details["tier_b_restored"] = False
                status = ValidationStatus.ERROR
                summary = "Tier B safety restoration failed"
        if work_directory.exists() and not config.keep_work_directory:
            shutil.rmtree(work_directory)
            details["work_directory_removed"] = True

    result = ValidationResult(
        "invalid_input", status, started_at, utc_timestamp(),
        round(time.monotonic() - started, 3), summary, details, errors, artifacts,
    )
    path = write_report(result, config.report_dir)
    result.artifacts.append(str(path))
    path.write_text(json.dumps(result.to_dict(), indent=2) + "\n", encoding="utf-8")
    return result, path


def run(
    config: InvalidInputConfig,
    docker: DockerClient | None = None,
) -> tuple[ValidationResult, Path]:
    docker = docker or DockerClient()
    return execute(config, docker, PostgresClient(docker), ApiClient())
