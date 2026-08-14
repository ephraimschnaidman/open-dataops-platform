BEGIN;

SELECT pg_advisory_xact_lock(
    hashtextextended('open-dataops-platform:canonical-schema:v1', 0)
);

CREATE TABLE IF NOT EXISTS metadata.environments (
    environment_id UUID PRIMARY KEY,
    environment_key TEXT NOT NULL UNIQUE,
    environment_name TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT environments_key_format_check
        CHECK (environment_key ~ '^[a-z0-9]+(?:-[a-z0-9]+)*$'),
    CONSTRAINT environments_name_nonblank_check
        CHECK (length(btrim(environment_name)) > 0)
);

CREATE TABLE IF NOT EXISTS metadata.data_sources (
    data_source_id UUID PRIMARY KEY,
    source_key TEXT NOT NULL UNIQUE,
    source_name TEXT NOT NULL,
    source_type TEXT NOT NULL,
    environment_id UUID NOT NULL
        REFERENCES metadata.environments (environment_id) ON DELETE RESTRICT,
    operational_status TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT data_sources_identity_environment_unique
        UNIQUE (data_source_id, environment_id),
    CONSTRAINT data_sources_key_format_check
        CHECK (source_key ~ '^[a-z0-9]+(?:-[a-z0-9]+)*$'),
    CONSTRAINT data_sources_name_nonblank_check
        CHECK (length(btrim(source_name)) > 0),
    CONSTRAINT data_sources_type_check
        CHECK (source_type IN ('KAFKA', 'POSTGRESQL', 'SNOWFLAKE', 'SQL_SERVER')),
    CONSTRAINT data_sources_status_check
        CHECK (operational_status IN ('HEALTHY', 'WARNING', 'DISCONNECTED', 'DISABLED')),
    CONSTRAINT data_sources_updated_at_check
        CHECK (updated_at >= created_at)
);

CREATE TABLE IF NOT EXISTS metadata.pipelines (
    pipeline_id UUID PRIMARY KEY,
    pipeline_key TEXT NOT NULL UNIQUE,
    pipeline_name TEXT NOT NULL,
    environment_id UUID NOT NULL,
    data_source_id UUID NOT NULL,
    airflow_dag_id TEXT NOT NULL,
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pipelines_environment_dag_unique
        UNIQUE (environment_id, airflow_dag_id),
    CONSTRAINT pipelines_source_environment_fkey
        FOREIGN KEY (data_source_id, environment_id)
        REFERENCES metadata.data_sources (data_source_id, environment_id)
        ON DELETE RESTRICT,
    CONSTRAINT pipelines_key_format_check
        CHECK (pipeline_key ~ '^[a-z0-9]+(?:-[a-z0-9]+)*$'),
    CONSTRAINT pipelines_name_nonblank_check
        CHECK (length(btrim(pipeline_name)) > 0),
    CONSTRAINT pipelines_dag_nonblank_check
        CHECK (length(btrim(airflow_dag_id)) > 0),
    CONSTRAINT pipelines_updated_at_check
        CHECK (updated_at >= created_at)
);

