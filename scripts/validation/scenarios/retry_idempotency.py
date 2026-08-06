from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

from framework.airflow import AirflowClient
from framework.api import ApiClient
from framework.docker import DockerClient
from framework.idempotency import (
    MART_KEYS, RAW_KEYS, analyze_metadata_growth, capture_database_snapshot,
)
from framework.models import AirflowTaskState, ValidationResult, ValidationStatus
from framework.postgres import PostgresClient
from framework.reporting import write_report
from framework.timing import utc_timestamp
from scenarios.pipeline_recovery import (
    InvalidInputConfig, STANDARD_TIER_B_CONTAINER_PATH,
    execute as execute_invalid_input,
)
from scenarios.postgres_interruption import EXPECTED_TIER_B_COUNTS


@dataclass(frozen=True)
class RetryIdempotencyConfig:
    dag_id: str = "ecommerce_pipeline"
    timeout: float = 600.0
    report_dir: str | Path = "runtime/validation/reports"


def _state_map(states: list[AirflowTaskState]) -> dict[str, str]:
    return {task.task_id: task.state for task in states}


def _all_zero(values: dict[str, int]) -> bool:
    return all(value == 0 for value in values.values())


def _counts_are_stable(
    first: dict[str, Any], second: dict[str, Any], tables: dict[str, str],
) -> bool:
    return all(
        first["row_counts"].get(table) == second["row_counts"].get(table)
        for table in tables
    )


