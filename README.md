# Open DataOps Platform

Open DataOps Platform is an open-source, production-style data engineering platform built with free and open-source tools.

The project separates reusable platform capabilities from example business domains. The first domain is e-commerce, with room to add fintech, SaaS, logistics, and other domains later.

## Current Phase

This milestone establishes data incident detection around the PostgreSQL, dbt, and Airflow analytics pipeline:

- Docker Compose for a local Postgres warehouse
- A persistent Docker volume for database state
- Warehouse schemas created automatically on first database startup
- A simple service boundary so future containers can connect over Docker networking
- Python bootstrap loader for CSV files in `domains/ecommerce/sample_data/`
- dbt staging views that clean and standardize source-like raw e-commerce tables
- dimensional marts and tested aggregate tables for ecommerce analytics
- Apache Airflow with LocalExecutor and a manually triggered pipeline DAG
- centralized Airflow run and dbt node results in the PostgreSQL `metadata` schema
- row-count, business-timestamp freshness, and schema measurements for important tables
- retry-safe incident detection for freshness, row-count changes, and schema drift

## Repository Layout

```text
platform/
  airflow/          Airflow image, dependencies, and orchestration DAGs
  dbt/              dbt Core project for warehouse transformations
  jobs/             Reusable, orchestrator-independent job entrypoints
  warehouse/        Shared warehouse initialization and database assets
```

