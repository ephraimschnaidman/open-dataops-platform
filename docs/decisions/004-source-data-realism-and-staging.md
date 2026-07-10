# 004. Source Data Realism and Staging Refinement

## Status

Accepted

## Context

The e-commerce sample data previously behaved like already-clean analytical data. That made the raw loader and staging models easy to validate, but it did not demonstrate a realistic raw-to-staging boundary.

Real source systems often preserve mixed casing, whitespace, status synonyms, regional label differences, missing processor IDs for failed payments, and inconsistent event or device labels. The platform needs small but realistic examples of those issues without breaking row counts or referential integrity.

## Decision

The raw e-commerce CSV fixtures will intentionally preserve realistic source-system imperfections:

- Mixed-case emails and occasional whitespace in text fields.
- Inconsistent region and product category labels.
- Order and payment status variants that represent the same business states.
- Failed payment attempts with missing provider transaction IDs.
- Web event and device labels from different application or analytics conventions.

The Python bootstrap loader will continue loading CSV data into the `raw` schema as-is. It will not clean or standardize the source data.

dbt staging views will perform the first cleaning and standardization pass by trimming strings, lowercasing emails, normalizing categorical values, casting timestamps and numerics, and exposing explicit columns. dbt tests will assert the standardized staging values and relationships.

## Consequences

- Raw tables remain source-like and auditable.
- Staging models now demonstrate meaningful transformation logic.
- Downstream marts can depend on stable, standardized staging values.
- The local bootstrap and dbt validation pipeline remains deterministic.

## Non-Goals

- No raw loader cleaning is introduced.
- No row counts or table names are changed.
- No marts, orchestration, dashboards, or production data quality framework are added in this milestone.
