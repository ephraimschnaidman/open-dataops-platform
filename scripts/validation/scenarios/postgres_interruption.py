from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from framework.airflow import AirflowClient
from framework.api import ApiClient
from framework.docker import DockerClient
from framework.models import AirflowTaskState, ValidationResult, ValidationStatus
from framework.postgres import PostgresClient
from framework.reporting import write_report
from framework.timing import utc_timestamp

EXPECTED_TIER_B_COUNTS = {
    "raw.customers": 50_000,
    "raw.products": 10_000,
    "raw.orders": 200_000,
    "raw.order_items": 400_000,
    "raw.payments": 200_000,
    "raw.web_events": 140_000,
}
MART_TABLES = [
    "marts.dim_customers", "marts.dim_products", "marts.dim_date",
    "marts.fct_orders", "marts.fct_order_items", "marts.fct_payments",
    "marts.fct_web_events", "marts.daily_sales",
    "marts.customer_lifetime_value", "marts.product_sales",
]


@dataclass(frozen=True)
class PostgresInterruptionConfig:
    dag_id: str = "ecommerce_pipeline"
    target_task: str = "run_dbt"
    interruption_seconds: float = 10.0
    timeout: float = 600.0
    report_dir: str | Path = "runtime/validation/reports"


def validate_tier_b_counts(counts: dict[str, int]) -> dict[str, Any]:
    mismatches = {
        table: {"expected": expected, "actual": counts.get(table)}
        for table, expected in EXPECTED_TIER_B_COUNTS.items()
        if counts.get(table) != expected
    }
    return {"expected": EXPECTED_TIER_B_COUNTS, "matches": not mismatches,
            "mismatches": mismatches}


def _state_map(states: list[AirflowTaskState]) -> dict[str, str]:
    return {task.task_id: task.state for task in states}


