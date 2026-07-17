# Engineering Standards

## Purpose

These standards exist to improve consistency, readability, maintainability, and production-style engineering across the Open DataOps Platform. They are intended to help the project grow deliberately without becoming hard to understand, test, or extend.

## Architecture Principles

- Separate concerns across platform infrastructure, domain examples, ingestion, transformation, and analytics layers.
- Keep platform code domain-agnostic.
- Treat business domains, currently e-commerce, as demonstrations built on top of the platform.
- Favor modularity over monolithic implementations.
- Build incrementally without overengineering.
- Give every layer one clearly defined responsibility.

## Data Layer Responsibilities

### Raw

- Preserve source data exactly as received.
- Do not apply business logic.
- Keep transformations minimal.
- Keep the source schema recognizable.

### Staging

- Clean and standardize source data.
- Rename ambiguous columns.
- Cast data types.
- Normalize categorical values.
- Trim whitespace.
- Standardize timestamps.
- Use explicit `SELECT` statements only.
- Do not calculate business metrics.

### Marts

- Place business logic here.
- Build fact and dimension tables.
- Produce analytics-ready datasets.
- Use dimensional modeling patterns where appropriate.

## SQL Standards

- Never use `SELECT *`.
- Use `snake_case`.
- Prefer descriptive column names.
- Alias tables clearly.
- Organize SQL for readability.
- Comment only when intent is not obvious.

## dbt Standards

- Sources represent raw data.
- Staging models begin with `stg_`.
- Fact tables begin with `fct_`.
- Dimension tables begin with `dim_`.
- `schema.yml` files contain documentation and tests.
- Test keys, relationships, and accepted values.

## Python Standards

- Follow PEP 8.
- Prefer small, focused modules.
- Use type hints where practical.
- Keep scripts single-purpose.
- Add logging for operational visibility.
- Raise meaningful exceptions.

## Operational Metadata Standards

- Store platform execution metadata in the `metadata` schema.
- Link tool-level results to one orchestrator pipeline run.
- Use stable uniqueness constraints and transactional upserts so collection is safe to retry.
- Preserve source-tool identifiers and statuses rather than recreating execution logic.
- Link health measurements and schema snapshots to the pipeline run that produced the measured data.
- Keep freshness-column semantics in centralized configuration rather than scattering them through collection code.
- Keep incident thresholds and severity mappings in centralized configuration.
- Detect incidents from persisted measurements; do not couple policy evaluation to measurement collection.
- Store generated incident context separately from incident detection facts.
- Centralize deterministic context rules and assign an explicit version to every output policy.
- Persist structured numeric context and controlled status/action codes; render prose only at presentation time.
- Present investigative next steps as recommendations, never as proven root causes.

## Repository Standards

- Use UTF-8 encoding.
- Use LF line endings.
- `.editorconfig` governs formatting.
- `.gitattributes` governs line endings.
- Never commit:
  - `.venv`
  - `.env`
  - generated artifacts
  - logs
  - local databases

## Runtime Artifacts

- Treat source code as immutable during execution.
- Write runtime files under the repository's `runtime/` boundary.
- Never write logs, generated artifacts, temporary files, or generated metadata into source-controlled directories.
- Commit only placeholder files needed to preserve the runtime directory structure; ignore generated contents.
- Use standard rotating logging handlers with explicit retention; never trim active log files manually.

## Docker Standards

- Keep services isolated.
- Configure services through environment variables.
- Store persistent data in Docker volumes.
- Avoid hard-coded credentials.

## Observability Standards

- Query centralized operational metadata instead of coupling dashboards to domain tables.
- Provision data sources and dashboards from version-controlled configuration.
- Give visualization tools read-only access using dedicated database identities.
- Keep credentials in environment configuration and out of committed provisioning files.

## Documentation Standards

- Every architectural decision receives an ADR.
- Keep the README current.
- Document assumptions and tradeoffs.
- Update the ADR index whenever a new ADR is added.

## Guiding Philosophy

Prefer clarity over cleverness. Make every layer have one responsibility. Optimize for maintainability and learning. Build as if this project could eventually become an open-source platform or commercial product.