def execute(
    config: RetryIdempotencyConfig,
    docker: DockerClient,
    airflow: AirflowClient,
    postgres: PostgresClient,
    api: ApiClient,
    airflow_factory: Callable[[DockerClient], AirflowClient] = AirflowClient,
) -> tuple[ValidationResult, Path]:
    started_at = utc_timestamp()
    started = time.monotonic()
    details: dict[str, Any] = {
        "baseline_counts": {}, "first_valid_run_id": None,
        "first_valid_run_state": None, "first_valid_task_states": {},
        "second_valid_run_id": None, "second_valid_run_state": None,
        "second_valid_task_states": {}, "counts_after_first_run": {},
        "counts_after_second_run": {}, "raw_duplicate_checks": {},
        "mart_duplicate_checks": {}, "metadata_growth_analysis": {},
        "duplicate_trigger_first_response": None,
        "duplicate_trigger_second_response": None,
        "duplicate_trigger_run_ids": [],
        "duplicate_trigger_protection_result": False,
        "failed_run_id": None, "failed_run_state": None,
        "recovery_run_id": None, "recovery_run_state": None,
        "final_counts": {}, "manual_recovery_required": True,
    }
    errors: list[str] = []
    artifacts: list[str] = []
    status = ValidationStatus.ERROR
    summary = "Retry and idempotency validation did not complete"

    try:
        username = os.getenv("VALIDATION_API_USERNAME")
        password = os.getenv("VALIDATION_API_PASSWORD")
        if not username or not password:
            raise RuntimeError(
                "VALIDATION_API_USERNAME and VALIDATION_API_PASSWORD are required"
            )

        details["postgres_health_before"] = docker.wait_for_service_healthy(
            "postgres", config.timeout
        ).health
        details["scheduler_health_before"] = airflow.wait_for_scheduler_healthy(
            config.timeout
        ).health
        details["webserver_health_before"] = docker.wait_for_service_healthy(
            "airflow-webserver", config.timeout
        ).health
        details["api_health_before"] = api.wait_for_health(config.timeout)
        environment = docker.compose_environment_value(
            "airflow-scheduler", "ECOMMERCE_DATA_DIR"
        )
        details["scheduler_environment"] = environment
        if environment != STANDARD_TIER_B_CONTAINER_PATH:
            raise RuntimeError(f"Scheduler is not using Tier B: {environment!r}")

        baseline = capture_database_snapshot(postgres, config.dag_id)
        details["baseline_counts"] = baseline
        details["latest_successful_run_before"] = baseline["latest_successful_run_id"]

        first = airflow.trigger_dag(config.dag_id)
        details["first_valid_run_id"] = first.run_id
        first_final = airflow.wait_for_dag_terminal_state(
            config.dag_id, first.run_id, config.timeout
        )
        details["first_valid_run_state"] = first_final.state
        details["first_valid_task_states"] = _state_map(
            airflow.get_task_states(config.dag_id, first.run_id)
        )
        after_first = capture_database_snapshot(postgres, config.dag_id)
        details["counts_after_first_run"] = after_first

        second = airflow.trigger_dag(config.dag_id)
        details["second_valid_run_id"] = second.run_id
        second_final = airflow.wait_for_dag_terminal_state(
            config.dag_id, second.run_id, config.timeout
        )
        details["second_valid_run_state"] = second_final.state
        details["second_valid_task_states"] = _state_map(
            airflow.get_task_states(config.dag_id, second.run_id)
        )
        after_second = capture_database_snapshot(postgres, config.dag_id)
        details["counts_after_second_run"] = after_second
        details["raw_duplicate_checks"] = after_second["raw_duplicate_checks"]
        details["mart_duplicate_checks"] = after_second["mart_duplicate_checks"]
        details["metadata_growth_analysis"] = analyze_metadata_growth(
            baseline, after_first, after_second
        )
        details["raw_counts_stable"] = _counts_are_stable(
            after_first, after_second, RAW_KEYS
        )
        details["mart_counts_stable"] = _counts_are_stable(
            after_first, after_second, MART_KEYS
        )
        details["tier_b_raw_counts_match"] = all(
            after_second["row_counts"].get(table) == expected
            for table, expected in EXPECTED_TIER_B_COUNTS.items()
        )

        token = api.authenticate(username, password)
        api_run_id = f"validation__api_idempotency__{uuid.uuid4().hex}"
        first_response = api.trigger_dag_operation(config.dag_id, api_run_id, token)
        second_response = api.trigger_dag_operation(config.dag_id, api_run_id, token)
        details["duplicate_trigger_first_response"] = asdict(first_response)
        details["duplicate_trigger_second_response"] = asdict(second_response)
        matching_runs = [
            run.run_id for run in airflow.list_dag_runs(config.dag_id)
            if run.run_id == api_run_id
        ]
        details["duplicate_trigger_run_ids"] = matching_runs
        details["duplicate_trigger_protection_result"] = (
            first_response.status_code == 201
            and second_response.status_code == 409
            and len(matching_runs) == 1
        )
        if first_response.status_code == 201:
            api_final = airflow.wait_for_dag_terminal_state(
                config.dag_id, api_run_id, config.timeout
            )
            details["duplicate_trigger_run_final_state"] = api_final.state

        invalid_config = InvalidInputConfig(
            dag_id=config.dag_id, timeout=config.timeout,
            report_dir=config.report_dir,
        )
        invalid_result, invalid_report = execute_invalid_input(
            invalid_config, docker, postgres, api, airflow_factory
        )
        artifacts.extend(invalid_result.artifacts)
        artifacts.append(str(invalid_report))
        details["controlled_failure_scenario_status"] = invalid_result.status.value
        details["failed_run_id"] = invalid_result.details.get("invalid_run_id")
        details["failed_run_state"] = invalid_result.details.get("invalid_run_final_state")
        details["recovery_run_id"] = invalid_result.details.get("recovery_run_id")
        details["recovery_run_state"] = invalid_result.details.get(
            "recovery_run_final_state"
        )
        if invalid_result.errors:
            details["controlled_failure_errors"] = invalid_result.errors

        failed_historical = airflow.get_dag_run(
            config.dag_id, details["failed_run_id"]
        )
        recovery_historical = airflow.get_dag_run(
            config.dag_id, details["recovery_run_id"]
        )
        details["failed_run_history_preserved"] = failed_historical.state == "failed"
        details["recovery_run_history_distinct"] = (
            recovery_historical.state == "success"
            and failed_historical.run_id != recovery_historical.run_id
        )

        final_snapshot = capture_database_snapshot(postgres, config.dag_id)
        details["final_counts"] = final_snapshot
        details["database_size"] = postgres.database_size()
        details["postgres_health"] = docker.wait_for_service_healthy(
            "postgres", config.timeout
        ).health
        details["scheduler_health"] = airflow.wait_for_scheduler_healthy(
            config.timeout
        ).health
        details["webserver_health"] = docker.wait_for_service_healthy(
            "airflow-webserver", config.timeout
        ).health
        details["api_health"] = api.wait_for_health(config.timeout)

        repeated_runs_pass = (
            first_final.state == second_final.state == "success"
            and details["first_valid_task_states"].get("test_dbt") == "success"
            and details["second_valid_task_states"].get("test_dbt") == "success"
            and details["raw_counts_stable"] and details["mart_counts_stable"]
            and details["tier_b_raw_counts_match"]
            and _all_zero(details["raw_duplicate_checks"])
            and _all_zero(details["mart_duplicate_checks"])
            and details["metadata_growth_analysis"]["classification"]
                == "expected_append_only_history"
        )
        controlled_recovery_pass = (
            invalid_result.status is ValidationStatus.PASS
            and details["failed_run_history_preserved"]
            and details["recovery_run_history_distinct"]
        )
        final_health = (
            details["postgres_health"] == "healthy"
            and details["scheduler_health"] == "healthy"
            and details["webserver_health"] == "healthy"
            and details["api_health"]
        )
        if not repeated_runs_pass:
            status = ValidationStatus.FAIL
            summary = "Repeated Tier B runs were not fully idempotent"
        elif not details["duplicate_trigger_protection_result"]:
            status = ValidationStatus.FAIL
            summary = "Operations API duplicate-trigger protection did not match its contract"
        elif details.get("duplicate_trigger_run_final_state") != "success":
            status = ValidationStatus.FAIL
            summary = "The accepted Operations API run did not finish successfully"
        elif not controlled_recovery_pass:
            status = ValidationStatus.FAIL
            summary = "Controlled failure or fresh recovery behavior was inconsistent"
        elif not final_health:
            status = ValidationStatus.FAIL
            summary = "Idempotency checks passed, but final service health did not"
        else:
            status = ValidationStatus.PASS
            summary = "Repeated, duplicate, failed, and recovery operations remained consistent"
    except Exception as exc:
        errors.append(f"{type(exc).__name__}: {exc}")
        status = ValidationStatus.ERROR
        summary = "Retry/idempotency scenario encountered an orchestration or setup error"

    result = ValidationResult(
        "retry_idempotency", status, started_at, utc_timestamp(),
        round(time.monotonic() - started, 3), summary, details, errors, artifacts,
    )
    path = write_report(result, config.report_dir)
    result.artifacts.append(str(path))
    path.write_text(json.dumps(result.to_dict(), indent=2) + "\n", encoding="utf-8")
    return result, path


def run(
    config: RetryIdempotencyConfig, docker: DockerClient | None = None,
) -> tuple[ValidationResult, Path]:
    docker = docker or DockerClient()
    return execute(
        config, docker, AirflowClient(docker), PostgresClient(docker), ApiClient()
    )
