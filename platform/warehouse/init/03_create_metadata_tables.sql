CREATE TABLE IF NOT EXISTS metadata.pipeline_runs (
    pipeline_run_id UUID PRIMARY KEY,
    dag_id TEXT NOT NULL,
    airflow_run_id TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    run_status TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pipeline_runs_airflow_run_unique UNIQUE (dag_id, airflow_run_id)
);

CREATE TABLE IF NOT EXISTS metadata.dbt_node_results (
    result_id UUID PRIMARY KEY,
    pipeline_run_id UUID NOT NULL REFERENCES metadata.pipeline_runs (pipeline_run_id) ON DELETE CASCADE,
    invocation_id TEXT NOT NULL,
    command_type TEXT NOT NULL CHECK (command_type IN ('run', 'test')),
    node_unique_id TEXT NOT NULL,
    node_name TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    execution_status TEXT NOT NULL,
    execution_time_seconds DOUBLE PRECISION NOT NULL,
    message TEXT,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT dbt_node_results_retry_unique
        UNIQUE (pipeline_run_id, invocation_id, command_type, node_unique_id)
);
