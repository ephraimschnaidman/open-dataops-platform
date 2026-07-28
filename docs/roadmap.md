# Roadmap

The core pipeline validation phase (Tasks #1 through #5) is complete and has
passed. Task #6 is also complete and has passed final acceptance. Items under
Future Enhancements are planned work and are not represented as current platform
capabilities.

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

Additional production capabilities such as deployment automation and CI/CD remain
future plans unless they are explicitly documented as completed in a later
release.
