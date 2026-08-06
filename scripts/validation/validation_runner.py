from __future__ import annotations

import argparse
import os

from framework.docker import DockerClient
from framework.models import ValidationStatus
from framework.reporting import print_summary
from scenarios.postgres_interruption import (
    PostgresInterruptionConfig, run as run_postgres_interruption,
)
from scenarios.pipeline_recovery import InvalidInputConfig, run as run_invalid_input
from scenarios.scheduler_interruption import (
    SchedulerInterruptionConfig, run as run_scheduler_interruption,
)

AVAILABLE = {"scheduler-interruption", "postgres-interruption", "invalid-input"}
NOT_IMPLEMENTED = {"api-restart", "concurrent-api-pipeline"}


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description="Open DataOps production validation runner")
    value.add_argument("scenario", choices=["list", *sorted(AVAILABLE | NOT_IMPLEMENTED)])
    value.add_argument("--compose-file", default=os.getenv("VALIDATION_COMPOSE_FILE", "docker-compose.yml"))
    value.add_argument("--validation-compose-file", default=os.getenv("VALIDATION_OVERRIDE_FILE", "docker-compose.validation.yml"))
    value.add_argument("--dag-id", default=os.getenv("VALIDATION_DAG_ID", "ecommerce_pipeline"))
    value.add_argument("--target-task", default=os.getenv("VALIDATION_TARGET_TASK", "run_dbt"))
    value.add_argument("--interruption-seconds", type=float, default=float(os.getenv("VALIDATION_INTERRUPTION_SECONDS", "10")))
    value.add_argument("--timeout", type=float, default=float(os.getenv("VALIDATION_TIMEOUT", "600")))
    value.add_argument("--report-dir", default=os.getenv("VALIDATION_REPORT_DIR", "runtime/validation/reports"))
    value.add_argument("--keep-work-directory", action="store_true")
    value.add_argument("--invalid-value", default="bank_transfer")
    return value


def main() -> int:
    args = parser().parse_args()
    if args.scenario == "list":
        print("Available:")
        for name in sorted(AVAILABLE):
            print(f"  {name}")
        print("Not implemented:")
        for name in sorted(NOT_IMPLEMENTED):
            print(f"  {name}")
        return 0
    if args.scenario in NOT_IMPLEMENTED:
        print(f"Scenario '{args.scenario}' is NOT_IMPLEMENTED")
        return 3
    if args.timeout <= 0 or args.interruption_seconds < 0:
        parser().error("--timeout must be positive and --interruption-seconds must not be negative")
    docker = DockerClient(args.compose_file, args.validation_compose_file)
    if args.scenario == "scheduler-interruption":
        config = SchedulerInterruptionConfig(
            args.dag_id, args.target_task, args.interruption_seconds,
            args.timeout, args.report_dir,
        )
        result, path = run_scheduler_interruption(config, docker)
    elif args.scenario == "postgres-interruption":
        postgres_config = PostgresInterruptionConfig(
            args.dag_id, args.target_task, args.interruption_seconds,
            args.timeout, args.report_dir,
        )
        result, path = run_postgres_interruption(postgres_config, docker)
    else:
        invalid_config = InvalidInputConfig(
            dag_id=args.dag_id, timeout=args.timeout, report_dir=args.report_dir,
            invalid_value=args.invalid_value,
            keep_work_directory=args.keep_work_directory,
        )
        result, path = run_invalid_input(invalid_config, docker)
    print_summary(result, path)
    return 0 if result.status is ValidationStatus.PASS else (1 if result.status is ValidationStatus.FAIL else 2)


if __name__ == "__main__":
    raise SystemExit(main())
