from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from framework.airflow import AirflowClient
from framework.docker import DockerClient
from framework.models import ValidationResult, ValidationStatus
from framework.reporting import print_summary, write_report
from framework.timing import utc_timestamp


@dataclass(frozen=True)
class SchedulerInterruptionConfig:
    dag_id: str = "ecommerce_pipeline"
    target_task: str = "run_dbt"
    interruption_seconds: float = 10.0
    timeout: float = 600.0
    report_dir: str | Path = "runtime/validation/reports"


def execute(
    config: SchedulerInterruptionConfig,
    docker: DockerClient,
    airflow: AirflowClient,
) -> tuple[ValidationResult, Path]:
    started_at = utc_timestamp()
    started = time.monotonic()
    details: dict[str, Any] = {
        "dag_id": config.dag_id, "target_task": config.target_task,
        "interruption_seconds": config.interruption_seconds,
        "scheduler_was_stopped": False, "native_recovery_only": True,
        "data_integrity": "Not directly evaluated by this service-recovery scenario",
    }
    errors: list[str] = []
    run_id: str | None = None
    scheduler_stopped = False
    status = ValidationStatus.ERROR
    summary = "Scenario did not complete"
    try:
        initial = airflow.wait_for_scheduler_healthy(config.timeout)
        details["initial_scheduler_health"] = initial.health
        run = airflow.trigger_dag(config.dag_id)
        run_id = run.run_id
        details["run_id"] = run_id
        observed = airflow.wait_for_task_state(
            config.dag_id, run_id, config.target_task, {"running"}, config.timeout
        )
        details["target_task_state_before_interruption"] = observed.state
        docker.stop_service("airflow-scheduler")
        scheduler_stopped = True
        details["scheduler_was_stopped"] = True
        details["scheduler_stopped_at"] = utc_timestamp()
        time.sleep(config.interruption_seconds)
        recovery_started = time.monotonic()
        details["scheduler_restart_started_at"] = utc_timestamp()
        docker.start_service("airflow-scheduler")
        scheduler_stopped = False
        recovered = airflow.wait_for_scheduler_healthy(config.timeout)
        details["scheduler_recovered_at"] = utc_timestamp()
        details["scheduler_recovery_seconds"] = round(time.monotonic() - recovery_started, 3)
        details["recovered_scheduler_health"] = recovered.health
        final_run = airflow.wait_for_dag_terminal_state(config.dag_id, run_id, config.timeout)
        task_states = airflow.get_task_states(config.dag_id, run_id)
        details["final_dag_state"] = final_run.state
        details["final_task_states"] = {task.task_id: task.state for task in task_states}
        if not task_states:
            raise RuntimeError("Airflow returned no final task states")
        if final_run.state == "success" and all(task.state in {"success", "skipped"} for task in task_states):
            status = ValidationStatus.PASS
            summary = "Scheduler restarted and the DAG completed successfully"
            details["recovery_behavior"] = "Scheduler health and in-flight DAG execution recovered natively"
        else:
            status = ValidationStatus.FAIL
            summary = f"Scheduler recovered, but the DAG finished in {final_run.state} state"
            details["recovery_behavior"] = (
                "Scheduler health recovered, but native LocalExecutor task/DAG recovery did not complete successfully"
            )
    except Exception as exc:
        errors.append(f"{type(exc).__name__}: {exc}")
        summary = "Scheduler interruption scenario encountered an error"
        if run_id:
            try:
                available_runs = airflow.list_dag_runs(config.dag_id)
                matching_run = next(
                    (run for run in available_runs if run.run_id == run_id), None
                )
                details["dag_run_lookup_evidence"] = {
                    "available_run_count": len(available_runs),
                    "exact_run_id_found": matching_run is not None,
                }
                if matching_run is not None:
                    details["last_observed_dag_state"] = matching_run.state
            except Exception as evidence_error:
                errors.append(f"DAG-run evidence collection failed: {type(evidence_error).__name__}: {evidence_error}")
            try:
                details["last_observed_task_states"] = {
                    task.task_id: task.state for task in airflow.get_task_states(config.dag_id, run_id)
                }
            except Exception as evidence_error:
                errors.append(f"Task-state evidence collection failed: {type(evidence_error).__name__}: {evidence_error}")
    finally:
        if scheduler_stopped:
            try:
                docker.start_service("airflow-scheduler")
                details["safety_restart_attempted"] = True
            except Exception as restart_error:
                errors.append(f"Safety restart failed: {type(restart_error).__name__}: {restart_error}")
    result = ValidationResult(
        "scheduler_interruption", status, started_at, utc_timestamp(),
        round(time.monotonic() - started, 3), summary, details, errors, [],
    )
    path = write_report(result, config.report_dir)
    result.artifacts.append(str(path))
    # Rewrite once so the report includes its own artifact path.
    path.write_text(__import__("json").dumps(result.to_dict(), indent=2) + "\n", encoding="utf-8")
    return result, path


def run(config: SchedulerInterruptionConfig, docker: DockerClient | None = None) -> tuple[ValidationResult, Path]:
    docker = docker or DockerClient()
    return execute(config, docker, AirflowClient(docker))
