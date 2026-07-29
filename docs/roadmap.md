# Roadmap

The core pipeline validation phase (Tasks #1 through #5) is complete and has
passed. Tasks #6 and #7 are also complete and have passed final acceptance.
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
- A differentiated permissions model
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
