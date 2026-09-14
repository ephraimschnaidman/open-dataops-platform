BEGIN;

SELECT pg_advisory_xact_lock(
    hashtextextended('open-dataops-platform:workspace-settings:v1', 0)
);

ALTER TABLE metadata.environments
    ADD COLUMN IF NOT EXISTS description TEXT;

CREATE TABLE IF NOT EXISTS metadata.workspace_settings (
    workspace_key TEXT PRIMARY KEY,
    workspace_name TEXT NOT NULL,
    default_environment_id UUID NOT NULL
        REFERENCES metadata.environments (environment_id) ON DELETE RESTRICT,
    timezone TEXT NOT NULL,
    notification_enabled BOOLEAN NOT NULL,
    notification_recipients TEXT[] NOT NULL,
    notification_severity TEXT NOT NULL,
    notify_resolved BOOLEAN NOT NULL,
    pipeline_healthy NUMERIC(5,2) NOT NULL,
    pipeline_warning NUMERIC(5,2) NOT NULL,
    schedule_healthy NUMERIC(5,2) NOT NULL,
    schedule_warning NUMERIC(5,2) NOT NULL,
    source_healthy NUMERIC(5,2) NOT NULL,
    source_warning NUMERIC(5,2) NOT NULL,
    runtime_warning NUMERIC(5,2) NOT NULL,
    freshness_hours NUMERIC(7,2) NOT NULL,
    validation_severity TEXT NOT NULL,
    blocking_alerts BOOLEAN NOT NULL,
    warning_alerts BOOLEAN NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT workspace_settings_key_format_check
        CHECK (workspace_key ~ '^workspace_[A-Za-z0-9]+$'),
    CONSTRAINT workspace_settings_name_nonblank_check
        CHECK (length(btrim(workspace_name)) > 0),
    CONSTRAINT workspace_settings_timezone_check
        CHECK (timezone IN ('America/New_York', 'America/Chicago', 'America/Los_Angeles', 'UTC')),
    CONSTRAINT workspace_settings_notification_severity_check
        CHECK (notification_severity IN ('CRITICAL_ONLY', 'CRITICAL_AND_WARNING')),
    CONSTRAINT workspace_settings_notification_recipient_check
        CHECK (NOT notification_enabled OR cardinality(notification_recipients) > 0),
    CONSTRAINT workspace_settings_percentage_range_check CHECK (
        pipeline_healthy BETWEEN 0 AND 100 AND pipeline_warning BETWEEN 0 AND 100
        AND schedule_healthy BETWEEN 0 AND 100 AND schedule_warning BETWEEN 0 AND 100
        AND source_healthy BETWEEN 0 AND 100 AND source_warning BETWEEN 0 AND 100
        AND runtime_warning BETWEEN 0 AND 100
    ),
    CONSTRAINT workspace_settings_threshold_order_check CHECK (
        pipeline_healthy > pipeline_warning
        AND schedule_healthy > schedule_warning
        AND source_healthy > source_warning
    ),
    CONSTRAINT workspace_settings_freshness_range_check
        CHECK (freshness_hours > 0 AND freshness_hours <= 8760),
    CONSTRAINT workspace_settings_validation_severity_check
        CHECK (validation_severity IN ('WARNING', 'BLOCKING')),
    CONSTRAINT workspace_settings_updated_at_check
        CHECK (updated_at >= created_at)
);

INSERT INTO metadata.workspace_settings (
    workspace_key, workspace_name, default_environment_id, timezone,
    notification_enabled, notification_recipients, notification_severity,
    notify_resolved, pipeline_healthy, pipeline_warning, schedule_healthy,
    schedule_warning, source_healthy, source_warning, runtime_warning,
    freshness_hours, validation_severity, blocking_alerts, warning_alerts
)
SELECT
    'workspace_01J4X8K97B', 'Corvetra Demo Workspace', environment_id,
    'America/New_York', TRUE,
    ARRAY['ops@example.com', 'engineering@example.com'],
    'CRITICAL_AND_WARNING', TRUE, 98, 95, 99, 95, 99.5, 98, 30, 2,
    'WARNING', TRUE, FALSE
FROM metadata.environments
WHERE environment_key = 'production'
ON CONFLICT (workspace_key) DO NOTHING;

COMMIT;
