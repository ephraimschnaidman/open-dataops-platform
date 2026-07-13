CREATE TABLE IF NOT EXISTS metadata.table_health_metrics (
    metric_id UUID PRIMARY KEY,
    pipeline_run_id UUID NOT NULL REFERENCES metadata.pipeline_runs (pipeline_run_id) ON DELETE CASCADE,
    table_schema TEXT NOT NULL,
    table_name TEXT NOT NULL,
    row_count BIGINT NOT NULL CHECK (row_count >= 0),
    freshness_column TEXT,
    max_freshness_value TIMESTAMPTZ,
    measured_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT table_health_metrics_run_table_unique
        UNIQUE (pipeline_run_id, table_schema, table_name)
);

CREATE TABLE IF NOT EXISTS metadata.table_schema_snapshots (
    snapshot_id UUID PRIMARY KEY,
    pipeline_run_id UUID NOT NULL REFERENCES metadata.pipeline_runs (pipeline_run_id) ON DELETE CASCADE,
    table_schema TEXT NOT NULL,
    table_name TEXT NOT NULL,
    column_name TEXT NOT NULL,
    ordinal_position INTEGER NOT NULL CHECK (ordinal_position > 0),
    data_type TEXT NOT NULL,
    is_nullable BOOLEAN NOT NULL,
    measured_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT table_schema_snapshots_run_table_column_unique
        UNIQUE (pipeline_run_id, table_schema, table_name, column_name)
);
