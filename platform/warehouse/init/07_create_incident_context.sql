BEGIN;

CREATE TABLE IF NOT EXISTS metadata.incident_context (
    context_id UUID PRIMARY KEY,
    incident_id UUID NOT NULL REFERENCES metadata.data_incidents (incident_id) ON DELETE CASCADE,
    context_version TEXT NOT NULL,
    qualified_table TEXT,
    evaluation_status TEXT,
    severity TEXT,
    expected_freshness_hours NUMERIC,
    observed_freshness_hours NUMERIC,
    recommended_action_code TEXT,
    generated_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT incident_context_incident_version_unique UNIQUE (incident_id, context_version)
);

ALTER TABLE metadata.incident_context
    ADD COLUMN IF NOT EXISTS qualified_table TEXT,
    ADD COLUMN IF NOT EXISTS evaluation_status TEXT,
    ADD COLUMN IF NOT EXISTS severity TEXT,
    ADD COLUMN IF NOT EXISTS expected_freshness_hours NUMERIC,
    ADD COLUMN IF NOT EXISTS observed_freshness_hours NUMERIC,
    ADD COLUMN IF NOT EXISTS recommended_action_code TEXT;

WITH parsed AS (
    SELECT i.incident_id,
           i.table_schema || '.' || i.table_name AS qualified_table,
           i.severity,
           CASE WHEN i.expected_value ~* '^\s*<=\s*[0-9]+(\.[0-9]+)?\s+hours?\s*$'
                THEN substring(i.expected_value FROM '([0-9]+(?:\.[0-9]+)?)')::numeric END AS expected_hours,
           CASE WHEN i.observed_value ~* '^\s*[0-9]+(\.[0-9]+)?\s+hours?\s*$'
                THEN substring(i.observed_value FROM '([0-9]+(?:\.[0-9]+)?)')::numeric END AS observed_hours
      FROM metadata.data_incidents i
     WHERE i.incident_type = 'STALE_DATA'
)
UPDATE metadata.incident_context c
   SET qualified_table = p.qualified_table,
       severity = p.severity,
       expected_freshness_hours = p.expected_hours,
       observed_freshness_hours = p.observed_hours,
       evaluation_status = CASE
           WHEN p.expected_hours IS NULL OR p.observed_hours IS NULL THEN 'UNKNOWN'
           WHEN p.observed_hours > p.expected_hours THEN 'EXCEEDED_THRESHOLD'
           ELSE 'WITHIN_THRESHOLD'
       END,
       recommended_action_code = 'INVESTIGATE_UPSTREAM_INGESTION_AND_VERIFY_THRESHOLD'
  FROM parsed p
 WHERE c.incident_id = p.incident_id
   AND c.context_version = 'stale_data_v1'
   AND (c.qualified_table IS NULL OR c.evaluation_status IS NULL OR c.severity IS NULL
        OR c.recommended_action_code IS NULL);

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM metadata.incident_context
         WHERE qualified_table IS NULL OR evaluation_status IS NULL OR severity IS NULL
            OR recommended_action_code IS NULL
    ) THEN
        RAISE EXCEPTION 'incident_context migration could not backfill all required fields';
    END IF;
END $$;

ALTER TABLE metadata.incident_context
    ALTER COLUMN qualified_table SET NOT NULL,
    ALTER COLUMN evaluation_status SET NOT NULL,
    ALTER COLUMN severity SET NOT NULL,
    ALTER COLUMN recommended_action_code SET NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'incident_context_evaluation_status_check') THEN
        ALTER TABLE metadata.incident_context ADD CONSTRAINT incident_context_evaluation_status_check
            CHECK (evaluation_status IN ('EXCEEDED_THRESHOLD', 'WITHIN_THRESHOLD', 'UNKNOWN'));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'incident_context_action_code_check') THEN
        ALTER TABLE metadata.incident_context ADD CONSTRAINT incident_context_action_code_check
            CHECK (recommended_action_code IN ('INVESTIGATE_UPSTREAM_INGESTION_AND_VERIFY_THRESHOLD'));
    END IF;
END $$;

ALTER TABLE metadata.incident_context
    DROP COLUMN IF EXISTS what_happened,
    DROP COLUMN IF EXISTS why_it_matters,
    DROP COLUMN IF EXISTS recommended_next_step;

COMMIT;
