# ADR 011: Metadata-Driven Incident Context

## Status

Accepted

## Context

An incident is a durable detection fact. Operators also need an explanation, but stored
sentences are difficult to query, localize, or safely evolve and force every consumer to
depend on one presentation policy.

## Decision

Store structured `stale_data_v1` context in `metadata.incident_context`, one row per
incident and version. The source-of-truth fields are qualified table, controlled
evaluation status, recorded severity, separate numeric expected and observed freshness
hours, and a controlled recommended-action code. Numeric values support comparison and
aggregation without reparsing display strings. Controlled status and action codes give
consumers stable semantics and prevent prose changes from becoming schema changes.

Human-readable what-happened, why-it-matters, and next-step messages are deterministic
presentation functions in `platform/context/render_incident_context.py`; rendered prose
is never persisted as authoritative metadata. The recommendation remains investigative
and does not assert root cause, ownership, business impact, or downstream impact.

Generation transactionally upserts `(incident_id, context_version)`. A retry retains
`context_id` and `created_at`, and refreshes structured values, `generated_at`, and
`updated_at`.

The idempotent migration adds the structured columns, backfills table identity and
severity from `data_incidents`, parses detector strings into numeric hours, derives the
status, validates required values, adds controlled-value constraints, and only then
drops prose columns. Existing identifiers and timestamps are retained. Values that
cannot be parsed remain nullable and receive `UNKNOWN`; missing required identity or
severity aborts the transaction rather than losing data.

Operational execution logs are separate from persistent incident metadata because they
describe job activity rather than domain state. The standalone job appends to
`runtime/logs/jobs/incident_context.log`; Python's daily timed rotation retains 30
backups. Handler-managed rotation avoids unsafe, ad hoc deletion or truncation of an
active log.

## Consequences and limitations

Version 1 supports only `STALE_DATA` and the detector's current hours format. It does not
add Airflow or Grafana changes, alerts, delivery integrations, other incident types,
lineage, ownership, business-impact scoring, root-cause analysis, AI/LLM generation, or
automatic remediation.
