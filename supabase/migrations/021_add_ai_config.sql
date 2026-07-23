-- PR B Phase 0: AI deployer-input layer for the EU AI Act doc types.
-- Backs the eight user-input gap fields surfaced as bare ✏️ markers in
-- ki_system / ai_act_manifest / ki_policy (PR-3 / PR-B inventory).
--
-- Single JSONB column so new fields are added without further migrations.
-- Structure:
--   ai_config = {
--     "per_service":   { "<scan service name>": {
--                          nutzergruppen, grenzen, training_data,
--                          logging, review_date } },   -- per AI service
--     "project_level": { operative_responsible,
--                        tech_responsible,
--                        ki_policy_review_date }        -- once per project
--   }
-- The per_service map is keyed by the scan service name so the (M)-class
-- fields (eingabedaten/ausgabedaten/modell_version/integration) can later be
-- added as additional per-service keys WITHOUT a new migration.
ALTER TABLE project_config
  ADD COLUMN IF NOT EXISTS ai_config JSONB DEFAULT '{}'::jsonb;

COMMENT ON COLUMN project_config.ai_config IS
  'AI deployer-input layer (EU AI Act). {per_service: {<service>: {nutzergruppen, grenzen, training_data, logging, review_date}}, project_level: {operative_responsible, tech_responsible, ki_policy_review_date}}';
