# Open DataOps Platform

Open DataOps Platform is an open-source, production-style data engineering platform built with free and open-source tools.

The project separates reusable platform capabilities from example business domains. The first domain is e-commerce, with room to add fintech, SaaS, logistics, and other domains later.

## Current Phase

This milestone establishes a minimal local PostgreSQL warehouse foundation and a simple raw bootstrap loader for the e-commerce sample data:

- Docker Compose for a local Postgres warehouse
- A persistent Docker volume for database state
- Warehouse schemas created automatically on first database startup
- A simple service boundary so future containers can connect over Docker networking
- Python bootstrap loader for CSV files in `domains/ecommerce/sample_data/`

## Repository Layout

```text
platform/
  warehouse/        Shared warehouse initialization and database assets
```

## Getting Started

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` and set `POSTGRES_PASSWORD` to the local warehouse password you want to use.

Start the local warehouse:

```bash
docker compose up -d
```

Postgres will be available from the host machine on `localhost:5433` with:

- database: `dataops`
- user: `dataops`
- password: `POSTGRES_PASSWORD` from `.env`

Inside Docker networking, future services can use the `postgres` hostname and port `5432`.

On first startup, Postgres runs SQL files from `platform/warehouse/init` in filename order. The current initialization script creates these schemas:

- `raw`
- `staging`
- `marts`
- `metadata`

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

Run the bootstrap loader:

```bash
python scripts/bootstrap_raw_ecommerce_data.py
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

For backward compatibility, the previous command still works:

```bash
python scripts/load_raw_ecommerce_data.py
```

Future milestones will introduce orchestrated and incremental ingestion. This bootstrap loader is intentionally simple and is not a production ingestion pipeline.

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

The Compose file intentionally contains only the `postgres` service. Future platform services can connect to it through Docker Compose networking by using the service name `postgres` as the hostname.
