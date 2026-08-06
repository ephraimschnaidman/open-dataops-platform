from __future__ import annotations

import json
import re
import uuid
from typing import Any

from .docker import DockerClient
from .models import AirflowDagRun, AirflowTaskState
from .timing import utc_timestamp, wait_until

TERMINAL_DAG_STATES = {"success", "failed"}
KNOWN_TASK_STATES = {"queued", "running", "success", "failed", "upstream_failed", "skipped", "none"}


def parse_airflow_table(output: str) -> list[dict[str, str]]:
    rows: list[list[str]] = []
    for line in output.splitlines():
        stripped = line.strip()
        if not stripped or "|" not in stripped or stripped.startswith(("+", "FutureWarning", "/")):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) > 1 and not all(re.fullmatch(r"[-=: ]*", cell) for cell in cells):
            rows.append(cells)
    if not rows:
        return []
    header_index = None
    headers: list[str] = []
    for index, row in enumerate(rows):
        candidate = [re.sub(r"\s+", "_", value.strip().lower()) for value in row]
        if "dag_id" in candidate and ({"run_id", "dag_run_id", "task_id"} & set(candidate)):
            header_index = index
            headers = candidate
            break
    if header_index is None:
        return []
    return [dict(zip(headers, row)) for row in rows[header_index + 1:] if len(row) == len(headers)]


def _value(row: dict[str, str], *names: str) -> str:
    for name in names:
        if name in row:
            return row[name]
    return ""


def _dag_run_from_mapping(row: dict[str, Any]) -> AirflowDagRun | None:
    dag_id = str(row.get("dag_id", ""))
    run_id = str(row.get("run_id") or row.get("dag_run_id") or "")
    if not dag_id or not run_id:
        return None
    return AirflowDagRun(
        dag_id, run_id, str(row.get("state", "")).lower(),
        str(row.get("execution_date") or row.get("logical_date") or "") or None,
        str(row.get("start_date") or "") or None,
        str(row.get("end_date") or "") or None,
    )


def parse_dag_runs_json(output: str) -> list[AirflowDagRun]:
    """Decode Airflow JSON even when informational lines precede it."""
    decoder = json.JSONDecoder()
    for index, character in enumerate(output):
        if character not in "[{":
            continue
        try:
            payload, _ = decoder.raw_decode(output[index:])
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, list):
            continue
        runs = [run for item in payload if isinstance(item, dict)
                if (run := _dag_run_from_mapping(item)) is not None]
        if runs or not payload:
            return runs
    raise ValueError("Airflow output did not contain a JSON DAG-run list")


def parse_dag_runs(output: str) -> list[AirflowDagRun]:
    runs = []
    for row in parse_airflow_table(output):
        run = _dag_run_from_mapping(row)
        if run is not None:
            runs.append(run)
    return runs


def parse_task_states(output: str, dag_id: str, run_id: str) -> list[AirflowTaskState]:
    states = []
    for row in parse_airflow_table(output):
        task_id = _value(row, "task_id")
        state = (_value(row, "state") or "none").lower()
        if task_id:
            states.append(AirflowTaskState(dag_id, run_id, task_id, state if state in KNOWN_TASK_STATES else state))
    return states


class AirflowClient:
    def __init__(self, docker: DockerClient, scheduler_service: str = "airflow-scheduler"):
        self.docker = docker
        self.scheduler_service = scheduler_service

    def _airflow(self, arguments: list[str]):
        return self.docker.compose_exec(self.scheduler_service, ["airflow", *arguments])

    def trigger_dag(self, dag_id: str, run_id: str | None = None) -> AirflowDagRun:
        run_id = run_id or f"validation__{utc_timestamp().replace(':', '').replace('-', '')}__{uuid.uuid4().hex[:8]}"
        self._airflow(["dags", "trigger", "--run-id", run_id, dag_id])
        return AirflowDagRun(dag_id, run_id, "queued")

    def list_dag_runs(self, dag_id: str) -> list[AirflowDagRun]:
        output = self._airflow(
            ["dags", "list-runs", "--dag-id", dag_id, "--output", "json"]
        ).stdout
        try:
            return parse_dag_runs_json(output)
        except ValueError:
            # Retain compatibility with installations that ignore --output and
            # emit the standard pipe-delimited table.
            return parse_dag_runs(output)

    def find_dag_run(self, dag_id: str, run_id: str) -> AirflowDagRun | None:
        return next(
            (run for run in self.list_dag_runs(dag_id)
             if run.dag_id == dag_id and run.run_id == run_id),
            None,
        )

    def get_dag_run(self, dag_id: str, run_id: str) -> AirflowDagRun:
        run = self.find_dag_run(dag_id, run_id)
        if run is not None:
            return run
        raise LookupError(f"DAG run not found: {dag_id}/{run_id}")

    def get_task_states(self, dag_id: str, run_id: str) -> list[AirflowTaskState]:
        result = self._airflow(["tasks", "states-for-dag-run", dag_id, run_id])
        return parse_task_states(result.stdout, dag_id, run_id)

    def get_task_state(self, dag_id: str, run_id: str, task_id: str) -> AirflowTaskState:
        result = self._airflow(["tasks", "state", dag_id, task_id, run_id])
        state = next((line.strip().lower() for line in reversed(result.stdout.splitlines()) if line.strip().lower() in KNOWN_TASK_STATES), "none")
        return AirflowTaskState(dag_id, run_id, task_id, state)

    def wait_for_task_state(self, dag_id: str, run_id: str, task_id: str,
                            expected: set[str], timeout: float) -> AirflowTaskState:
        return wait_until(
            lambda: (item if (item := self.get_task_state(dag_id, run_id, task_id)).state in expected else None),
            timeout, 2.0, f"task {task_id} to enter {sorted(expected)}",
        )

    def wait_for_dag_terminal_state(self, dag_id: str, run_id: str, timeout: float) -> AirflowDagRun:
        def terminal_run() -> AirflowDagRun | None:
            run = self.find_dag_run(dag_id, run_id)
            return run if run is not None and run.state in TERMINAL_DAG_STATES else None

        return wait_until(
            terminal_run,
            timeout, 3.0, f"DAG run {run_id} to reach a terminal state",
        )

    def wait_for_scheduler_healthy(self, timeout: float):
        return self.docker.wait_for_service_healthy(self.scheduler_service, timeout)