def execute(
    config: PostgresInterruptionConfig,
    docker: DockerClient,
    airflow: AirflowClient,
    postgres: PostgresClient,
    api: ApiClient,
) -> tuple[ValidationResult, Path]:
    started_at = utc_timestamp()
    started = time.monotonic()
    details: dict[str, Any] = {
        "dag_id": config.dag_id,
        "target_task": config.target_task,
        "interruption_seconds": config.interruption_seconds,
        "postgres_was_stopped": False,
        "manual_recovery_required": False,
        "fresh_recovery_run_id": None,
        "fresh_recovery_run_state": None,
        "final_row_counts": {},
    }
    errors: list[str] = []
    run_id: str | None = None
    postgres_ever_stopped = False
    postgres_currently_stopped = False
    status = ValidationStatus.ERROR
    summary = "PostgreSQL interruption scenario did not complete"

    try:
        initial_postgres = docker.wait_for_service_healthy("postgres", config.timeout)
        details["postgres_health_before_interruption"] = initial_postgres.health
        details["postgres_readiness_before_interruption"] = postgres.wait_for_postgres_ready(config.timeout)
        scheduler = airflow.wait_for_scheduler_healthy(config.timeout)
        details["scheduler_health_before_interruption"] = scheduler.health
        api_container = docker.wait_for_service_healthy("api", config.timeout)
        details["api_container_health_before_interruption"] = api_container.health
        details["api_health_before_interruption"] = api.wait_for_health(config.timeout)

        triggered = airflow.trigger_dag(config.dag_id)
        run_id = triggered.run_id
        details["run_id"] = run_id
        target = airflow.wait_for_task_state(
            config.dag_id, run_id, config.target_task, {"running"}, config.timeout
        )
        details["target_task_state_before_interruption"] = target.state

        postgres.stop_postgres()
        postgres_ever_stopped = True
        postgres_currently_stopped = True
        details["postgres_was_stopped"] = True
        details["postgres_stopped_at"] = utc_timestamp()
        time.sleep(config.interruption_seconds)

        recovery_started = time.monotonic()
        details["postgres_restart_started_at"] = utc_timestamp()
        postgres.start_postgres()
        postgres_currently_stopped = False
        details["postgres_readiness_after_recovery"] = postgres.wait_for_postgres_ready(config.timeout)
        recovered = docker.wait_for_service_healthy("postgres", config.timeout)
        details["postgres_recovered_at"] = utc_timestamp()
        details["postgres_recovery_seconds"] = round(time.monotonic() - recovery_started, 3)
        details["postgres_health_after_recovery"] = recovered.health
        recovered_scheduler = airflow.wait_for_scheduler_healthy(config.timeout)
        details["scheduler_health_after_recovery"] = recovered_scheduler.health
        details["api_health_after_recovery"] = api.wait_for_health(config.timeout)

        interrupted = airflow.wait_for_dag_terminal_state(
            config.dag_id, run_id, config.timeout
        )
        details["interrupted_dag_final_state"] = interrupted.state
        interrupted_states = airflow.get_task_states(config.dag_id, run_id)
        if not interrupted_states:
            raise RuntimeError("Airflow returned no interrupted-run task states")
        details["interrupted_task_states"] = _state_map(interrupted_states)
        details["interrupted_dbt_tests_passed"] = (
            details["interrupted_task_states"].get("test_dbt") == "success"
        )

        fresh_states: dict[str, str] = {}
        if interrupted.state == "failed":
            details["manual_recovery_required"] = True
            fresh = airflow.trigger_dag(config.dag_id)
            details["fresh_recovery_run_id"] = fresh.run_id
            fresh_final = airflow.wait_for_dag_terminal_state(
                config.dag_id, fresh.run_id, config.timeout
            )
            details["fresh_recovery_run_state"] = fresh_final.state
            fresh_task_list = airflow.get_task_states(config.dag_id, fresh.run_id)
            if not fresh_task_list:
                raise RuntimeError("Airflow returned no fresh recovery-run task states")
            fresh_states = _state_map(fresh_task_list)
            details["fresh_recovery_task_states"] = fresh_states
            details["fresh_recovery_dbt_tests_passed"] = (
                fresh_states.get("test_dbt") == "success"
            )

        counts = postgres.table_row_counts(
            [*EXPECTED_TIER_B_COUNTS, *MART_TABLES]
        )
        details["final_row_counts"] = counts
        details["tier_b_count_validation"] = validate_tier_b_counts(counts)
        details["database_size"] = postgres.database_size()

        infrastructure_recovered = all((
            details["postgres_readiness_after_recovery"],
            details["postgres_health_after_recovery"] == "healthy",
            details["scheduler_health_after_recovery"] == "healthy",
            details["api_health_after_recovery"],
            bool(details["database_size"]),
        ))
        details["infrastructure_recovery_passed"] = infrastructure_recovered

        if not infrastructure_recovered:
            status = ValidationStatus.FAIL
            summary = "PostgreSQL restarted, but platform health was not fully restored"
        elif not details["tier_b_count_validation"]["matches"]:
            status = ValidationStatus.FAIL
            summary = "PostgreSQL recovered, but final Tier B row counts did not match"
        elif interrupted.state == "failed":
            status = ValidationStatus.FAIL
            if details["fresh_recovery_run_state"] == "success" and details.get("fresh_recovery_dbt_tests_passed"):
                summary = "PostgreSQL recovered and a fresh run succeeded, but the interrupted DAG failed"
            else:
                summary = "PostgreSQL recovered, but the interrupted and fresh recovery outcomes were not successful"
        elif interrupted.state == "success" and details["interrupted_dbt_tests_passed"]:
            status = ValidationStatus.PASS
            summary = "PostgreSQL and the active pipeline recovered successfully"
        else:
            status = ValidationStatus.FAIL
            summary = "PostgreSQL recovered, but the interrupted pipeline did not complete cleanly"
    except Exception as exc:
        errors.append(f"{type(exc).__name__}: {exc}")
        summary = "PostgreSQL interruption scenario encountered a tooling or timeout error"
        if run_id:
            try:
                runs = airflow.list_dag_runs(config.dag_id)
                matching = next((item for item in runs if item.run_id == run_id), None)
                details["dag_run_lookup_evidence"] = {
                    "available_run_count": len(runs),
                    "exact_run_id_found": matching is not None,
                    "state": matching.state if matching else None,
                }
            except Exception as evidence_error:
                errors.append(
                    f"DAG-run evidence collection failed: {type(evidence_error).__name__}: {evidence_error}"
                )
            try:
                task_states = airflow.get_task_states(config.dag_id, run_id)
                details["last_observed_task_states"] = _state_map(task_states)
            except Exception as evidence_error:
                errors.append(
                    f"Task-state evidence collection failed: {type(evidence_error).__name__}: {evidence_error}"
                )
    finally:
        if postgres_ever_stopped:
            try:
                # Compose start is idempotent. Always perform the safety action,
                # even when the normal restart path already ran.
                postgres.start_postgres()
                postgres_currently_stopped = False
                details["safety_restart_attempted"] = True
                final_ready = postgres.wait_for_postgres_ready(config.timeout)
                final_state = docker.wait_for_service_healthy("postgres", config.timeout)
                details["postgres_final_readiness"] = final_ready
                details["postgres_final_health"] = final_state.health
                details["postgres_left_running_healthy"] = (
                    final_ready and final_state.health == "healthy"
                )
            except Exception as recovery_error:
                errors.append(
                    f"PostgreSQL safety recovery failed: {type(recovery_error).__name__}: {recovery_error}"
                )
                details["postgres_left_running_healthy"] = False
                status = ValidationStatus.ERROR
                summary = "PostgreSQL safety recovery failed"
        elif postgres_currently_stopped:
            # Defensive invariant; normally covered by postgres_ever_stopped.
            errors.append("PostgreSQL stop state was not recoverable")
            status = ValidationStatus.ERROR

    result = ValidationResult(
        "postgres_interruption", status, started_at, utc_timestamp(),
        round(time.monotonic() - started, 3), summary, details, errors, [],
    )
    path = write_report(result, config.report_dir)
    result.artifacts.append(str(path))
    path.write_text(json.dumps(result.to_dict(), indent=2) + "\n", encoding="utf-8")
    return result, path


def run(
    config: PostgresInterruptionConfig,
    docker: DockerClient | None = None,
) -> tuple[ValidationResult, Path]:
    docker = docker or DockerClient()
    return execute(
        config, docker, AirflowClient(docker), PostgresClient(docker), ApiClient()
    )
