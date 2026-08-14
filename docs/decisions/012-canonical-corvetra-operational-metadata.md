# 012: Canonical Corvetra Operational Metadata

## Status

Accepted.

## Context

The existing `metadata` schema records Airflow/dbt executions, table health,
schema snapshots, and data-health incidents. Those structures must remain
stable, but they do not provide first-class Corvetra pipeline/source identity,
operational alerts, product validation results, or structured technical
evidence for the finalized Round 1 stories.

## Decision

Add normalized environment, source, pipeline, validation-definition,
validation-execution, operational-alert, and technical-event tables to the
existing `metadata` schema. Add nullable Corvetra identity and outcome columns
to `metadata.pipeline_runs` without changing its UUID, DAG, Airflow-run,
uniqueness, or cascade semantics. Operational alerts remain separate from
table-oriented `metadata.data_incidents`; validation executions may optionally
reference dbt node results but are not dependent on dbt.

Use deterministic UUIDv5 identities for the Round 1 seed. Reserved
`corvetra_demo__*` DAG IDs identify seeded provenance without claiming that the
deployed `ecommerce_pipeline` executed canonical demo runs. Existing unmapped
runs are preserved with null additive fields.

Fresh volumes execute numbered scripts 11 and 12 after security initialization.
Existing volumes receive scripts 10 through 12 from `api-db-init`. Each new file
is transactional, advisory-locked, and repeatable. Reapplication may converge
immutable facts but must not reset mutable source status, pipeline/check enabled
state, configured check severity, alert lifecycle, or `created_at` values.

## Consequences

- Canonical Events and Billing stories have coherent relational joins.
- Existing metadata writers and readers remain compatible with nullable
  additions.
- The seed provides only approved runs and evidence; it does not fabricate
  long-term reliability metrics.
- API and frontend integration remain separate work.