## Getting Started

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` and set `POSTGRES_PASSWORD` to the local warehouse password you want to use.

Start PostgreSQL and Airflow (the first build can take several minutes):

```bash
docker compose up -d
```

Postgres will be available from the host machine on `localhost:5433` with:

- database: `dataops`
- user: `dataops`
- password: `POSTGRES_PASSWORD` from `.env`

Inside Docker networking, services use the `postgres` hostname and port `5432`.

On first startup, Postgres runs SQL files from `platform/warehouse/init` in filename order. The current initialization script creates these schemas:

- `raw`
- `staging`
- `marts`
- `metadata`

The initialization also creates a dedicated `airflow` metadata database. Airflow metadata is separate from the `dataops` warehouse database.

## Startup

Start or recreate the warehouse container:

```bash
docker compose up -d
```

## Verification

Check that the service is running and healthy:

```bash
docker compose ps
```

Verify the schemas were created:

```bash
docker compose exec postgres psql -U dataops -d dataops -c "\dn"
```

You can also verify the database connection directly:

```bash
docker compose exec postgres psql -U dataops -d dataops -c "SELECT current_database(), current_user;"
```

## Bootstrap E-commerce Raw Data

Install the Python dependencies:

```bash
python -m pip install -r requirements.txt
```

Make sure the warehouse is running:

```bash
docker compose up -d
```

Run the canonical bootstrap job:

```bash
python platform/jobs/bootstrap_raw_data.py
```

This is a development bootstrap loader for deterministic local setup. It reads CSV files from `domains/ecommerce/sample_data/`, creates the raw e-commerce tables if needed, truncates the raw tables, and reloads them as a full refresh.

The truncation is intentional. It keeps repeated local runs predictable by replacing the raw sample data instead of appending duplicate rows.

- `customers.csv` to `raw.customers`
- `products.csv` to `raw.products`
- `orders.csv` to `raw.orders`
- `order_items.csv` to `raw.order_items`
- `payments.csv` to `raw.payments`
- `web_events.csv` to `raw.web_events`

The script reads connection settings from `.env`. If optional values are not present, it defaults to:

- `POSTGRES_HOST=localhost`
- `POSTGRES_PORT=5433`
- `POSTGRES_DB=dataops`
- `POSTGRES_USER=dataops`

For backward compatibility, both previous commands still work:

```bash
python scripts/load_raw_ecommerce_data.py
python scripts/bootstrap_raw_ecommerce_data.py
```

Future milestones will introduce orchestrated and incremental ingestion. This bootstrap loader is intentionally simple and is not a production ingestion pipeline.

## Transform E-commerce Data With dbt

The dbt Core project lives in `platform/dbt`. It connects to the local Docker Postgres warehouse and builds staging views, dimensional marts, and business aggregates.

The raw e-commerce CSVs intentionally preserve realistic source-system imperfections, including mixed-case emails, whitespace in text fields, inconsistent categorical labels, and missing processor transaction IDs for failed payments. The bootstrap loader loads those files as-is into `raw`; dbt staging views perform the first cleaning and standardization pass.

Install the Python dependencies if you have not already:

```bash
python -m pip install -r requirements.txt
```

Use a stable Python environment for dbt, such as Python 3.11 or 3.12.

Make sure the warehouse is running and raw data has been bootstrapped:

```bash
docker compose up -d
python scripts/bootstrap_raw_ecommerce_data.py
```

Build all dbt models through the reusable job:

```bash
python platform/jobs/run_dbt.py
```

Run the dbt tests through the reusable job:

```bash
python platform/jobs/test_dbt.py
```

The staging models are materialized as views in the `staging` schema:

- `staging.stg_customers`
- `staging.stg_products`
- `staging.stg_orders`
- `staging.stg_order_items`
- `staging.stg_payments`
- `staging.stg_web_events`

The analytics lineage is:

```text
raw tables -> staging views -> dimension and fact tables -> aggregate tables
```

dbt routes models by layer while using one target connection:

- Staging models are materialized as views in the `staging` schema.
- Marts and aggregates are materialized as tables in the `marts` schema.

The custom schema naming macro uses these configured schema names verbatim, so
dbt does not create concatenated names such as `staging_marts`.

- Dimensions: `dim_customers`, `dim_products`, `dim_date`
- Facts: `fct_orders`, `fct_order_items`, `fct_payments`, `fct_web_events`
- Aggregates: `daily_sales`, `customer_lifetime_value`, `product_sales`

All models currently rebuild as tables. A production implementation would likely make the event and transaction facts incremental first, with merge handling for late or changed records. Incremental materializations are intentionally deferred while the demo dataset remains small and deterministic.

The dbt profile uses these environment variables when present:

- `POSTGRES_HOST`, default `localhost`
- `POSTGRES_PORT`, default `5433`
- `POSTGRES_DB`, default `dataops`
- `POSTGRES_USER`, default `dataops`
- `POSTGRES_PASSWORD`, default `open_dataops`

Inside the Airflow containers, dbt writes logs and runtime artifacts to the writable,
host-backed runtime mount. Run and test artifacts are kept separately at
`/opt/airflow/runtime/dbt/run` and `/opt/airflow/runtime/dbt/test`; the project
source remains read-only.

This milestone does not add scheduling, sensors, Metabase, external data quality tools, incremental models, or cloud services.

## Runtime Directory

The repository's `runtime/` directory is the boundary for files generated while
the platform runs. Docker bind mounts it at `/opt/airflow/runtime` in the Airflow
containers. Keeping generated files outside the read-only project mount prevents
dbt, Airflow, and reusable jobs from modifying source-controlled code.

Runtime files are organized as follows:

- `runtime/dbt/run/` contains dbt run artifacts, including `run_results.json`.
- `runtime/dbt/test/` contains dbt test artifacts, including `run_results.json`.
- `runtime/dbt/target/` is reserved for shared dbt target artifacts.
- `runtime/logs/airflow/` contains Airflow task and scheduler-visible logs.
- `runtime/logs/jobs/` contains logs emitted directly by platform jobs and dbt.
- `runtime/metadata/` is reserved for generated local metadata files.

Only the `.gitkeep` placeholders that preserve this structure should be committed.
Generated logs, dbt artifacts, compiled SQL, temporary files, and generated metadata
under `runtime/` are ignored by Git and can be removed during local cleanup.

## Apache Airflow

Copy `.env.example` to `.env`, replace the example secrets (including
`AIRFLOW_ADMIN_USERNAME` and `AIRFLOW_ADMIN_PASSWORD`), then start the stack:

```bash
docker compose up -d --build
docker compose ps
```

Open the Airflow UI at [http://localhost:8080](http://localhost:8080). Unless changed in `.env`, the local-development credentials are `admin` / `admin`. These defaults are not appropriate for a shared or production environment.

The `airflow-init` service migrates the metadata database and creates the configured admin user. It is safe to rerun when that user already exists.

The `ecommerce_pipeline` DAG is paused and has no schedule. In the UI, find the DAG, unpause it, and select **Trigger DAG**. It runs these reusable jobs in order:

```text
bootstrap_raw_data -> run_dbt -> test_dbt -> collect_dbt_metadata -> collect_data_health_metrics -> detect_data_incidents
```

The DAG only coordinates process execution, retries, timeouts, and task dependencies; implementation remains in `platform/jobs`.

The metadata task parses both dbt `run_results.json` files and transactionally upserts
one row in `metadata.pipeline_runs` plus model and test rows in
`metadata.dbt_node_results`. Re-running it for the same Airflow run is idempotent.

### Metadata collection execution modes

Airflow orchestration supplies the pipeline identity and timing arguments to the
collector. The DAG invokes the equivalent of:

```bash
python platform/jobs/collect_dbt_metadata.py \
  --dag-id ecommerce_pipeline \
  --airflow-run-id "<airflow-run-id>" \
  --started-at "<ISO-8601-timestamp>" \
  --run-status success
