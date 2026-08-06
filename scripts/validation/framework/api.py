from __future__ import annotations

import concurrent.futures
import json
import os
import statistics
import time
import urllib.error
import urllib.parse
import urllib.request
from urllib.parse import quote
from typing import Any

from .models import ApiLoadResult, ApiResponse
from .timing import wait_until


def percentile(values: list[float], quantile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return ordered[int(round((len(ordered) - 1) * quantile))]


def make_request(url: str, token: str | None, timeout: float) -> tuple[bool, float, int]:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    request = urllib.request.Request(url, headers=headers)
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response.read()
            return 200 <= response.status < 300, (time.perf_counter() - started) * 1000, response.status
    except urllib.error.HTTPError as exc:
        return False, (time.perf_counter() - started) * 1000, exc.code
    except Exception:
        return False, (time.perf_counter() - started) * 1000, 0


class ApiClient:
    def __init__(self, base_url: str | None = None, request_timeout: float = 30.0):
        self.base_url = (base_url or os.getenv("VALIDATION_API_BASE_URL", "http://localhost:8000")).rstrip("/")
        self.request_timeout = request_timeout

    def request(self, endpoint: str, token: str | None = None, method: str = "GET",
                data: dict[str, Any] | None = None) -> tuple[int, Any]:
        url = endpoint if endpoint.startswith(("http://", "https://")) else f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        if data is not None and endpoint.rstrip("/").endswith("/auth/token"):
            body = urllib.parse.urlencode(data).encode()
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        else:
            body = json.dumps(data).encode() if data is not None else None
            if body:
                headers["Content-Type"] = "application/json"
        request = urllib.request.Request(url, data=body, headers=headers, method=method)
        with urllib.request.urlopen(request, timeout=self.request_timeout) as response:
            raw = response.read()
            return response.status, json.loads(raw) if raw else None

    def authenticate(self, username: str, password: str) -> str:
        status, payload = self.request("/api/v1/auth/token", method="POST", data={"username": username, "password": password})
        if status // 100 != 2 or not isinstance(payload, dict) or not payload.get("access_token"):
            raise RuntimeError("API authentication failed")
        return str(payload["access_token"])

    def request_captured(
        self, endpoint: str, token: str | None = None, method: str = "GET",
        data: dict[str, Any] | None = None,
    ) -> ApiResponse:
        try:
            status, payload = self.request(endpoint, token, method, data)
            return ApiResponse(status, payload)
        except urllib.error.HTTPError as exc:
            raw = exc.read()
            try:
                payload = json.loads(raw) if raw else None
            except (json.JSONDecodeError, UnicodeDecodeError):
                payload = {"detail": "Non-JSON API error response"}
            return ApiResponse(exc.code, payload)

    def trigger_dag_operation(
        self, dag_id: str, run_id: str, token: str,
    ) -> ApiResponse:
        return self.request_captured(
            f"/api/v1/operations/dags/{quote(dag_id, safe='')}/trigger",
            token=token, method="POST", data={"run_id": run_id},
        )

    def health_check(self) -> bool:
        try:
            status, payload = self.request("/health")
            return status // 100 == 2 and isinstance(payload, dict) and payload.get("status") == "healthy"
        except Exception:
            return False

    def wait_for_health(self, timeout: float) -> bool:
        return wait_until(self.health_check, timeout, 1.0, "API health")

    def measure_requests(self, endpoint: str, request_count: int, concurrency: int,
                         token: str | None = None, timeout: float | None = None) -> ApiLoadResult:
        if request_count < 1 or concurrency < 1:
            raise ValueError("request_count and concurrency must be positive")
        url = endpoint if endpoint.startswith(("http://", "https://")) else f"{self.base_url}/{endpoint.lstrip('/')}"
        started = time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
            results = list(executor.map(lambda _: make_request(url, token, timeout or self.request_timeout), range(request_count)))
        duration = time.perf_counter() - started
        latencies = [item[1] for item in results]
        successful = sum(item[0] for item in results)
        counts: dict[int, int] = {}
        for _, _, status in results:
            counts[status] = counts.get(status, 0) + 1
        return ApiLoadResult(url, request_count, concurrency, successful, request_count - successful,
            round(successful / request_count * 100, 2), round(duration, 3), round(request_count / duration, 2),
            round(min(latencies), 2), round(statistics.mean(latencies), 2), round(statistics.median(latencies), 2),
            round(percentile(latencies, .95), 2), round(percentile(latencies, .99), 2), round(max(latencies), 2), counts)


def load_result_to_legacy_dict(result: ApiLoadResult) -> dict[str, Any]:
    return {"url": result.url, "requests": result.request_count, "concurrency": result.concurrency,
        "successful": result.success_count, "failed": result.failure_count,
        "success_rate_percent": result.success_rate_percent, "total_seconds": result.total_duration_seconds,
        "requests_per_second": result.requests_per_second,
        "latency_ms": {"minimum": result.minimum_latency_ms, "average": result.average_latency_ms,
            "median": result.median_latency_ms, "p95": result.p95_latency_ms, "p99": result.p99_latency_ms,
            "maximum": result.maximum_latency_ms}, "status_counts": result.status_counts}
