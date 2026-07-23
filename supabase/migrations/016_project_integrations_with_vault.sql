-- ADR-082 + ADR-083: Integration Catalog backed by Supabase Vault.
--
-- Moves third-party credentials out of plaintext TEXT columns on
-- project_config into per-project rows on project_integrations, with
-- the actual secret material held in vault.secrets (AES-256-GCM at
-- rest, decrypt gated on service_role).
--
-- Convention (ADR-083): application tables hold *_secret_id UUID
-- referencing vault.secrets(id). They never hold plaintext.
--
-- Idempotent: every step uses IF [NOT] EXISTS or ON CONFLICT.

-- ─── Vault extension ─────────────────────────────────────────────────────────

CREATE EXTENSION IF NOT EXISTS supabase_vault;

-- Decrypt access is backend-only. A compromised dashboard session
-- (anon or authenticated JWT) structurally cannot read secret material.
REVOKE ALL ON vault.decrypted_secrets FROM anon, authenticated;
GRANT  SELECT ON vault.decrypted_secrets TO service_role;

-- ─── project_integrations ───────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS project_integrations (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id         UUID NOT NULL REFERENCES project_config(id) ON DELETE CASCADE,
    project_name       TEXT NOT NULL,
    integration        TEXT NOT NULL,
    enabled            BOOLEAN NOT NULL DEFAULT TRUE,
    api_key_secret_id  UUID,
    config             JSONB NOT NULL DEFAULT '{}'::jsonb,
    connected_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_sync_at       TIMESTAMPTZ,
    last_error         TEXT,
    UNIQUE (project_id, integration)
);

CREATE INDEX IF NOT EXISTS idx_project_integrations_project
    ON project_integrations(project_id);

COMMENT ON TABLE  project_integrations          IS 'ADR-082: per-project wiring to catalog Service nodes (category=integration).';
COMMENT ON COLUMN project_integrations.api_key_secret_id
                                                IS 'ADR-083: references vault.secrets(id). NULL when the integration has no credential.';
COMMENT ON COLUMN project_integrations.project_name
                                                IS 'ADR-080: denormalised for log/psql readability. Authoritative FK is project_id.';

-- ─── Backfill existing erecht24 keys into the Vault ─────────────────────────

-- Only runs if the legacy columns still exist (fresh installs skip this).
DO $$
DECLARE
    has_legacy BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM information_schema.columns
         WHERE table_schema = 'public'
           AND table_name   = 'project_config'
           AND column_name  = 'erecht24_api_key'
    ) INTO has_legacy;

    IF has_legacy THEN
        INSERT INTO project_integrations
              (project_id, project_name, integration, api_key_secret_id, config)
        SELECT pc.id,
               pc.project_name,
               'erecht24',
               vault.create_secret(pc.erecht24_api_key, 'erecht24-' || pc.id::text),
               jsonb_build_object(
                   'domain',
                   COALESCE(
                       (SELECT pc2.erecht24_domain
                          FROM project_config pc2
                         WHERE pc2.id = pc.id),
                       ''
                   )
               )
          FROM project_config pc
         WHERE pc.erecht24_api_key IS NOT NULL
           AND TRIM(pc.erecht24_api_key) <> ''
        ON CONFLICT (project_id, integration) DO NOTHING;
    END IF;
END $$;

-- ─── Drop legacy plaintext columns ──────────────────────────────────────────

-- Post-backfill: the columns no longer belong on project_config. Their
-- replacement lives in project_integrations + vault.secrets.
ALTER TABLE project_config DROP COLUMN IF EXISTS erecht24_api_key;
ALTER TABLE project_config DROP COLUMN IF EXISTS erecht24_domain;
