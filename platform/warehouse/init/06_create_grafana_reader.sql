DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'grafana_reader') THEN
        CREATE ROLE grafana_reader LOGIN;
    END IF;
END
$$;

REVOKE CREATE ON SCHEMA metadata FROM grafana_reader;
GRANT CONNECT ON DATABASE dataops TO grafana_reader;
GRANT USAGE ON SCHEMA metadata TO grafana_reader;
GRANT SELECT ON TABLE
    metadata.pipeline_runs,
    metadata.dbt_node_results,
    metadata.table_health_metrics,
    metadata.table_schema_snapshots,
    metadata.data_incidents
TO grafana_reader;

ALTER ROLE grafana_reader SET default_transaction_read_only = on;

ALTER DEFAULT PRIVILEGES IN SCHEMA metadata
    GRANT SELECT ON TABLES TO grafana_reader;