```

For standalone local testing, first run the dbt run and test jobs to create both
artifacts, then run the collector with generated development metadata:

```bash
python platform/jobs/run_dbt.py
python platform/jobs/test_dbt.py
python platform/jobs/collect_dbt_metadata.py --manual
```

Calling the collector with no arguments is equivalent to `--manual`. Development
mode uses `dag_id=manual`, generated pipeline and Airflow run IDs, the current UTC
start time, and `run_status=SUCCESS`. Database connection settings still come from
`.env`.

The final health task resolves the centralized pipeline run and measures 12 selected
tables across `raw`, `staging`, and `marts`. It stores one row-count and freshness
measurement per table in `metadata.table_health_metrics` and column-level shape in
`metadata.table_schema_snapshots`. Freshness uses centrally configured business
timestamps such as order, payment, and event time. Collection is transactional and
safe to retry for the same pipeline run.

Apply both metadata initialization scripts manually when using an existing
PostgreSQL volume:

```bash
docker compose exec -T postgres psql -U dataops -d dataops -f /docker-entrypoint-initdb.d/03_create_metadata_tables.sql
docker compose exec -T postgres psql -U dataops -d dataops -f /docker-entrypoint-initdb.d/04_create_data_health_tables.sql
```

Apply `05_create_data_incidents.sql` in the same way for an existing volume. Fresh
database volumes apply all metadata initialization scripts automatically. The sixth
task compares stored health data with the previous successful pipeline run and
persists `OPEN` incidents in `metadata.data_incidents`. Thresholds and severities
are centralized in `platform/jobs/data_health_config.py`. It does not add alerts,
dashboards, automated resolution, machine-learning detection, or AI analysis.
Query collected metadata with:

```bash
docker compose exec postgres psql -U dataops -d dataops -c "SELECT * FROM metadata.pipeline_runs;"
```

### Airflow troubleshooting

- Check service health with `docker compose ps` and task/service output with `docker compose logs airflow-init airflow-webserver airflow-scheduler`.
- If this repository already has a Postgres volume created before Airflow was added, create the metadata database once with `docker compose exec postgres psql -U dataops -d dataops -c "CREATE DATABASE airflow;"`, then run `docker compose up -d` again. Alternatively, `docker compose down -v` performs a destructive full local reset.
- If port 8080 is occupied, stop the conflicting service or change the host-side webserver port in `docker-compose.yml`.
- If the DAG is absent, confirm the scheduler is healthy and inspect `docker compose logs airflow-scheduler` for DAG import errors.
- If a task cannot connect to PostgreSQL, confirm `POSTGRES_PASSWORD` is identical for PostgreSQL and Airflow and that the `postgres` service is healthy.

## Shutdown

Stop the warehouse without deleting data:

```bash
docker compose down
```

## Reset

Delete the container and the persistent warehouse volume, then initialize a fresh database:

```bash
docker compose down -v
docker compose up -d
```

## Architecture Notes

Airflow and the jobs share no business implementation. This keeps the job entrypoints usable from the command line, CI, and future orchestration systems.
