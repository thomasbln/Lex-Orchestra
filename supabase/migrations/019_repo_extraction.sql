-- ADR-087: Repo-Content Extraction Layer
-- audit_log table for extraction provenance + extraction_meta on project_config

CREATE TABLE IF NOT EXISTS audit_log (
    id          SERIAL PRIMARY KEY,
    project_name TEXT NOT NULL,
    event_type  TEXT NOT NULL,
    source_file TEXT,
    details     JSONB,
    created_at  TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_log_project ON audit_log(project_name);
CREATE INDEX IF NOT EXISTS idx_audit_log_event   ON audit_log(event_type);

ALTER TABLE project_config
    ADD COLUMN IF NOT EXISTS extraction_meta JSONB DEFAULT '{}';
