# ADR-006: Separate Orchestration from Platform Jobs

- Status: Accepted
- Date: 2026-07-10

## Context

The platform needs workflow coordination, retries, operational visibility, and a path to scheduled execution. The existing bootstrap and dbt commands can already run independently. Embedding their implementation in an Airflow DAG would couple data work to one orchestrator and make local testing and reuse harder.

## Decision

Reusable, single-purpose entrypoints live in `platform/jobs`. Each job owns one operation, provides `main()`, logs its progress, and returns a process exit code. Apache Airflow uses a manually triggered `ecommerce_pipeline` DAG to execute those entrypoints in dependency order. The DAG contains no loading or transformation logic.

Airflow uses LocalExecutor and a dedicated `airflow` database on the existing PostgreSQL service. Its metadata remains isolated from warehouse data while keeping local infrastructure small.

## Consequences

- Jobs can be run and tested without Airflow.
- Scripts and future APIs, CI systems, Prefect, or Dagster can invoke the same stable entrypoints.
- Airflow is limited to dependencies, retries, timeouts, logs, and execution state.
- Business logic has one canonical implementation instead of being duplicated in DAG files.
- The local Airflow image must include the Python and dbt dependencies required by the jobs.
- Changing an already-initialized Postgres volume requires creating the Airflow database manually or resetting the local volume.
