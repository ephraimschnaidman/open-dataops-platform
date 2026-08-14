# Platform API Architecture

## Purpose and scope

The platform API is a standalone FastAPI service in Docker Compose. It exposes
selected PostgreSQL operational metadata as read-only JSON and provides a
separate operations boundary for live Airflow reads and safe triggering of
existing DAGs. It is not a metadata-processing, workflow-authoring, or direct
database-mutation layer.

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

Live Airflow operations follow a separate layered path:

```text
FastAPI operations router
          |
          v
PipelineOperationsService
          |
          v
OrchestratorClient
          |
          v
AirflowClient -> Airflow 2.10.5 stable REST API
```

Airflow, dbt, and platform jobs remain responsible for orchestration,
transformation, metadata collection, health measurement, schema drift
detection, and incident generation. The API consumes the resulting PostgreSQL
records. Only the operations trigger route initiates an existing Airflow DAG;
the API does not invoke dbt directly, parse dbt artifacts directly,
mutate incidents, recalculate metrics, perform schema drift detection, or modify
operational tables. It does not create or edit DAGs.

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
access. Operations routes remain thin: they contain no HTTP client, Airflow URL,
response-parsing, or Airflow-specific behavior. `PipelineOperationsService`
owns platform behavior such as generated run IDs. `OrchestratorClient` defines
platform-neutral contracts, and `AirflowClient` alone translates them to and
from the Airflow stable REST API. Raw Airflow dictionaries never escape the
client.

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
router is included. `Admin`, `Operator`, and `ReadOnly` have read access to all
operational endpoints. Write operations add a second dependency allowing only
`Admin` and `Operator`; `ReadOnly` receives HTTP 403 before route service
execution. Anonymous requests receive HTTP 401.

Public resources are:

- `GET /health`;
- `POST /api/v1/auth/token`; and
- `/docs`, `/redoc`, and `/openapi.json` when `API_DOCS_ENABLED=true`.

All existing read-only incident, metric, schema-snapshot, dbt-metadata, and
pipeline-history operations require authentication. Health and login remain
public. Invalid credentials return HTTP 401 with
`WWW-Authenticate: Bearer`; an active user lacking an accepted role receives
HTTP 403.

Required authentication configuration consists of `API_JWT_SECRET_KEY`,
`API_JWT_ACCESS_TOKEN_EXPIRE_MINUTES`, `API_JWT_ISSUER`, `API_JWT_AUDIENCE`,
and `API_DOCS_ENABLED`. HS256 is fixed in code rather than selected from token
headers or configuration.

Airflow operations use `AIRFLOW_API_URL`, `AIRFLOW_API_USERNAME`,
`AIRFLOW_API_PASSWORD`, and `AIRFLOW_API_VERIFY_TLS`. The shared asynchronous
HTTP client has explicit connect/read/write/pool timeouts, bounded connections,
disabled redirect following, configurable TLS verification, and no automatic
POST retry. Airflow URLs, credentials, authorization headers, raw problem
bodies, and trigger configuration are excluded from API errors and logs.

Fresh volumes execute `10_create_security_tables.sql` during ordered PostgreSQL
initialization. Existing volumes use the one-shot `api-db-init` service. The
migration is transactional, concurrency-locked, idempotent, and seeds the three
roles but no users. Users are provisioned securely with:

```bash
docker compose exec api python -m platform.api.cli.create_user \
  <username> --role <role>
```

The initializer then executes `11_create_corvetra_canonical_model.sql` and
`12_seed_corvetra_round1.sql`. These transactional, advisory-locked files apply
the additive canonical metadata model and its deterministic Round 1 records to
both fresh and existing volumes. The schema migration does not replace existing
pipeline-run, dbt-result, health, schema-snapshot, data-incident, or incident-
context identities. Seed reapplication preserves operator-modifiable source,
pipeline, validation-definition, and alert state.

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
| `GET /api/v1/operations/dags` | List live Airflow DAGs |
| `GET /api/v1/operations/dags/{dag_id}` | Get one live DAG |
| `GET /api/v1/operations/runs` | List live DAG runs, optionally filtered by DAG |
| `GET /api/v1/operations/dags/{dag_id}/runs/{run_id}` | Get one live DAG run |
| `GET /api/v1/operations/dags/{dag_id}/runs/{run_id}/tasks` | List task instances for a run |
| `GET /api/v1/operations/dags/{dag_id}/runs/{run_id}/tasks/{task_id}/logs` | Read validated task log coordinates |
| `POST /api/v1/operations/dags/{dag_id}/trigger` | Trigger an existing DAG (Admin/Operator) |
| `POST /api/v1/operations/dags/{dag_id}/runs/{run_id}/retry` | Capability endpoint; HTTP 501 |
| `POST /api/v1/operations/dags/{dag_id}/runs/{run_id}/cancel` | Capability endpoint; HTTP 501 |

List endpoints support bounded limit/offset pagination and filters backed
directly by their persisted columns. Filters include identifiers and relevant
status, resource, node, table, schema, and pipeline fields where supported.
Invalid query parameters are rejected through FastAPI validation.

### Trigger contract and idempotency

The trigger request permits only safe Airflow-backed fields: optional
`run_id`, optional `logical_date`, and optional JSON-object `conf`. A supplied
run ID is preserved. When omitted, the service generates a clear
`platform__manual__<UTC timestamp>__<UUID>` identifier. The run ID is the
idempotency key together with the DAG ID; duplicate or conflicting triggers
return HTTP 409 and are not retried automatically.

Successful triggers return a platform-neutral operation/run model containing
the operation ID, DAG ID, run ID, state, logical date, start date, and external
trigger indicator. Airflow configuration and raw response fields are not
exposed. Missing resources return HTTP 404. Upstream connectivity,
authentication, permission, timeout, or malformed-response failures return a
safe HTTP 503.

### Capability-driven retry and cancellation

Airflow 2.10.5's stable API provides clearing and state-mutation primitives but
does not expose a safe whole-run retry contract with unambiguous semantics.
Likewise, it does not provide cancellation semantics that guarantee active
tasks stop. The platform does not simulate either operation through database
updates, undocumented endpoints, task-state mutation, process termination, or
hidden clearing. The retry and cancel routes therefore intentionally return
HTTP 501 `Pipeline operation not supported`. This is a documented capability
limit, not a defect.

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
- DAG creation/editing, scheduler UI functionality, arbitrary run/task state
  mutation, direct Airflow database manipulation, and guaranteed whole-run
  retry/cancel are outside the current operations contract.
- Triggering a paused Airflow DAG creates a queued run, but Airflow will not
  execute its tasks until the DAG is unpaused.
- Complete auditing of runs that fail before metadata collection remains
  deferred from the PostgreSQL-backed pipeline-history endpoint; live Airflow
  run reads are not subject to that persistence limitation.
