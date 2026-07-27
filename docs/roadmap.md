# Roadmap

The core pipeline validation phase (Tasks #1 through #5) is complete and has
passed. Roadmap items below are planned work and are not represented as current
platform capabilities.

## Next: Task #6 – Platform API

**Status: NEXT / NOT STARTED**

### Objective

Create a REST API that exposes selected platform metadata, data-health metrics,
and incident information without changing the behavior of the existing Airflow
and dbt pipeline.

The API design, authentication model, and deployment approach have not yet been
implemented.

## Future Enhancements

The following items are deferred enhancements. They are not defects and do not
block the current validated release:

- Complete execution auditing, including early failed runs
- Task-level lineage
- Task-level metadata
- Automated dbt artifact management
- Operational alerting
- Metadata retention policies
- Recovery runbook

Additional production capabilities such as deployment automation and CI/CD remain
future plans unless they are explicitly documented as completed in a later
release.
