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
    Authenticated JSON clients
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

Authenticated endpoint requests follow:

```text
Request
  -> Authentication
  -> JWT validation
  -> Current user lookup
  -> RBAC
  -> Route
  -> Service
  -> Repository
  -> PostgreSQL
```

Routes define HTTP contracts and parameter validation. Services assemble
validated response models. Repositories contain parameterized SQL and database
access. The initial API scope is read-only.

## Authentication and authorization

Users, roles, and assignments are stored in `security.users`,
`security.roles`, and `security.user_roles`. Passwords are stored only as
Argon2 hashes. OAuth2 form login at `POST /api/v1/auth/token` issues short-lived
HS256 JWT access tokens whose subject is the stable PostgreSQL user UUID.

JWT decoding strictly validates subject, issuer, audience, issued-at,
not-before, expiration, and token-ID claims. Every authenticated request then
reloads active state and current roles from PostgreSQL. PostgreSQL is
authoritative for user activity and roles; JWT role claims are not trusted.
Deactivation and role changes therefore affect already-issued tokens
immediately.

Reusable FastAPI dependencies provide current-user, active-user, and
required-role checks. One role dependency is attached when each operational
router is included. `Admin`, `Operator`, and `ReadOnly` currently have read
access to all operational endpoints; future endpoints can differentiate roles
without redesigning authentication.

Public resources are:

- `GET /health`;
- `POST /api/v1/auth/token`; and
- `/docs`, `/redoc`, and `/openapi.json` when `API_DOCS_ENABLED=true`.

All existing read-only incident, metric, schema-snapshot, dbt-metadata, and
pipeline-history operations require authentication. Health and login remain
public. Invalid credentials return HTTP 401 with
`WWW-Authenticate: Bearer`; an active user lacking an accepted role receives
HTTP 403.

Required configuration consists of `API_JWT_SECRET_KEY`,
`API_JWT_ACCESS_TOKEN_EXPIRE_MINUTES`, `API_JWT_ISSUER`, `API_JWT_AUDIENCE`,
and `API_DOCS_ENABLED`. HS256 is fixed in code rather than selected from token
headers or configuration.

Fresh volumes execute `10_create_security_tables.sql` during ordered PostgreSQL
initialization. Existing volumes use the one-shot `api-db-init` service. The
migration is transactional, concurrency-locked, idempotent, and seeds the three
roles but no users. Users are provisioned securely with:

```bash
docker compose exec api python -m platform.api.cli.create_user \
  <username> --role <role>
```

## Implemented endpoints

| Endpoint | Purpose |
| --- | --- |
| `GET /health` | Public service and PostgreSQL connectivity health |
| `POST /api/v1/auth/token` | Public OAuth2 password-form token issuance |
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

## Security limitations and scope boundaries

- Access tokens have no refresh-token flow or per-token revocation list.
- User deactivation and role changes take effect immediately because each
  authenticated request reloads authorization state from PostgreSQL.
- TLS is required outside local loopback development.
- The API still uses the broad `dataops` database user.
- OAuth providers, SSO, MFA, registration, password reset, email verification,
  billing, and multi-tenancy are outside the current scope.
- Pipeline execution, incident mutation, and complete auditing of runs that
  fail before metadata collection remain deferred.
