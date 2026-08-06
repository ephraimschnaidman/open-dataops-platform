from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class ValidationStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    ERROR = "ERROR"


@dataclass(frozen=True)
class CommandResult:
    command: list[str]
    return_code: int
    stdout: str
    stderr: str
    started_at: str
    completed_at: str
    duration_seconds: float


@dataclass(frozen=True)
class ContainerState:
    name: str
    status: str
    health: str | None = None
    running: bool = False


@dataclass(frozen=True)
class AirflowTaskState:
    dag_id: str
    run_id: str
    task_id: str
    state: str


@dataclass(frozen=True)
class AirflowDagRun:
    dag_id: str
    run_id: str
    state: str
    execution_date: str | None = None
    start_date: str | None = None
    end_date: str | None = None


@dataclass(frozen=True)
class ApiLoadResult:
    url: str
    request_count: int
    concurrency: int
    success_count: int
    failure_count: int
    success_rate_percent: float
    total_duration_seconds: float
    requests_per_second: float
    minimum_latency_ms: float
    average_latency_ms: float
    median_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    maximum_latency_ms: float
    status_counts: dict[int, int]


@dataclass(frozen=True)
class ApiResponse:
    status_code: int
    payload: Any


@dataclass
class ValidationResult:
    test_name: str
    status: ValidationStatus
    started_at: str
    completed_at: str
    duration_seconds: float
    summary: str
    details: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    artifacts: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["status"] = self.status.value
        return value
