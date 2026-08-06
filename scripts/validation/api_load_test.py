from __future__ import annotations

import argparse
import concurrent.futures
import json
import statistics
import time
import urllib.error
import urllib.request


def make_request(url: str, token: str | None, timeout: float) -> tuple[bool, float, int]:
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(url, headers=headers)

    started = time.perf_counter()

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response.read()
            elapsed_ms = (time.perf_counter() - started) * 1000
            return 200 <= response.status < 300, elapsed_ms, response.status
    except urllib.error.HTTPError as exc:
        elapsed_ms = (time.perf_counter() - started) * 1000
        return False, elapsed_ms, exc.code
    except Exception:
        elapsed_ms = (time.perf_counter() - started) * 1000
        return False, elapsed_ms, 0


def percentile(values: list[float], percentile_value: float) -> float:
    if not values:
        return 0.0

    ordered = sorted(values)
    index = int(round((len(ordered) - 1) * percentile_value))
    return ordered[index]


def main() -> int:
    parser = argparse.ArgumentParser(description="Simple concurrent API load test")
    parser.add_argument("--url", required=True)
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument("--token")
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args()

    started = time.perf_counter()

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=args.concurrency
    ) as executor:
        futures = [
            executor.submit(
                make_request,
                args.url,
                args.token,
                args.timeout,
            )
            for _ in range(args.requests)
        ]

        results = [future.result() for future in futures]

    total_seconds = time.perf_counter() - started
    successful = [result for result in results if result[0]]
    failed = [result for result in results if not result[0]]
    latencies = [result[1] for result in results]

    status_counts: dict[int, int] = {}
    for _, _, status in results:
        status_counts[status] = status_counts.get(status, 0) + 1

    summary = {
        "url": args.url,
        "requests": args.requests,
        "concurrency": args.concurrency,
        "successful": len(successful),
        "failed": len(failed),
        "success_rate_percent": round(len(successful) / len(results) * 100, 2),
        "total_seconds": round(total_seconds, 3),
        "requests_per_second": round(len(results) / total_seconds, 2),
        "latency_ms": {
            "minimum": round(min(latencies), 2),
            "average": round(statistics.mean(latencies), 2),
            "median": round(statistics.median(latencies), 2),
            "p95": round(percentile(latencies, 0.95), 2),
            "p99": round(percentile(latencies, 0.99), 2),
            "maximum": round(max(latencies), 2),
        },
        "status_counts": status_counts,
    }

    print(json.dumps(summary, indent=2))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())