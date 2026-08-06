from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Callable, TypeVar

T = TypeVar("T")


class WaitTimeoutError(TimeoutError):
    """Raised when an explicitly bounded wait does not complete."""


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def wait_until(
    predicate: Callable[[], T], timeout: float, interval: float = 1.0,
    description: str = "condition",
) -> T:
    if timeout <= 0 or interval <= 0:
        raise ValueError("timeout and interval must be positive")
    deadline = time.monotonic() + timeout
    while True:
        value = predicate()
        if value:
            return value
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise WaitTimeoutError(f"Timed out after {timeout:g}s waiting for {description}")
        time.sleep(min(interval, remaining))


def retry(
    operation: Callable[[], T], attempts: int, timeout: float,
    interval: float = 1.0,
) -> T:
    if attempts < 1:
        raise ValueError("attempts must be at least one")
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            return operation()
        except Exception as exc:
            last_error = exc
            if attempt + 1 == attempts or time.monotonic() >= deadline:
                break
            time.sleep(min(interval, max(0, deadline - time.monotonic())))
    raise WaitTimeoutError(
        f"Operation failed after {attempts} attempts within {timeout:g}s: {last_error}"
    ) from last_error
