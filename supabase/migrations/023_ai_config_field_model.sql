-- ADR-124 Gate A — KI-Angaben field model: ai_config content transform.
--
-- ONE-TIME DATA migration (not schema): ai_config is already a single JSONB
-- column (021), so there is NO DDL. This rewrites the JSONB content of existing
-- rows. Fresh installs start with ai_config = '{}' and the new frontend writes
-- the new keys directly, so they need no transform — hence this is NOT folded
-- into the re-runnable scripts/migrate.sql; apply once via psql on NucBox.
--
-- Per service entry (per_service.<svc>) the target shape is exactly 6 keys:
--   model, purpose        (NEW, default JSON null)
--   training_data, logging (tri-state bool|null)
--   usage_limits          (renamed from grenzen, value carried over)
--   user_groups           (renamed from nutzergruppen, value carried over)
-- review_date is dropped (not carried). grenzen/nutzergruppen are dropped after
-- their values are copied.
--
-- project_level target keys:
--   operative_responsible, tech_responsible (kept)
--   ai_literacy_measures, ai_literacy_note   (NEW, Art. 4)
-- ki_policy_review_date is dropped.
--
-- ⚠️ Coercion correction (Gate-A read-of-truth, 2026-06-07): the ADR-124 draft
-- assumed legacy training_data/logging strings were presence markers → true.
-- The live rand-industries row holds training_data="Kein Fine-Tuning" — a
-- NEGATIVE answer. Coercing any non-empty string to `true` would assert a false
-- fact in a legal document. No mechanical rule can read negation reliably, so
-- legacy strings coerce to JSON null (unset → gap); the deployer re-confirms via
-- the Gate-D tri-state toggle. Only an already-boolean value is preserved.
--
-- Idempotent: re-running is a no-op. Renames use coalesce(new, old) so the
-- already-renamed value wins; coercion preserves booleans and re-nulls strings;
-- rebuilding the object from a fixed key set drops removed keys every run.

UPDATE project_config pc
SET ai_config = jsonb_build_object(
    'per_service', (
        SELECT coalesce(
            jsonb_object_agg(
                svc.key,
                jsonb_build_object(
                    'model',         coalesce(svc.value->'model',   'null'::jsonb),
                    'purpose',       coalesce(svc.value->'purpose', 'null'::jsonb),
                    'training_data',
                        CASE WHEN jsonb_typeof(svc.value->'training_data') = 'boolean'
                             THEN svc.value->'training_data' ELSE 'null'::jsonb END,
                    'logging',
                        CASE WHEN jsonb_typeof(svc.value->'logging') = 'boolean'
                             THEN svc.value->'logging' ELSE 'null'::jsonb END,
                    'usage_limits',  coalesce(svc.value->'usage_limits', svc.value->'grenzen',       'null'::jsonb),
                    'user_groups',   coalesce(svc.value->'user_groups',  svc.value->'nutzergruppen', 'null'::jsonb)
                )
            ),
            '{}'::jsonb
        )
        FROM jsonb_each(coalesce(pc.ai_config->'per_service', '{}'::jsonb)) AS svc
    ),
    'project_level', (
        SELECT jsonb_build_object(
            'operative_responsible', pl->'operative_responsible',
            'tech_responsible',      pl->'tech_responsible',
            'ai_literacy_measures',
                CASE WHEN jsonb_typeof(pl->'ai_literacy_measures') = 'boolean'
                     THEN pl->'ai_literacy_measures' ELSE 'null'::jsonb END,
            'ai_literacy_note',      coalesce(pl->'ai_literacy_note', 'null'::jsonb)
        )
        FROM (SELECT coalesce(pc.ai_config->'project_level', '{}'::jsonb) AS pl) s
    )
)
WHERE pc.ai_config IS NOT NULL
  AND pc.ai_config::text <> '{}';
