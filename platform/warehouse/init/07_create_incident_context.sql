CREATE TABLE IF NOT EXISTS metadata.incident_context (
    context_id UUID PRIMARY KEY,
    incident_id UUID NOT NULL REFERENCES metadata.data_incidents (incident_id) ON DELETE CASCADE,
    context_version TEXT NOT NULL,
    what_happened TEXT NOT NULL,
    why_it_matters TEXT NOT NULL,
    recommended_next_step TEXT NOT NULL,
    generated_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT incident_context_incident_version_unique UNIQUE (incident_id, context_version)
);
