ALTER TABLE jobs ADD COLUMN IF NOT EXISTS last_slice_at timestamptz;
CREATE INDEX IF NOT EXISTS jobs_lanes ON jobs(type,status,created_at);
