BEGIN;

ALTER TABLE metadata.incident_context
    ADD COLUMN IF NOT EXISTS change_type TEXT,
    ADD COLUMN IF NOT EXISTS affected_column TEXT;

ALTER TABLE metadata.incident_context
    DROP CONSTRAINT IF EXISTS incident_context_action_code_check;

ALTER TABLE metadata.incident_context
    ADD CONSTRAINT incident_context_action_code_check CHECK (
        recommended_action_code IN (
            'INVESTIGATE_UPSTREAM_INGESTION_AND_VERIFY_THRESHOLD',
            'REVIEW_SCHEMA_CHANGE_AND_VALIDATE_CONSUMERS'
        )
    );

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
         WHERE conname = 'incident_context_change_type_check'
    ) THEN
        ALTER TABLE metadata.incident_context
            ADD CONSTRAINT incident_context_change_type_check CHECK (
                change_type IS NULL OR change_type IN (
                    'COLUMN_ADDED', 'COLUMN_REMOVED', 'COLUMN_TYPE_CHANGED'
                )
            );
    END IF;
END $$;

COMMIT;
