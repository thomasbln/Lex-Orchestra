-- ADR-098 PR1 Task 1.3: Add weisungsbefugte field for AVV Art. 28 Abs. 3 Satz 2 lit. a
-- Array of {name, title} objects — weisungsberechtigte Personen des Verantwortlichen
ALTER TABLE project_config
  ADD COLUMN IF NOT EXISTS weisungsbefugte JSONB DEFAULT '[]'::jsonb;

COMMENT ON COLUMN project_config.weisungsbefugte IS
  'Array of {name, title} objects — weisungsberechtigte Personen für AVV Art. 28 Abs. 3 Satz 2 lit. a';
