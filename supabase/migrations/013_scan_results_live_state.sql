-- ADR-068: extend scan_results with live-state fields for scan-status page.
-- Backwards compatible — existing rows get status='complete' (they are finished).
-- run_id (UUID, UNIQUE) stays the join key for scan_signals + generated_docs.

ALTER TABLE scan_results
  ADD COLUMN IF NOT EXISTS status         TEXT        DEFAULT 'complete',
  ADD COLUMN IF NOT EXISTS step           TEXT        DEFAULT 'docgen',
  ADD COLUMN IF NOT EXISTS started_at     TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS completed_at   TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS error          TEXT,
  ADD COLUMN IF NOT EXISTS triggered_by   TEXT        DEFAULT 'manual',
  ADD COLUMN IF NOT EXISTS docs_generated INTEGER     DEFAULT 0;

-- Backfill started_at from scanned_at for existing rows (one-time).
UPDATE scan_results
SET started_at = scanned_at
WHERE started_at IS NULL;

-- Backfill completed_at from scanned_at for rows that are 'complete'.
UPDATE scan_results
SET completed_at = scanned_at
WHERE completed_at IS NULL AND status = 'complete';

-- New rows: started_at must be set explicitly on INSERT (cannot default to now()
-- yet because we want to keep scanned_at semantics for "final snapshot" time).

-- Value constraints (soft — keep schema permissive).
ALTER TABLE scan_results
  DROP CONSTRAINT IF EXISTS scan_results_status_check;
ALTER TABLE scan_results
  ADD CONSTRAINT scan_results_status_check
  CHECK (status IN ('running', 'complete', 'failed'));

ALTER TABLE scan_results
  DROP CONSTRAINT IF EXISTS scan_results_step_check;
ALTER TABLE scan_results
  ADD CONSTRAINT scan_results_step_check
  CHECK (step IN ('clone', 'infra', 'signals', 'graph', 'docgen'));

-- Index for dashboard status polling: "latest running/failed per project"
CREATE INDEX IF NOT EXISTS idx_scan_results_status ON scan_results(status);
CREATE INDEX IF NOT EXISTS idx_scan_results_started_at ON scan_results(started_at DESC);

COMMENT ON COLUMN scan_results.status         IS 'running | complete | failed — lifecycle state (ADR-068)';
COMMENT ON COLUMN scan_results.step           IS 'Current pipeline step: clone|infra|signals|graph|docgen (ADR-068)';
COMMENT ON COLUMN scan_results.started_at     IS 'When /scan/start was called (ADR-068)';
COMMENT ON COLUMN scan_results.completed_at   IS 'When scan reached complete/failed (ADR-068)';
COMMENT ON COLUMN scan_results.error          IS 'Error message when status=failed (ADR-068)';
COMMENT ON COLUMN scan_results.triggered_by   IS 'setup | manual | webhook (ADR-068)';
COMMENT ON COLUMN scan_results.docs_generated IS 'Count of docs produced — filled at scan end (ADR-068)';
