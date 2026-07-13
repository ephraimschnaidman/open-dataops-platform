# ADR-008: Data Health Metrics

- Status: Accepted
- Date: 2026-07-13

## Context

Successful orchestration and dbt tests show that the pipeline ran and its declared assertions passed, but they do not describe the volume, recency, or physical shape of important datasets. The platform needs a small historical measurement layer before it can responsibly evaluate changes in data health.

## Decision

After centralized execution metadata is recorded, collect row counts, maximum business timestamps, and column-level schema snapshots for selected raw, staging, and marts tables. Store measurements in `metadata.table_health_metrics` and `metadata.table_schema_snapshots`, linked to the same `metadata.pipeline_runs` record.

Row counts provide a useful volume baseline, but a plausible count can still hide stale, malformed, or unexpectedly distributed data. Freshness therefore uses the most meaningful business timestamp for each table, such as order, payment, or event time, rather than database insertion time. The table-to-column mapping is centralized in one configuration module so freshness semantics remain explicit and reviewable.

Schema snapshots capture column name, order, type, and nullability. These measurements establish the historical inputs needed for future anomaly and schema-drift detection, but this milestone performs no comparison, scoring, threshold evaluation, or alerting.

Deterministic identifiers, uniqueness constraints, transactional upserts, and replacement of each table's column snapshot make collection safe to retry for the same pipeline run.

## Consequences

- Each successful ecommerce run has table volume, freshness, and schema evidence connected to its pipeline metadata.
- Missing monitored tables or configured freshness columns fail clearly instead of silently producing incomplete health data.
- Adding a monitored table or changing freshness semantics requires an explicit configuration change.

## Local limitations

Measurements cover a fixed set of ecommerce tables and scan each table for exact counts and maximum timestamps. This is suitable for the small local dataset but can be expensive at production scale. The implementation does not measure distributions, null rates, freshness age, partitions, or semantic quality, and it adds no anomaly detection, thresholds, alerts, dashboards, AI analysis, or external observability services.
