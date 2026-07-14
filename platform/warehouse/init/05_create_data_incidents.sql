CREATE TABLE IF NOT EXISTS metadata.data_incidents (
    incident_id UUID PRIMARY KEY,
    pipeline_run_id UUID NOT NULL REFERENCES metadata.pipeline_runs (pipeline_run_id) ON DELETE CASCADE,
    incident_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    table_schema TEXT NOT NULL,
    table_name TEXT NOT NULL,
    column_name TEXT,
    expected_value TEXT,
    observed_value TEXT,
    incident_message TEXT NOT NULL,
    incident_status TEXT NOT NULL DEFAULT 'OPEN',
    detected_at TIMESTAMPTZ NOT NULL,
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT data_incidents_status_check CHECK (incident_status IN ('OPEN', 'RESOLVED')),
    CONSTRAINT data_incidents_severity_check CHECK (severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    CONSTRAINT data_incidents_retry_unique
        UNIQUE NULLS NOT DISTINCT
        (pipeline_run_id, incident_type, table_schema, table_name, column_name)
);
