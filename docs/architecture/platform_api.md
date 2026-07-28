# Platform API Architecture

## Purpose and scope

The platform API is a standalone FastAPI service in Docker Compose. It exposes
selected operational metadata already persisted in PostgreSQL as read-only JSON.
It is not an execution or metadata-processing layer.

```text
Airflow / dbt / platform jobs
              |
              v
     PostgreSQL metadata
              |
              v
           FastAPI
              |
              v
         JSON clients
```

Airflow, dbt, and platform jobs remain responsible for orchestration,
transformation, metadata collection, health measurement, schema drift
detection, and incident generation. The API consumes the resulting PostgreSQL
records. It does not execute Airflow or dbt, parse dbt artifacts directly,
mutate incidents, recalculate metrics, perform schema drift detection, or modify
operational tables.

## Technical design

The API uses:

- FastAPI with Pydantic request and response validation;
- psycopg 3 and `psycopg_pool` for asynchronous PostgreSQL access;
- environment-based configuration;
- an API-specific dependency file and dedicated Dockerfile;
- a standalone Compose service bound to `localhost:8000`;
- generated OpenAPI documentation at `/docs` and `/openapi.json`; and
- safe HTTP error responses that do not disclose SQL, credentials, connection
  strings, or stack traces.

Endpoint implementations follow:

```text
route -> service -> repository -> PostgreSQL
```

Routes define HTTP contracts and parameter validation. Services assemble
validated response models. Repositories contain parameterized SQL and database
access. The initial API scope is read-only.

## Implemented endpoints

| Endpoint | Purpose |
| --- | --- |
| `GET /health` | Report service and PostgreSQL connectivity health |
| `GET /api/v1/incidents` | List persisted data incidents and available context |
| `GET /api/v1/incidents/{incident_id}` | Retrieve one persisted incident |
| `GET /api/v1/metrics` | List persisted table health measurements |
| `GET /api/v1/schema-snapshots` | List persisted table schema snapshots |
| `GET /api/v1/dbt-metadata` | List persisted dbt node execution results |
| `GET /api/v1/pipelines` | List pipeline runs recorded by metadata collection |

List endpoints support bounded limit/offset pagination and filters backed
directly by their persisted columns. Filters include identifiers and relevant
status, resource, node, table, schema, and pipeline fields where supported.
Invalid query parameters are rejected through FastAPI validation.

## Persisted data sources

The API reads operational metadata from:

- `metadata.data_incidents`;
- `metadata.incident_context`;
- `metadata.table_health_metrics`;
- `metadata.table_schema_snapshots`;
- `metadata.dbt_node_results`; and
- `metadata.pipeline_runs`.

The pipelines endpoint represents records persisted by the metadata collection
stage. It is not guaranteed to include Airflow DAG runs that fail before
metadata collection occurs. Complete execution auditing, including failed runs
that terminate early, remains a deferred enhancement.

## Initial scope boundaries

Task #6 does not include authentication, authorization, user accounts,
monetization, a frontend, cloud deployment, pipeline execution through the API,
incident acknowledgement or mutation, or major database redesign.