ALTER TABLE metadata.pipeline_runs
    ADD COLUMN IF NOT EXISTS corvetra_run_id TEXT,
    ADD COLUMN IF NOT EXISTS pipeline_id UUID,
    ADD COLUMN IF NOT EXISTS stage_name TEXT,
    ADD COLUMN IF NOT EXISTS platform_code TEXT,
    ADD COLUMN IF NOT EXISTS vendor_code TEXT,
    ADD COLUMN IF NOT EXISTS rule_code TEXT;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'pipeline_runs_corvetra_run_unique'
          AND conrelid = 'metadata.pipeline_runs'::regclass
    ) THEN
        ALTER TABLE metadata.pipeline_runs
            ADD CONSTRAINT pipeline_runs_corvetra_run_unique UNIQUE (corvetra_run_id);
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'pipeline_runs_pipeline_id_fkey'
          AND conrelid = 'metadata.pipeline_runs'::regclass
    ) THEN
        ALTER TABLE metadata.pipeline_runs
            ADD CONSTRAINT pipeline_runs_pipeline_id_fkey
            FOREIGN KEY (pipeline_id) REFERENCES metadata.pipelines (pipeline_id)
            ON DELETE RESTRICT;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'pipeline_runs_corvetra_id_format_check'
          AND conrelid = 'metadata.pipeline_runs'::regclass
    ) THEN
        ALTER TABLE metadata.pipeline_runs
            ADD CONSTRAINT pipeline_runs_corvetra_id_format_check
            CHECK (corvetra_run_id IS NULL OR corvetra_run_id ~ '^run_[A-Za-z0-9]+$');
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'pipeline_runs_corvetra_pipeline_check'
          AND conrelid = 'metadata.pipeline_runs'::regclass
    ) THEN
        ALTER TABLE metadata.pipeline_runs
            ADD CONSTRAINT pipeline_runs_corvetra_pipeline_check
            CHECK (corvetra_run_id IS NULL OR pipeline_id IS NOT NULL);
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'pipeline_runs_stage_check'
          AND conrelid = 'metadata.pipeline_runs'::regclass
    ) THEN
        ALTER TABLE metadata.pipeline_runs
            ADD CONSTRAINT pipeline_runs_stage_check
            CHECK (stage_name IS NULL OR stage_name IN ('EXTRACT', 'TRANSFORM', 'VALIDATE', 'LOAD'));
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'pipeline_runs_codes_nonblank_check'
          AND conrelid = 'metadata.pipeline_runs'::regclass
    ) THEN
        ALTER TABLE metadata.pipeline_runs
            ADD CONSTRAINT pipeline_runs_codes_nonblank_check CHECK (
                (platform_code IS NULL OR length(btrim(platform_code)) > 0)
                AND (vendor_code IS NULL OR length(btrim(vendor_code)) > 0)
                AND (rule_code IS NULL OR length(btrim(rule_code)) > 0)
            );
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'pipeline_runs_cause_code_check'
          AND conrelid = 'metadata.pipeline_runs'::regclass
    ) THEN
        ALTER TABLE metadata.pipeline_runs
            ADD CONSTRAINT pipeline_runs_cause_code_check
            CHECK (vendor_code IS NULL OR rule_code IS NULL);
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS metadata.validation_checks (
    validation_check_id UUID PRIMARY KEY,
    check_key TEXT NOT NULL UNIQUE,
    pipeline_id UUID NOT NULL
        REFERENCES metadata.pipelines (pipeline_id) ON DELETE RESTRICT,
    check_name TEXT NOT NULL,
    check_type TEXT NOT NULL,
    dataset_name TEXT NOT NULL,
    column_name TEXT,
    default_severity TEXT NOT NULL,
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT validation_checks_definition_unique
        UNIQUE NULLS NOT DISTINCT (pipeline_id, dataset_name, column_name, check_type),
    CONSTRAINT validation_checks_key_format_check
        CHECK (check_key ~ '^[a-z0-9]+(?:-[a-z0-9]+)*$'),
    CONSTRAINT validation_checks_name_nonblank_check
        CHECK (length(btrim(check_name)) > 0),
    CONSTRAINT validation_checks_dataset_nonblank_check
        CHECK (length(btrim(dataset_name)) > 0),
    CONSTRAINT validation_checks_column_nonblank_check
        CHECK (column_name IS NULL OR length(btrim(column_name)) > 0),
    CONSTRAINT validation_checks_type_check CHECK (check_type IN (
        'NOT_NULL', 'UNIQUE', 'ACCEPTED_VALUES', 'RANGE', 'FRESHNESS',
        'ROW_COUNT', 'REFERENTIAL_INTEGRITY', 'CUSTOM'
    )),
    CONSTRAINT validation_checks_severity_check
        CHECK (default_severity IN ('WARNING', 'BLOCKING')),
    CONSTRAINT validation_checks_updated_at_check
        CHECK (updated_at >= created_at)
);

