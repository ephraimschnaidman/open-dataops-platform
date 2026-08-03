# Roadmap

The core pipeline validation phase (Tasks #1 through #5) is complete and has
passed. Tasks #6, #7, and #8 are also complete and have passed final acceptance.
Items under Future Enhancements are planned work and are not represented as
current platform capabilities.

## Completed: Task #6 – Platform API

**Status: COMPLETE / PASS**

### Objective

Create a REST API that exposes selected platform metadata, data-health metrics,
and incident information without changing the behavior of the existing Airflow
and dbt pipeline.

### Progress

- Phase 1 – repository and data-model assessment: complete
- Phase 2 – API skeleton and Docker integration: complete
- Phase 3 – read-only endpoint implementation: complete
- Final documentation and acceptance-criteria validation: complete

The implemented standalone FastAPI service exposes health, incidents, health
metrics, schema snapshots, dbt node results, and recorded pipeline runs from
persisted PostgreSQL metadata. Final acceptance passed 14 of 14 criteria, 76
focused API tests, the 128-test full repository suite, and a fresh Airflow/dbt
regression run. No blocking defects were identified.

The initial scope remains read-only. Authentication, authorization, user
accounts, monetization, a frontend, cloud deployment, pipeline execution,
incident acknowledgement or mutation, and major database redesign are outside
Task #6.

## Future Enhancements

The following items are deferred enhancements. They are not defects and do not
block the current validated release:

- Complete execution auditing, including failed runs that terminate early
- Task-level lineage
- Task-level metadata
- Automated dbt artifact management
- Operational alerting
- Metadata retention policies
- Recovery runbook
- Refresh tokens and per-token revocation
- OAuth providers and SSO
- Multi-factor authentication (MFA)
- Password reset and public registration
- User-administration workflows
- More granular permissions beyond the current read/write role split
- Multi-tenancy

Additional production capabilities such as deployment automation and CI/CD remain
future plans unless they are explicitly documented as completed in a later
release.

## Completed: Task #7 – Authentication and Authorization

**Status: COMPLETE / PASS**

Task #7 adds PostgreSQL-backed users and roles, Argon2 password hashing,
short-lived JWT access tokens, OAuth2 password-form login, configurable
documentation exposure, secure interactive provisioning, and reusable
router-level RBAC. `Admin`, `Operator`, and `ReadOnly` currently share read
access to the operational API.

Final acceptance passed all 14 criteria, 54 focused
security/authentication/RBAC tests, the 182-test repository suite, and a fresh
Airflow/dbt regression. Environment-based secret configuration, live login,
JWT issuance, authenticated access, anonymous rejection, and service health
were verified. No production-blocking defects were identified.

Future authentication capabilities are listed under Future Enhancements and
remain outside Task #7.

## Completed: Task #8 – Platform Operations API

**Status: COMPLETE / PASS**

Task #8 adds a platform-neutral orchestrator boundary, an Airflow 2.10.5 stable
REST client, six live read endpoints, and safe triggering of existing DAGs.
`Admin`, `Operator`, and `ReadOnly` can read operations data; only `Admin` and
`Operator` can trigger. Caller run IDs are preserved, omitted IDs are generated
by the platform, and duplicate triggers return HTTP 409.

Retry and cancel routes are capability-driven and intentionally return HTTP
501. Airflow 2.10.5 exposes task/DAG-run clearing and state mutation, but not a
stable operation with guaranteed safe whole-run retry or cancellation of
already-running work. DAG creation/editing, scheduler UI functionality, direct
Airflow database mutation, notifications, and broader workflow management
remain outside Task #8.

Final acceptance passed all 28 documented criteria, 36 focused Task #8 tests,
and the 219-test repository suite (215 passed, 4 intentionally skipped). A fresh live
Airflow/dbt/metadata regression completed successfully, all services remained
healthy, and no blocking defects were identified.
