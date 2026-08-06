from __future__ import annotations

import argparse
import json

from framework.api import ApiClient, load_result_to_legacy_dict, make_request, percentile

__all__ = ["main", "make_request", "percentile"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Simple concurrent API load test")
    parser.add_argument("--url", required=True)
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument("--token")
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args()

    result = ApiClient(request_timeout=args.timeout).measure_requests(
        args.url, args.requests, args.concurrency, args.token, args.timeout
    )
    summary = load_result_to_legacy_dict(result)

    print(json.dumps(summary, indent=2))
    return 0 if result.failure_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
