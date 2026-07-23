-- ADR-076 + ADR-080: Project setup with append-only revisions, retention
-- policies, and project_config(id) UUID as the canonical FK target.
--
-- project_name stays denormalised on each table for human-readable logs and
-- SQL queries, but it is NOT the foreign key — that's project_id UUID.

CREATE TABLE IF NOT EXISTS project_setups (
    project_id            UUID PRIMARY KEY REFERENCES project_config(id) ON DELETE CASCADE,
    project_name          TEXT NOT NULL,
    current_revision_id   UUID,
    on_prem               BOOLEAN DEFAULT FALSE,
    hosting_provider      TEXT,
    hosting_region        TEXT,
    homeoffice            BOOLEAN,
    dpo_name              TEXT,
    dpo_email             TEXT,
    training_frequency    TEXT,
    contract_duration     TEXT,
    updated_at            TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_project_setups_name ON project_setups(project_name);

CREATE TABLE IF NOT EXISTS project_setup_revisions (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id            UUID NOT NULL REFERENCES project_setups(project_id) ON DELETE CASCADE,
    project_name          TEXT NOT NULL,
    data                  JSONB NOT NULL,
    created_at            TIMESTAMPTZ DEFAULT now(),
    created_by            TEXT
);

CREATE INDEX IF NOT EXISTS idx_setup_revisions_project
    ON project_setup_revisions(project_id, created_at DESC);

CREATE TABLE IF NOT EXISTS retention_policies (
    project_id            UUID NOT NULL REFERENCES project_config(id) ON DELETE CASCADE,
    project_name          TEXT NOT NULL,
    category              TEXT NOT NULL,
    duration_days         INTEGER,
    duration_raw          TEXT,
    source                TEXT NOT NULL CHECK (source IN ('code', 'setup', 'firecrawl')),
    extracted_from        TEXT,
    updated_at            TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (project_id, category)
);

CREATE INDEX IF NOT EXISTS idx_retention_policies_name
    ON retention_policies(project_name);

COMMENT ON TABLE project_setups
    IS 'ADR-076 + ADR-080: current pointer to append-only revisions. FK is project_id; project_name denormalised for readability.';
COMMENT ON TABLE project_setup_revisions
    IS 'ADR-076 + ADR-080: append-only evidence chain. data = full setup snapshot.';
COMMENT ON TABLE retention_policies
    IS 'ADR-076 + ADR-077 + ADR-080: source=code|setup|firecrawl — reconciliation input.';
