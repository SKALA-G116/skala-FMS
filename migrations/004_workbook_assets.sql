ALTER TABLE price_workbooks ADD COLUMN IF NOT EXISTS asset_id uuid;
UPDATE price_workbooks w SET asset_id=(r.data->>'snapshot_asset_id')::uuid FROM app_records r WHERE r.kind='revision' AND r.id=w.revision_id AND w.asset_id IS NULL;
ALTER TABLE price_workbooks DROP CONSTRAINT IF EXISTS price_workbooks_revision_id_key;
CREATE UNIQUE INDEX IF NOT EXISTS workbook_asset_revision ON price_workbooks(revision_id,asset_id);
