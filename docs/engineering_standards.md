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

## Docker Standards

- Keep services isolated.
- Configure services through environment variables.
- Store persistent data in Docker volumes.
- Avoid hard-coded credentials.

## Documentation Standards

- Every architectural decision receives an ADR.
- Keep the README current.
- Document assumptions and tradeoffs.
- Update the ADR index whenever a new ADR is added.

## Guiding Philosophy

Prefer clarity over cleverness. Make every layer have one responsibility. Optimize for maintainability and learning. Build as if this project could eventually become an open-source platform or commercial product.
