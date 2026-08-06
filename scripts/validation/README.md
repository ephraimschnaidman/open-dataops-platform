# Python production validation framework

This directory contains evidence-oriented validation tooling for Docker Compose,
Airflow, PostgreSQL, and the platform API. It does not change DAGs, schemas, dbt
models, or the production API contract.

## Prerequisites

- Python 3.10 or newer
- Docker Desktop with Compose v2
- The platform images built and services initialized
- Repository `.env` values configured; never commit secrets

Run commands from the repository root. The validation override currently selects
the Tier B ecommerce dataset.

## Architecture

`framework/` holds typed command, Docker, Airflow, API, PostgreSQL, timing, and
reporting helpers. `scenarios/` holds orchestration only. The command layer always
uses argument arrays and captures stdout, stderr, exit status, timestamps, and
duration. Reports are UTF-8 JSON under `runtime/validation/reports/` by default.

The first complete scenario is `scheduler-interruption`. The API restart,
PostgreSQL interruption, concurrent API/pipeline, and pipeline recovery entry
points are explicitly marked `NOT_IMPLEMENTED` and return no false PASS result.

## Running

List scenario status:

```console
python scripts/validation/validation_runner.py list
```

Run scheduler interruption:

```console
python scripts/validation/validation_runner.py scheduler-interruption
```

The runner waits for `run_dbt` to be running, stops the scheduler for 10 seconds,
starts it, waits for container health, and records the native outcome. With
LocalExecutor, stopping the scheduler can terminate its active child task; a
failed DAG is reported as `FAIL`, never rewritten as recovery success. No task is
cleared or retried by the scenario.

Options include `--compose-file`, `--validation-compose-file`, `--dag-id`,
`--target-task`, `--interruption-seconds`, `--timeout`, and `--report-dir`.
Equivalent environment variables are `VALIDATION_COMPOSE_FILE`,
`VALIDATION_OVERRIDE_FILE`, `VALIDATION_DAG_ID`, `VALIDATION_TARGET_TASK`,
`VALIDATION_INTERRUPTION_SECONDS`, `VALIDATION_TIMEOUT`, and
`VALIDATION_REPORT_DIR`. API helpers additionally support callers using
`VALIDATION_API_BASE_URL`, `VALIDATION_API_USERNAME`, and
`VALIDATION_API_PASSWORD`; secret values are not logged or placed in reports.

## Reports

Each timestamped, non-overwriting JSON report contains `test_name`, `status`, UTC
start/completion timestamps, duration, summary, details, errors, and artifacts.
Scenario details preserve the run ID, interruption timestamps, recovery duration,
final DAG state, and all final task states.

## Safety

Validation scenarios intentionally interrupt services. Never run them against an
uncontrolled production environment. Use a dedicated validation deployment,
confirm the Compose files and dataset first, and keep credentials in environment
configuration only. If the scheduler scenario errors while the service is
stopped, it makes and records a safety restart attempt.

## Adding a scenario

Create a small module under `scenarios/`, compose existing framework clients,
bound every wait with an explicit timeout, collect evidence before classification,
write a `ValidationResult`, and add the command to the runner only when implemented.
Mock external processes in unit tests; keep live-Docker tests separately marked.
