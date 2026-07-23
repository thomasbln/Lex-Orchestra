-- ADR-083 follow-up: github_token on project_tokens + project_repos moves
-- into vault.secrets. Closes the last plaintext-credential hole so the
-- public Trust Statement ("no third-party API key is stored in plaintext
-- anywhere in the system") is true without qualification.
--
-- Secret naming:
--   project_tokens  → 'github-token-<project_id>'   (one per project)
--   project_repos   → 'github-repo-<repo_id>'       (per-repo override)
--
-- Idempotent via IF [NOT] EXISTS + legacy-column-present guards.

-- ─── project_tokens ──────────────────────────────────────────────────────────

ALTER TABLE project_tokens
    ADD COLUMN IF NOT EXISTS github_token_secret_id UUID;

DO $$
DECLARE
    has_legacy BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM information_schema.columns
         WHERE table_schema = 'public'
           AND table_name   = 'project_tokens'
           AND column_name  = 'github_token'
    ) INTO has_legacy;

    IF has_legacy THEN
        UPDATE project_tokens pt
           SET github_token_secret_id =
               vault.create_secret(pt.github_token,
                                   'github-token-' || pt.project_id::text)
         WHERE pt.github_token IS NOT NULL
           AND TRIM(pt.github_token) <> ''
           AND pt.github_token_secret_id IS NULL;
    END IF;
END $$;

ALTER TABLE project_tokens DROP COLUMN IF EXISTS github_token;

COMMENT ON COLUMN project_tokens.github_token_secret_id
    IS 'ADR-083: vault.secrets(id) reference. NULL = project has no default GitHub PAT.';

-- ─── project_repos ───────────────────────────────────────────────────────────

ALTER TABLE project_repos
    ADD COLUMN IF NOT EXISTS github_token_secret_id UUID;

DO $$
DECLARE
    has_legacy BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM information_schema.columns
         WHERE table_schema = 'public'
           AND table_name   = 'project_repos'
           AND column_name  = 'github_token'
    ) INTO has_legacy;

    IF has_legacy THEN
        UPDATE project_repos pr
           SET github_token_secret_id =
               vault.create_secret(pr.github_token,
                                   'github-repo-' || pr.id::text)
         WHERE pr.github_token IS NOT NULL
           AND TRIM(pr.github_token) <> ''
           AND pr.github_token_secret_id IS NULL;
    END IF;
END $$;

ALTER TABLE project_repos DROP COLUMN IF EXISTS github_token;

COMMENT ON COLUMN project_repos.github_token_secret_id
    IS 'ADR-083: vault.secrets(id) reference. NULL = use project-level default from project_tokens.';
