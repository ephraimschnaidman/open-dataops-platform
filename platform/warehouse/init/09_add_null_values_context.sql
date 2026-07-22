BEGIN;

ALTER TABLE metadata.incident_context
    DROP CONSTRAINT IF EXISTS incident_context_action_code_check;

ALTER TABLE metadata.incident_context
    ADD CONSTRAINT incident_context_action_code_check CHECK (
        recommended_action_code IN (
            'INVESTIGATE_UPSTREAM_INGESTION_AND_VERIFY_THRESHOLD',
            'REVIEW_SCHEMA_CHANGE_AND_VALIDATE_CONSUMERS',
            'REVIEW_NULL_VALUES_AND_VALIDATE_SOURCE_DATA'
        )
    );

COMMIT;
