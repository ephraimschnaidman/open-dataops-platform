# ADR 009: Data Incident Detection

## Status

Accepted

## Context

Health collection records facts about tables, but measurements alone do not say which changes require action. Alerting, investigation, and future root-cause tooling need a durable, queryable record of detected problems.

## Decision

Run incident detection as a separate platform job after health measurement. The job reads only stored row counts, freshness values, and schema snapshots and persists findings in `metadata.data_incidents`. Thresholds and severity mappings are centralized with the monitored-table configuration. New incidents have `OPEN` status; lifecycle management is deferred.

NULL-value detection additionally reads current table contents. It evaluates only
columns listed in `NULL_VALUE_COLUMNS_BY_TABLE`, because nullable attributes such as
anonymous-event customer IDs are valid and scanning every column would create noisy,
non-actionable incidents. The configured columns represent logical NOT NULL data
contracts and generally mirror dbt `not_null` tests. A positive count creates one
`HIGH` `NULL_VALUES` incident per run, table, and column. `HIGH` reflects that a
contract violation can invalidate keys, joins, and measures and needs prompt review;
it is not `CRITICAL` because detection alone does not prove a platform outage.

Row-count and schema comparisons use the most recent earlier successful run for the same DAG. Failed or incomplete runs are poor baselines because their partial output can turn execution failures into misleading data incidents. On the first successful run, the job establishes a baseline and evaluates only freshness.

Detection and measurement remain separate so measurements stay objective and reusable while detection policy can evolve independently. This also keeps collection behavior unchanged and lets detection be retried safely. NULL counts are intentionally not persisted as health metrics in this milestone; the incident records retain the expected zero and observed count.

## Consequences and limitations

Simple percentage thresholds are understandable but do not model seasonality, expected growth, small-table volatility, or business calendars. A fixed percentage can overreact to small denominators and miss meaningful absolute changes on large tables. Freshness can also produce false positives during planned pauses, and intentional schema migrations will look like drift. Configuration therefore belongs in one reviewable location, but suppressions and advanced anomaly models are outside this milestone.

Central incident storage provides one history across tables and incident types, enforces retry idempotency, and creates a stable source for later alert delivery, triage, and root-cause correlation with pipeline and dbt metadata. This milestone does not send alerts, explain causes, automatically resolve incidents, or apply machine learning.
