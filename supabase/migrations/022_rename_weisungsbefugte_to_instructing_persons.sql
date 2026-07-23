-- Rename project_config.weisungsbefugte → instructing_persons.
--
-- Convention: project_config identifiers are English; weisungsbefugte was the
-- last German column name. One identifier across all layers (column, JSONB key,
-- builder var, template var, gap field, fix_url section, VALID_SECTIONS, HTTP
-- route) — see the rename sweep. UI label + AVV § 3 legal text stay German.
--
-- 020 (which created weisungsbefugte) stays as historical record; this migration
-- renames it. Idempotent: only renames when the old column exists and the new
-- one does not, so re-runs and fresh installs (which never had weisungsbefugte)
-- are both safe.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'project_config' AND column_name = 'weisungsbefugte'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'project_config' AND column_name = 'instructing_persons'
    ) THEN
        ALTER TABLE project_config RENAME COLUMN weisungsbefugte TO instructing_persons;
    END IF;
END $$;

-- Fresh installs that never ran 020 get the column directly.
ALTER TABLE project_config
  ADD COLUMN IF NOT EXISTS instructing_persons JSONB DEFAULT '[]'::jsonb;

COMMENT ON COLUMN project_config.instructing_persons IS
  'Array of {name, title} objects — weisungsberechtigte Personen für AVV Art. 28 Abs. 3 Satz 2 lit. a (renamed from weisungsbefugte)';
