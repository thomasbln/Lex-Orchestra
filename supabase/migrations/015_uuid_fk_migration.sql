-- ADR-080: Swap TEXT FKs on project_name for UUID FKs on project_config(id).
-- Retro-fit migration for deployments that already hold 011–014 data.
-- Fresh OSS installs never need this — they start from migrate.sql +
-- 014_project_setups.sql which already uses project_id UUID.
--
-- Strategy:
-- 1. Add project_id UUID column.
-- 2. Backfill via join on project_name.
-- 3. NOT NULL + FK on project_config(id).
-- 4. Drop the old TEXT FK (where one existed).
-- 5. Keep project_name column for log / query readability.
--
-- Idempotent: every step uses IF [NOT] EXISTS; safe to re-run.

-- ─── project_tokens ──────────────────────────────────────────────────────────

ALTER TABLE project_tokens
    ADD COLUMN IF NOT EXISTS project_id UUID;

UPDATE project_tokens pt
   SET project_id = pc.id
  FROM project_config pc
 WHERE pt.project_name = pc.project_name
   AND pt.project_id IS NULL;

ALTER TABLE project_tokens
    ALTER COLUMN project_id SET NOT NULL;

ALTER TABLE project_tokens
    DROP CONSTRAINT IF EXISTS project_tokens_project_name_fkey;

ALTER TABLE project_tokens
    DROP CONSTRAINT IF EXISTS project_tokens_project_id_fkey;

ALTER TABLE project_tokens
    ADD CONSTRAINT project_tokens_project_id_fkey
        FOREIGN KEY (project_id) REFERENCES project_config(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_project_tokens_project_id ON project_tokens(project_id);

-- ─── project_repos ───────────────────────────────────────────────────────────

ALTER TABLE project_repos
    ADD COLUMN IF NOT EXISTS project_id UUID;

UPDATE project_repos pr
   SET project_id = pc.id
  FROM project_config pc
 WHERE pr.project_name = pc.project_name
   AND pr.project_id IS NULL;

ALTER TABLE project_repos
    ALTER COLUMN project_id SET NOT NULL;

ALTER TABLE project_repos
    DROP CONSTRAINT IF EXISTS project_repos_project_name_fkey;

ALTER TABLE project_repos
    DROP CONSTRAINT IF EXISTS project_repos_project_id_fkey;

ALTER TABLE project_repos
    ADD CONSTRAINT project_repos_project_id_fkey
        FOREIGN KEY (project_id) REFERENCES project_config(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_project_repos_project_id ON project_repos(project_id);

-- ─── scan_results (loose-coupling previously, now FK'd) ──────────────────────

ALTER TABLE scan_results
    ADD COLUMN IF NOT EXISTS project_id UUID;

UPDATE scan_results sr
   SET project_id = pc.id
  FROM project_config pc
 WHERE sr.project_name = pc.project_name
   AND sr.project_id IS NULL;

-- scan_results rows are sometimes written before project_config exists in
-- edge race-condition cases. Keep the column nullable; add an FK that
-- accepts NULL so existing loose-coupling semantics stay intact.
ALTER TABLE scan_results
    DROP CONSTRAINT IF EXISTS scan_results_project_id_fkey;

ALTER TABLE scan_results
    ADD CONSTRAINT scan_results_project_id_fkey
        FOREIGN KEY (project_id) REFERENCES project_config(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_scan_results_project_id ON scan_results(project_id);

-- ─── scan_signals ────────────────────────────────────────────────────────────

ALTER TABLE scan_signals
    ADD COLUMN IF NOT EXISTS project_id UUID;

UPDATE scan_signals ss
   SET project_id = pc.id
  FROM project_config pc
 WHERE ss.project_name = pc.project_name
   AND ss.project_id IS NULL;

ALTER TABLE scan_signals
    DROP CONSTRAINT IF EXISTS scan_signals_project_id_fkey;

ALTER TABLE scan_signals
    ADD CONSTRAINT scan_signals_project_id_fkey
        FOREIGN KEY (project_id) REFERENCES project_config(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_scan_signals_project_id ON scan_signals(project_id);

-- ─── generated_docs ──────────────────────────────────────────────────────────

ALTER TABLE generated_docs
    ADD COLUMN IF NOT EXISTS project_id UUID;

UPDATE generated_docs gd
   SET project_id = pc.id
  FROM project_config pc
 WHERE gd.project_name = pc.project_name
   AND gd.project_id IS NULL;

ALTER TABLE generated_docs
    DROP CONSTRAINT IF EXISTS generated_docs_project_id_fkey;

ALTER TABLE generated_docs
    ADD CONSTRAINT generated_docs_project_id_fkey
        FOREIGN KEY (project_id) REFERENCES project_config(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_generated_docs_project_id ON generated_docs(project_id);

COMMENT ON COLUMN project_tokens.project_id      IS 'ADR-080: FK to project_config(id). project_name kept denormalised for readability.';
COMMENT ON COLUMN project_repos.project_id       IS 'ADR-080: FK to project_config(id). project_name kept denormalised for readability.';
COMMENT ON COLUMN scan_results.project_id        IS 'ADR-080: FK to project_config(id). Nullable/ON DELETE SET NULL — loose coupling preserved.';
COMMENT ON COLUMN scan_signals.project_id        IS 'ADR-080: FK to project_config(id). Nullable/ON DELETE SET NULL.';
COMMENT ON COLUMN generated_docs.project_id      IS 'ADR-080: FK to project_config(id). Nullable/ON DELETE SET NULL.';
