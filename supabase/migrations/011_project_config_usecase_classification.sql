-- ADR-029: auto-classified AI usecase fields
ALTER TABLE project_config
  ADD COLUMN IF NOT EXISTS ai_usecase_verified    BOOLEAN     DEFAULT false,
  ADD COLUMN IF NOT EXISTS ai_usecase_source      TEXT,       -- 'phi4_mini_classification' | 'manual'
  ADD COLUMN IF NOT EXISTS ai_usecase_confidence  FLOAT;      -- 0.0 - 1.0

COMMENT ON COLUMN project_config.ai_usecase_verified   IS 'ADR-029: confirmed via Telegram /confirm_usecase';
COMMENT ON COLUMN project_config.ai_usecase_source     IS 'ADR-029: phi4_mini_classification | manual';
COMMENT ON COLUMN project_config.ai_usecase_confidence IS 'ADR-029: Phi-4-mini classification confidence';
