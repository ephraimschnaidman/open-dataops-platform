# Open DataOps Platform

Open DataOps Platform is an open-source, production-style data engineering platform built with free and open-source tools.

The project separates reusable platform capabilities from example business domains. The first domain is e-commerce, with room to add fintech, SaaS, logistics, and other domains later.

## Current Phase

This milestone establishes a minimal local PostgreSQL warehouse foundation:

- Docker Compose for a local Postgres warehouse
- A persistent Docker volume for database state
- Warehouse schemas created automatically on first database startup
- A simple service boundary so future containers can connect over Docker networking

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

Postgres will be available on `localhost:5432` with:

- database: `dataops`
- user: `dataops`
- password: `POSTGRES_PASSWORD` from `.env`

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
