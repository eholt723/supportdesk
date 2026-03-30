-- Add error column to pipeline_runs for debugging stage failures
ALTER TABLE pipeline_runs ADD COLUMN IF NOT EXISTS error TEXT;
