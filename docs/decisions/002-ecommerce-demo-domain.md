# 002. E-Commerce Demo Domain

## Status

Accepted

## Context

Open DataOps Platform needs realistic sample data to demonstrate warehouse loading, data quality, transformations, metadata, and analytics workflows. The platform itself must remain domain-agnostic, so any business-specific examples should live outside core platform infrastructure.

## Decision

We will use e-commerce as the first demo domain. The domain will live under `domains/ecommerce` and provide static CSV fixtures for customers, products, orders, order items, payments, and web events.

The sample data is intentionally small but relational:

- Customers place orders.
- Orders contain order items.
- Order items reference products.
- Payments reference orders.
- Web events may reference customers, products, and completed orders.

The dataset includes realistic edge cases such as failed payments, refunded payments, canceled orders, repeat customers, unsold products, anonymous browsing, and non-converting sessions.

## Consequences

- The platform foundation stays reusable for other domains.
- Future ingestion work can use the CSVs as stable inputs.
- Future dbt or warehouse modeling work can demonstrate joins, quality checks, and business metrics without inventing data later.
- E-commerce-specific assumptions should remain inside `domains/ecommerce` or downstream demo models, not platform-wide configuration.

## Non-Goals

- No ingestion code is added in this decision.
- No warehouse tables are created for the demo domain yet.
- No Airflow, dbt, Metabase, or observability services are introduced by this milestone.
