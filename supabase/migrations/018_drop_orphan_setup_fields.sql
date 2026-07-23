-- ADR-084: Drop orphan fields from project_setups
-- homeoffice / training_frequency / contract_duration: collected but never read by any template
-- dpo_name / dpo_email: ADR-076 DPO override rollback — project_config is now authoritative
-- Art. 5(1)(c) GDPR: no obligation to retain data that should not have been collected.

ALTER TABLE project_setups DROP COLUMN IF EXISTS homeoffice;
ALTER TABLE project_setups DROP COLUMN IF EXISTS training_frequency;
ALTER TABLE project_setups DROP COLUMN IF EXISTS contract_duration;
ALTER TABLE project_setups DROP COLUMN IF EXISTS dpo_name;
ALTER TABLE project_setups DROP COLUMN IF EXISTS dpo_email;