CREATE TABLE IF NOT EXISTS metadata.validation_executions (
    validation_execution_id UUID PRIMARY KEY,
    pipeline_run_id UUID NOT NULL
        REFERENCES metadata.pipeline_runs (pipeline_run_id) ON DELETE CASCADE,
    validation_check_id UUID NOT NULL
        REFERENCES metadata.validation_checks (validation_check_id) ON DELETE RESTRICT,
    dbt_result_id UUID UNIQUE
        REFERENCES metadata.dbt_node_results (result_id) ON DELETE SET NULL,
    stage_name TEXT NOT NULL,
    result_status TEXT NOT NULL,
    effective_severity TEXT NOT NULL,
    platform_code TEXT NOT NULL,
    rule_code TEXT,
    vendor_code TEXT,
    actual_value TEXT,
    expected_value TEXT,
    result_message TEXT NOT NULL,
    evaluated_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT validation_executions_run_check_unique
        UNIQUE (pipeline_run_id, validation_check_id),
    CONSTRAINT validation_executions_stage_check
        CHECK (stage_name = 'VALIDATE'),
    CONSTRAINT validation_executions_result_check
        CHECK (result_status IN ('PASSED', 'FAILED', 'NOT_EVALUATED')),
    CONSTRAINT validation_executions_severity_check
        CHECK (effective_severity IN ('WARNING', 'BLOCKING')),
    CONSTRAINT validation_executions_message_nonblank_check
        CHECK (length(btrim(result_message)) > 0),
    CONSTRAINT validation_executions_codes_nonblank_check CHECK (
        length(btrim(platform_code)) > 0
        AND (rule_code IS NULL OR length(btrim(rule_code)) > 0)
        AND (vendor_code IS NULL OR length(btrim(vendor_code)) > 0)
    ),
    CONSTRAINT validation_executions_cause_code_check
        CHECK (vendor_code IS NULL OR rule_code IS NULL),
    CONSTRAINT validation_executions_outcome_check CHECK (
        (result_status = 'PASSED'
            AND platform_code = 'VALIDATION_CHECK_PASSED'
            AND rule_code IS NULL AND vendor_code IS NULL)
        OR
        (result_status = 'FAILED'
            AND platform_code = 'VALIDATION_CHECK_FAILED'
            AND rule_code IS NOT NULL AND vendor_code IS NULL)
        OR
        (result_status = 'NOT_EVALUATED'
            AND platform_code = 'VALIDATION_EXECUTION_FAILED'
            AND rule_code IS NULL AND vendor_code IS NOT NULL)
    )
);

CREATE TABLE IF NOT EXISTS metadata.operational_alerts (
    alert_id UUID PRIMARY KEY,
    alert_key TEXT NOT NULL UNIQUE,
    pipeline_run_id UUID NOT NULL
        REFERENCES metadata.pipeline_runs (pipeline_run_id) ON DELETE CASCADE,
    validation_execution_id UUID UNIQUE
        REFERENCES metadata.validation_executions (validation_execution_id) ON DELETE SET NULL,
    alert_title TEXT NOT NULL,
    severity TEXT NOT NULL,
    alert_status TEXT NOT NULL,
    platform_code TEXT NOT NULL,
    vendor_code TEXT,
    rule_code TEXT,
    alert_message TEXT NOT NULL,
    detected_at TIMESTAMPTZ NOT NULL,
    last_seen_at TIMESTAMPTZ NOT NULL,
    acknowledged_at TIMESTAMPTZ,
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT operational_alerts_key_format_check
        CHECK (alert_key ~ '^ALT-[0-9]+$'),
    CONSTRAINT operational_alerts_title_nonblank_check
        CHECK (length(btrim(alert_title)) > 0),
    CONSTRAINT operational_alerts_message_nonblank_check
        CHECK (length(btrim(alert_message)) > 0),
    CONSTRAINT operational_alerts_severity_check
        CHECK (severity IN ('CRITICAL', 'WARNING')),
    CONSTRAINT operational_alerts_status_check
        CHECK (alert_status IN ('OPEN', 'ACKNOWLEDGED', 'RESOLVED')),
    CONSTRAINT operational_alerts_codes_nonblank_check CHECK (
        length(btrim(platform_code)) > 0
        AND (vendor_code IS NULL OR length(btrim(vendor_code)) > 0)
        AND (rule_code IS NULL OR length(btrim(rule_code)) > 0)
    ),
    CONSTRAINT operational_alerts_cause_code_check
        CHECK (vendor_code IS NULL OR rule_code IS NULL),
    CONSTRAINT operational_alerts_seen_at_check
        CHECK (last_seen_at >= detected_at),
    CONSTRAINT operational_alerts_updated_at_check
        CHECK (updated_at >= created_at),
    CONSTRAINT operational_alerts_lifecycle_check CHECK (
        (alert_status = 'OPEN' AND acknowledged_at IS NULL AND resolved_at IS NULL)
        OR
        (alert_status = 'ACKNOWLEDGED' AND acknowledged_at IS NOT NULL AND resolved_at IS NULL)
        OR
        (alert_status = 'RESOLVED' AND resolved_at IS NOT NULL)
    )
);

