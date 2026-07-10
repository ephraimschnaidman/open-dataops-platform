# ADR-001: Why PostgreSQL

## Status

Accepted

## Context

The Open DataOps Platform needed a warehouse foundation that is:

- Free
- Open source
- Easy to run locally
- Production-proven
- Well supported by Docker
- Compatible with dbt
- Familiar to employers

The goal is to build a production-style platform using tools that anyone can run locally. The database should be accessible for contributors, useful for learning, and representative enough of real production systems to support credible data engineering workflows.

## Decision

PostgreSQL was selected as the initial warehouse for the Open DataOps Platform.

PostgreSQL is a mature relational database with strong SQL compliance, excellent Docker support, and broad ecosystem adoption. It works well with dbt through the Postgres adapter and provides strong learning value because its concepts transfer to many production data systems.

PostgreSQL is also easy to run locally while remaining representative of production environments. It provides a practical migration path to managed cloud databases later, including managed Postgres services and warehouse-adjacent architectures that preserve many relational modeling practices.

## Alternatives Considered

### DuckDB

DuckDB is an excellent analytics engine and a strong choice for local analytical workloads. It was not selected as the operational warehouse foundation because it is less representative of the always-on database service pattern this project wants to demonstrate.

### Snowflake

Snowflake is an excellent cloud warehouse and widely used in production. It was not selected because it is paid, requires an external account, and is less suitable for an open-source portfolio project that should run locally for anyone.

### BigQuery

BigQuery is a powerful cloud-native warehouse. It was not selected because it requires Google Cloud Platform and introduces unnecessary external dependencies for the current local-first platform foundation.

### SQLite

SQLite is lightweight and easy to run. It was not selected because it lacks important database features needed for a realistic data platform, especially around schemas, concurrent service access, and production-style warehouse workflows.

## Consequences

Positive consequences:

- Simple local development
- Portable setup
- Open-source foundation
- Familiar to recruiters and employers
- Docker-friendly operation
- Supports future platform phases

Negative consequences:

- Not a distributed warehouse
- Less suitable for very large analytical workloads
- Some future optimizations may differ from cloud warehouses

PostgreSQL provides the best balance between realism, accessibility, maintainability, and educational value for the Open DataOps Platform.
