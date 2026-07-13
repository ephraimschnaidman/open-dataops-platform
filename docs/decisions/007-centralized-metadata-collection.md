# ADR-007: Centralized Pipeline Metadata Collection

- Status: Accepted
- Date: 2026-07-13

## Context

Airflow shows task state and dbt produces detailed execution artifacts, but those records live in separate tools and are not convenient for platform-wide operational analysis. The platform needs a durable link between one orchestrated pipeline run and the models and tests executed within it.

## Decision

Store pipeline execution records in `metadata.pipeline_runs` and dbt node outcomes in `metadata.dbt_node_results` in the existing `dataops` PostgreSQL database. Each node result references its Airflow pipeline run. The Airflow DAG passes its DAG ID, run ID, start time, and successful status to a reusable collection job after dbt tests finish.

The collector parses dbt's `run_results.json` from separate `run` and `test` artifact directories. dbt remains responsible for executing and describing models and tests; parsing its standard artifacts avoids reimplementing dbt selection, timing, status, and invocation behavior.

The job supports two execution modes. Under Airflow, the DAG supplies the stable
orchestration identity, start time, and status. For standalone local testing,
`--manual` (or no runtime arguments) generates temporary pipeline and Airflow run
identifiers, uses `manual` as the DAG ID, records the current UTC start time, and
uses `SUCCESS` as the status. This development convenience does not change the
Airflow execution path.

Pipeline and result identifiers are deterministic. Database uniqueness constraints cover an Airflow run and each dbt node within an invocation and command. Parameterized `INSERT ... ON CONFLICT DO UPDATE` statements run in one transaction, so task retries update the same logical records instead of appending duplicates.

## Consequences

- Operational SQL can relate an Airflow run to all dbt model and test outcomes.
- Run and test artifacts cannot overwrite each other.
- A malformed or missing artifact fails collection with a clear error, and the transaction prevents partial persistence.
- Existing database volumes must apply `03_create_metadata_tables.sql` manually because PostgreSQL initialization scripts only run for a new volume.

## Local limitations

This implementation records successful end-to-end runs because collection is the final downstream task; a failure before collection is not written to these tables. Artifacts use the host-backed local `runtime/` directory and are not durable object storage. Node names and resource types are derived from dbt unique IDs, and retention, concurrency governance, access controls, and cross-environment aggregation are deferred.