CREATE TABLE IF NOT EXISTS metadata.technical_events (
    technical_event_id UUID PRIMARY KEY,
    event_key TEXT NOT NULL UNIQUE,
    occurred_at TIMESTAMPTZ NOT NULL,
    event_level TEXT NOT NULL,
    environment_id UUID NOT NULL
        REFERENCES metadata.environments (environment_id) ON DELETE RESTRICT,
    pipeline_id UUID
        REFERENCES metadata.pipelines (pipeline_id) ON DELETE RESTRICT,
    pipeline_run_id UUID
        REFERENCES metadata.pipeline_runs (pipeline_run_id) ON DELETE CASCADE,
    data_source_id UUID
        REFERENCES metadata.data_sources (data_source_id) ON DELETE RESTRICT,
    alert_id UUID
        REFERENCES metadata.operational_alerts (alert_id) ON DELETE SET NULL,
    validation_execution_id UUID
        REFERENCES metadata.validation_executions (validation_execution_id) ON DELETE SET NULL,
    stage_name TEXT,
    platform_code TEXT,
    vendor_code TEXT,
    rule_code TEXT,
    event_message TEXT NOT NULL,
    event_details JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT technical_events_level_check
        CHECK (event_level IN ('ERROR', 'WARNING', 'INFO', 'DEBUG')),
    CONSTRAINT technical_events_stage_check
        CHECK (stage_name IS NULL OR stage_name IN ('EXTRACT', 'TRANSFORM', 'VALIDATE', 'LOAD')),
    CONSTRAINT technical_events_message_nonblank_check
        CHECK (length(btrim(event_message)) > 0),
    CONSTRAINT technical_events_codes_nonblank_check CHECK (
        (platform_code IS NULL OR length(btrim(platform_code)) > 0)
        AND (vendor_code IS NULL OR length(btrim(vendor_code)) > 0)
        AND (rule_code IS NULL OR length(btrim(rule_code)) > 0)
    ),
    CONSTRAINT technical_events_cause_code_check
        CHECK (vendor_code IS NULL OR rule_code IS NULL),
    CONSTRAINT technical_events_details_object_check
        CHECK (event_details IS NULL OR jsonb_typeof(event_details) = 'object')
);

CREATE INDEX IF NOT EXISTS pipeline_runs_pipeline_started_idx
    ON metadata.pipeline_runs (pipeline_id, started_at DESC);
CREATE INDEX IF NOT EXISTS pipelines_data_source_idx
    ON metadata.pipelines (data_source_id);
CREATE INDEX IF NOT EXISTS validation_checks_pipeline_idx
    ON metadata.validation_checks (pipeline_id);
CREATE INDEX IF NOT EXISTS validation_executions_run_evaluated_idx
    ON metadata.validation_executions (pipeline_run_id, evaluated_at DESC);
CREATE INDEX IF NOT EXISTS operational_alerts_run_seen_idx
    ON metadata.operational_alerts (pipeline_run_id, last_seen_at DESC);
CREATE INDEX IF NOT EXISTS operational_alerts_status_seen_idx
    ON metadata.operational_alerts (alert_status, last_seen_at DESC);
CREATE INDEX IF NOT EXISTS technical_events_occurred_idx
    ON metadata.technical_events (occurred_at DESC);
CREATE INDEX IF NOT EXISTS technical_events_run_occurred_idx
    ON metadata.technical_events (pipeline_run_id, occurred_at DESC);
CREATE INDEX IF NOT EXISTS technical_events_pipeline_occurred_idx
    ON metadata.technical_events (pipeline_id, occurred_at DESC);
CREATE INDEX IF NOT EXISTS technical_events_source_occurred_idx
    ON metadata.technical_events (data_source_id, occurred_at DESC);

GRANT SELECT ON TABLE
    metadata.environments,
    metadata.data_sources,
    metadata.pipelines,
    metadata.validation_checks,
    metadata.validation_executions,
    metadata.operational_alerts,
    metadata.technical_events
TO grafana_reader;

COMMIT;
