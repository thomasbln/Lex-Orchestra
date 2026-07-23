-- Fix: add last_scan column to project_config (referenced in node_scout)
ALTER TABLE project_config
  ADD COLUMN IF NOT EXISTS last_scan TIMESTAMPTZ;

COMMENT ON COLUMN project_config.last_scan IS 'Timestamp of most recent scan run for this project';
