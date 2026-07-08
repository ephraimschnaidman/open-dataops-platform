# 003. dbt Core for Warehouse Transformations

## Status

Accepted

## Context

The platform now has a local PostgreSQL warehouse and a deterministic bootstrap loader for raw e-commerce sample data. We need a simple transformation foundation that can model raw data into cleaner staging views without introducing orchestration, dashboards, or production ingestion concerns too early.

## Decision

We will use dbt Core with the Postgres adapter for local warehouse transformations.

The dbt project will live under `platform/dbt` and connect to the local Docker Postgres database. Configuration will use environment variables where appropriate, with local development defaults matching the Docker Compose warehouse.

The first dbt scope is limited to e-commerce staging models:

- Raw tables are declared as dbt sources.
- Staging models are materialized as views in the `staging` schema.
- Basic tests check unique and not null identifiers, key relationships, and accepted order/payment statuses.

## Consequences

- Transformations have a clear home under the platform layer.
- Raw-to-staging logic is documented and testable with dbt.
- The initial dbt setup stays small enough for local development.
- Future milestones can add marts, orchestration, documentation generation, and CI checks.

## Non-Goals

- No marts are added yet.
- No Airflow orchestration is added yet.
- No Metabase dashboards are added yet.
- No production ingestion or incremental loading strategy is introduced by this decision.
