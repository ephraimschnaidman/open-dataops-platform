# ADR 011: Metadata-Driven Incident Context

## Status

Accepted

## Context

An incident record captures the detected condition, but an operator also needs a concise explanation of what was observed, why the condition deserves attention, and a safe next investigative step. Those explanations may evolve independently from incident detection and lifecycle state.

## Decision

Store generated explanations in `metadata.incident_context`, separate from `metadata.data_incidents`, with one row per incident and context version. Separation preserves the incident as the durable detection fact while allowing explanations to be regenerated or new rendering policies to coexist without changing the original record.

Version 1 supports only `STALE_DATA` and uses the explicit version `stale_data_v1`. Freshness incidents already provide the metadata needed for a trustworthy explanation: table identity, threshold, observed age, severity, and status. Other incident types require their own carefully reviewed semantics and are deferred.

Generation is deterministic and rule-based. Templates live in one version-controlled rules module, use only stored incident metadata, and make no external or LLM calls. Retrying the job transactionally upserts the same incident and version rather than creating a duplicate. Versioning makes output policy visible, reproducible, and extensible without silently changing the meaning of previously generated context.

The recommended next step is explicitly an investigation recommendation. It must not be presented as a proven root cause: stale data establishes an observation about age, not why ingestion stopped or whether the threshold is wrong.

## Consequences and limitations

The stored text is predictable, testable, and queryable, but deliberately less flexible than generated prose. Version 1 does not infer downstream impact, ownership, business criticality, historical correlation, or root cause.

Alert delivery, Airflow integration, other incident types, AI or LLM generation, lineage analysis, business-impact scoring, automatic remediation, dashboard changes, and incident lifecycle automation are intentionally out of scope.
