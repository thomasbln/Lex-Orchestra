-- ADR-127 Phase 4 (P4.1) — Owner-editable TOM measures, scan-bound + language-scoped.
--
-- owner_measures: one row per (project_id, control_id, run_id, lang). Carries the
-- per-scan SNAPSHOT of the graph default (default_text/title/framework, written by
-- P4.2) PLUS the owner edit (text/edited_flag). Render priority (P4.3):
--   owner edit (text not null) > config.tom_implementations > snapshot default.
-- Run-immutable (ADR-127 Option B): old scans keep their snapshot, so graph drift
-- never rewrites a frozen scan retroactively. lang in {de,en}; EN rows exist only
-- where the graph carries default_tom_measure_en (today 19 BSI), else DE-only.
--
-- deleted_controls: SEPARATE, language-agnostic soft-delete layer on
-- (project_id, run_id, control_id) — a deactivated control is gone in DE AND EN
-- (consistent docs). Reversible: remove the row -> control renders again.
-- NO c_source column (RoT#2: the builder loads no c.source; the norm citation is
-- derived "{control_id} — {title}").
--
-- FK convention (ADR-080): project_id UUID is the canonical FK to project_config(id);
-- project_name denormalised for psql/log readability. run_id -> scan_results(run_id).
-- Idempotent (CREATE TABLE/INDEX IF NOT EXISTS). Standalone feature migration, NOT
-- folded into the re-runnable scripts/migrate.sql base (same pattern as 014/016).

CREATE TABLE IF NOT EXISTS owner_measures (
    project_id     UUID        NOT NULL REFERENCES project_config(id) ON DELETE CASCADE,
    project_name   TEXT        NOT NULL,
    control_id     TEXT        NOT NULL,
    run_id         UUID        NOT NULL REFERENCES scan_results(run_id) ON DELETE CASCADE,
    lang           TEXT        NOT NULL CHECK (lang IN ('de', 'en')),
    -- owner edit layer
    text           TEXT,                                       -- NULL = unedited; snapshot default renders
    edited_flag    BOOLEAN     NOT NULL DEFAULT FALSE,
    source         TEXT        NOT NULL DEFAULT 'lex-llm-draft',  -- row provenance: lex-llm-draft | owner
    -- per-lang snapshot of the graph default (written at scan time, P4.2)
    default_text   TEXT,
    title          TEXT,
    framework      TEXT,
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (project_id, control_id, run_id, lang)
);

CREATE INDEX IF NOT EXISTS idx_owner_measures_run     ON owner_measures (run_id);
CREATE INDEX IF NOT EXISTS idx_owner_measures_project ON owner_measures (project_id);
CREATE INDEX IF NOT EXISTS idx_owner_measures_edited  ON owner_measures (project_id, run_id) WHERE edited_flag = TRUE;

CREATE TABLE IF NOT EXISTS deleted_controls (
    project_id     UUID        NOT NULL REFERENCES project_config(id) ON DELETE CASCADE,
    project_name   TEXT        NOT NULL,
    run_id         UUID        NOT NULL REFERENCES scan_results(run_id) ON DELETE CASCADE,
    control_id     TEXT        NOT NULL,
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (project_id, run_id, control_id)
);

CREATE INDEX IF NOT EXISTS idx_deleted_controls_run ON deleted_controls (run_id);

COMMENT ON TABLE  owner_measures IS
    'ADR-127 P4.1: per-scan, per-lang owner-editable TOM measures + graph-default snapshot. Run-immutable (Option B).';
COMMENT ON COLUMN owner_measures.text IS
    'Owner edit; NULL = unedited (snapshot default_text renders). Priority: owner > config.tom_implementations > default.';
COMMENT ON COLUMN owner_measures.source IS
    'Row provenance: lex-llm-draft (machine default) | owner (edited).';
COMMENT ON COLUMN owner_measures.default_text IS
    'Snapshot of graph default_tom_measure(_en) at scan time — frozen so graph drift never rewrites an old scan.';
COMMENT ON TABLE  deleted_controls IS
    'ADR-127 P4.1: language-agnostic soft-delete (reversible). Row present = control excluded from DE+EN render.';
COMMENT ON COLUMN deleted_controls.control_id IS
    'Deactivated control for this run; sprach-übergreifend (DE+EN). Remove row to re-enable.';
