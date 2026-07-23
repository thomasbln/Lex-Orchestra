-- ============================================================
-- Lex-Orchestra — Supabase Migration
-- Run via: python scripts/migrate.py
-- Safe to re-run: CREATE TABLE IF NOT EXISTS + CREATE INDEX IF NOT EXISTS
-- ============================================================


-- ============================================================
-- TABLE: scan_results
-- ============================================================

CREATE TABLE IF NOT EXISTS scan_results (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id          UUID NOT NULL UNIQUE,
    project_name    TEXT NOT NULL,
    repo_url        TEXT,
    live_url        TEXT,
    overall_risk    TEXT,
    services_found  INT  DEFAULT 0,
    services_known  INT  DEFAULT 0,
    doc_types       TEXT[],
    scan_depth      TEXT DEFAULT 'quick',
    dry_run         BOOLEAN DEFAULT false,
    errors          TEXT[],
    scanned_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS scan_results_run_id_idx   ON scan_results (run_id);
CREATE INDEX IF NOT EXISTS scan_results_project_idx  ON scan_results (project_name);
CREATE INDEX IF NOT EXISTS scan_results_scanned_at   ON scan_results (scanned_at DESC);


-- ============================================================
-- TABLE: generated_docs
-- ============================================================

CREATE TABLE IF NOT EXISTS generated_docs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id          UUID NOT NULL REFERENCES scan_results(run_id) ON DELETE CASCADE,
    project_name    TEXT NOT NULL,
    doc_type        TEXT NOT NULL,
    file_path       TEXT NOT NULL,
    pdf_path        TEXT,
    version         INT  NOT NULL DEFAULT 1,
    status          TEXT NOT NULL DEFAULT 'draft',
    telegram_sent   BOOLEAN DEFAULT false,
    repo_committed  BOOLEAN DEFAULT false,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS generated_docs_run_id_idx  ON generated_docs (run_id);
CREATE INDEX IF NOT EXISTS generated_docs_project_idx ON generated_docs (project_name);
CREATE INDEX IF NOT EXISTS generated_docs_doc_type_idx ON generated_docs (doc_type);
CREATE INDEX IF NOT EXISTS generated_docs_status_idx  ON generated_docs (status);


-- ============================================================
-- TABLE: project_config
-- ============================================================

CREATE TABLE IF NOT EXISTS project_config (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_name    TEXT NOT NULL UNIQUE,
    company_name    TEXT,
    legal_form      TEXT,
    address         TEXT,
    zip_city        TEXT,
    country         TEXT DEFAULT 'Deutschland',
    contact_email   TEXT,
    contact_phone   TEXT,
    vat_id          TEXT,
    website_url     TEXT,
    extra_urls      TEXT[],
    doc_language    TEXT DEFAULT 'de',
    output_format   TEXT DEFAULT 'pdf',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE project_config ADD COLUMN IF NOT EXISTS responsible_name     TEXT;
ALTER TABLE project_config ADD COLUMN IF NOT EXISTS responsible_title    TEXT;
ALTER TABLE project_config ADD COLUMN IF NOT EXISTS dpo_name             TEXT;
ALTER TABLE project_config ADD COLUMN IF NOT EXISTS dpo_email            TEXT;
ALTER TABLE project_config ADD COLUMN IF NOT EXISTS business_type        TEXT DEFAULT 'saas_b2c';
ALTER TABLE project_config ADD COLUMN IF NOT EXISTS deletion_periods_custom TEXT;
ALTER TABLE project_config ADD COLUMN IF NOT EXISTS register_court       TEXT;
ALTER TABLE project_config ADD COLUMN IF NOT EXISTS register_number      TEXT;
ALTER TABLE project_config ADD COLUMN IF NOT EXISTS tom_implementations  JSONB DEFAULT '{}';
ALTER TABLE project_config ADD COLUMN IF NOT EXISTS ai_usecase_type      TEXT DEFAULT NULL;
-- PR B Phase 0: AI deployer-input layer (see supabase/migrations/021_add_ai_config.sql)
ALTER TABLE project_config ADD COLUMN IF NOT EXISTS ai_config            JSONB DEFAULT '{}';
-- AVV Art. 28 Abs. 3 Satz 2 lit. a — renamed from weisungsbefugte (see migration 022)
ALTER TABLE project_config ADD COLUMN IF NOT EXISTS instructing_persons  JSONB DEFAULT '[]';


-- ============================================================
-- TABLE: project_tokens (ADR-024)
-- ============================================================

CREATE TABLE IF NOT EXISTS project_tokens (
    project_name  TEXT        PRIMARY KEY REFERENCES project_config(project_name) ON DELETE CASCADE,
    repo_url      TEXT        NOT NULL,
    live_url      TEXT,
    github_token  TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- ============================================================
-- HELPER VIEW: current_docs
-- ============================================================

CREATE OR REPLACE VIEW current_docs AS
SELECT DISTINCT ON (project_name, doc_type)
    id, run_id, project_name, doc_type, file_path, pdf_path,
    version, status, telegram_sent, repo_committed, created_at
FROM generated_docs
ORDER BY project_name, doc_type, created_at DESC;


-- ============================================================
-- MIGRATION 004: disclaimer_templates
-- ============================================================

CREATE TABLE IF NOT EXISTS disclaimer_templates (
    id          SERIAL PRIMARY KEY,
    lang        VARCHAR(5)  NOT NULL,
    doc_type    VARCHAR(50),
    content     TEXT        NOT NULL,
    updated_at  TIMESTAMPTZ DEFAULT now()
);

DELETE FROM disclaimer_templates
WHERE doc_type IS NULL
  AND id NOT IN (
      SELECT MAX(id) FROM disclaimer_templates WHERE doc_type IS NULL GROUP BY lang
  );

ALTER TABLE disclaimer_templates
    DROP CONSTRAINT IF EXISTS disclaimer_templates_lang_doc_type_key;

ALTER TABLE disclaimer_templates
    ADD CONSTRAINT disclaimer_templates_lang_doc_type_key
    UNIQUE NULLS NOT DISTINCT (lang, doc_type);

INSERT INTO disclaimer_templates (lang, doc_type, content) VALUES
('de', NULL, E'---\n⚠️ ENTWURF — ARBEITSGRUNDLAGE, KEINE RECHTSBERATUNG\n\nLex-Orchestra dokumentiert die erkannten technischen Systeme und Datenflüsse und\nleitet daraus diesen Entwurf ab. Er dient als Arbeitsgrundlage für Datenschutz-,\nCompliance- und Rechtsberatung und ersetzt keine individuelle rechtliche Prüfung.\nVor produktivem Einsatz ist eine fachliche Prüfung erforderlich.\n\nErstellt von Lex-Orchestra (AGPL-3.0)\nhttps://github.com/thomasbln/Lex-Orchestra\n---'),
('de', 'avv', E'---\n⚠️ ENTWURF — ARBEITSGRUNDLAGE, KEINE RECHTSBERATUNG\n\nDieser AVV-Entwurf wurde aus den erkannten Auftragsverarbeitern abgeleitet und ist\neine Arbeitsgrundlage zur fachlichen Prüfung. Er ist nicht unmittelbar\nunterschriftsreif und stellt keinen rechtsverbindlichen Vertrag dar; vor Abschluss\nist eine individuelle Prüfung und Anpassung erforderlich.\n\nErstellt von Lex-Orchestra (AGPL-3.0)\nhttps://github.com/thomasbln/Lex-Orchestra\n---'),
('de', 'tom', E'---\n⚠️ ENTWURF — ARBEITSGRUNDLAGE, KEINE RECHTSBERATUNG\n\nDiese technischen und organisatorischen Maßnahmen wurden aus dem erkannten\nTechnik-Stack abgeleitet und sind eine Arbeitsgrundlage zur fachlichen Prüfung.\nVollständigkeit und Rechtskonformität sind unternehmensspezifisch zu prüfen und\ndurch einen Datenschutzbeauftragten zu bestätigen.\n\nErstellt von Lex-Orchestra (AGPL-3.0)\nhttps://github.com/thomasbln/Lex-Orchestra\n---'),
('de', 'ai_act', E'---\n⚠️ ENTWURF — ARBEITSGRUNDLAGE, KEINE RECHTSBERATUNG\n\nDie vorgeschlagene Risikoeinstufung wurde aus den erkannten KI-Diensten abgeleitet\nund ist nicht verbindlich. Die finale Klassifizierung nach EU AI Act erfordert eine\nfachliche Prüfung durch einen qualifizierten Rechtsberater.\n\nErstellt von Lex-Orchestra (AGPL-3.0)\nhttps://github.com/thomasbln/Lex-Orchestra\n---'),
('de', 'vvt', E'---\n⚠️ ENTWURF — ARBEITSGRUNDLAGE, KEINE RECHTSBERATUNG\n\nDieses Verzeichnis von Verarbeitungstätigkeiten wurde aus den erkannten Diensten\nund Datenflüssen abgeleitet und ist eine Arbeitsgrundlage zur fachlichen Prüfung.\nRechtsgrundlagen und Datenkategorien sind durch einen Datenschutzbeauftragten zu\nprüfen.\n\nErstellt von Lex-Orchestra (AGPL-3.0)\nhttps://github.com/thomasbln/Lex-Orchestra\n---'),
('en', NULL, E'---\n⚠️ AUTO-GENERATED DRAFT – NOT LEGAL ADVICE\n\nThis document was automatically generated by Lex-Orchestra and serves solely\nas a technical template to support compliance documentation.\n\nIt does not replace individual legal advice and must be reviewed and adapted\nby a qualified legal professional before use.\n\nGenerated by Lex-Orchestra (AGPL-3.0)\nhttps://github.com/thomasbln/Lex-Orchestra\n---'),
('en', 'avv', E'---\n⚠️ AUTO-GENERATED DRAFT – NOT LEGAL ADVICE\n\nThis DPA draft is not immediately ready for signature and must be individually\nreviewed and adapted before execution. It does not constitute a binding contract.\n\nGenerated by Lex-Orchestra (AGPL-3.0)\nhttps://github.com/thomasbln/Lex-Orchestra\n---'),
('en', 'tom', E'---\n⚠️ AUTO-GENERATED DRAFT – NOT LEGAL ADVICE\n\nExemplary technical and organisational measures (to be reviewed and adapted per\norganisation). Completeness and legal compliance must be confirmed by a DPO.\n\nGenerated by Lex-Orchestra (AGPL-3.0)\nhttps://github.com/thomasbln/Lex-Orchestra\n---'),
('en', 'ai_act', E'---\n⚠️ AUTO-GENERATED DRAFT – NOT LEGAL ADVICE\n\nProposed risk classification (non-binding). Final classification under the EU AI Act\nrequires review by a qualified legal advisor.\n\nGenerated by Lex-Orchestra (AGPL-3.0)\nhttps://github.com/thomasbln/Lex-Orchestra\n---'),
('en', 'vvt', E'---\n⚠️ AUTO-GENERATED DRAFT – NOT LEGAL ADVICE\n\nThis Record of Processing Activities was automatically generated.\nLegal bases and data categories must be verified by a Data Protection Officer.\n\nGenerated by Lex-Orchestra (AGPL-3.0)\nhttps://github.com/thomasbln/Lex-Orchestra\n---')
ON CONFLICT (lang, doc_type) DO UPDATE SET
    content    = EXCLUDED.content,
    updated_at = now();


-- ============================================================
-- MIGRATION 006: scan_signals (ADR-027)
-- ============================================================

CREATE TABLE IF NOT EXISTS scan_signals (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id       UUID        NOT NULL REFERENCES scan_results(run_id) ON DELETE CASCADE,
    project_name TEXT        NOT NULL,
    signal_type  TEXT        NOT NULL,
    value        TEXT,
    confidence   FLOAT       NOT NULL CHECK (confidence BETWEEN 0 AND 1),
    evidence     TEXT[]      NOT NULL DEFAULT '{}',
    source       TEXT        DEFAULT 'regex',
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_scan_signals_run_id      ON scan_signals(run_id);
CREATE INDEX IF NOT EXISTS idx_scan_signals_project     ON scan_signals(project_name);
CREATE INDEX IF NOT EXISTS idx_scan_signals_signal_type ON scan_signals(signal_type);


-- ============================================================
-- MIGRATION 007 + 008: zip_code + city (split from zip_city) + drop zip_city
-- ============================================================

ALTER TABLE project_config ADD COLUMN IF NOT EXISTS zip_code TEXT;
ALTER TABLE project_config ADD COLUMN IF NOT EXISTS city     TEXT;
ALTER TABLE project_config DROP COLUMN IF EXISTS zip_city;


-- ============================================================
-- MIGRATION 009: Onboarding Wizard + Multi-repo (ADR-037, ADR-033)
-- ============================================================

-- ADR-037: eRecht24 fields — superseded by ADR-082/083 (migration 016).
-- Fresh installs get these columns dropped again by 016; legacy rows are
-- backfilled into project_integrations + vault.secrets. Left here so the
-- consolidated migrate.sql replays the original 008 shape before 016 runs.
ALTER TABLE project_config ADD COLUMN IF NOT EXISTS erecht24_api_key TEXT;
ALTER TABLE project_config ADD COLUMN IF NOT EXISTS erecht24_domain  TEXT;

-- ADR-033: Multi-repo support
CREATE TABLE IF NOT EXISTS project_repos (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    project_name TEXT        NOT NULL REFERENCES project_config(project_name) ON DELETE CASCADE,
    repo_url     TEXT        NOT NULL,
    label        TEXT        NOT NULL DEFAULT 'main',
    github_token TEXT,
    is_primary   BOOLEAN     NOT NULL DEFAULT FALSE,
    is_active    BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_project_repos_primary
    ON project_repos (project_name)
    WHERE is_primary = TRUE;

CREATE UNIQUE INDEX IF NOT EXISTS uq_project_repos_url
    ON project_repos (project_name, repo_url);
