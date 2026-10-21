ALTER TABLE price_sheets ADD COLUMN IF NOT EXISTS source_header jsonb;
UPDATE price_sheets SET source_header=columns WHERE source_header IS NULL;
