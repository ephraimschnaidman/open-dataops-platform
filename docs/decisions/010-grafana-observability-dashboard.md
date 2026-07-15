# ADR 010: Grafana Observability Dashboard

## Status

Accepted

## Context

The platform persists pipeline execution, dbt results, table health measurements, schema snapshots, and data incidents in PostgreSQL. Operators need a single local view of that information without adding another application codebase or changing collection and detection behavior.

## Decision

Use the free Grafana OSS image to provide the local observability interface. Grafana queries the centralized `metadata` schema rather than operational warehouse tables. Central metadata has stable operational semantics, preserves history, and prevents visualization concerns from coupling directly to domain data models.

Provision the PostgreSQL data source and the **Open DataOps Platform Health** dashboard from version-controlled files. Provisioning makes a fresh clone reproducible, eliminates manual dashboard setup, and keeps query and visualization changes reviewable.

Grafana connects as `grafana_reader`, a dedicated PostgreSQL login with `CONNECT`, metadata-schema `USAGE`, and table `SELECT` privileges only. It receives no write privileges. Its password comes from `.env`; the committed migration creates grants while a one-shot initialization service applies the secret safely at runtime.

## Consequences

Grafana provides mature panels, variables, SQL data sources, and dashboard provisioning with much less implementation and maintenance work than a custom React or Streamlit frontend. The tradeoff is that dashboard behavior is expressed in Grafana JSON and SQL, customization follows Grafana's model, and application-specific workflows would eventually require another interface.

This implementation is intentionally local. It uses one Grafana instance, local Docker volumes, HTTP on loopback, and database password authentication. It does not configure TLS, external identity, high availability, backups, row-level security, alerts, logs, traces, metrics scraping, or automated incident lifecycle operations.
