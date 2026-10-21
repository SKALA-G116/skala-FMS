CREATE TABLE IF NOT EXISTS source_connections (
 source_id uuid PRIMARY KEY, encrypted_config text NOT NULL,
 state text NOT NULL DEFAULT 'saved', last_checked_at timestamptz, updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS collection_cursors (
 source_id uuid NOT NULL, board_key text NOT NULL, high_water bigint NOT NULL DEFAULT 0,
 continuation_page integer, cycle_max bigint NOT NULL DEFAULT 0, last_success_at timestamptz,
 PRIMARY KEY(source_id,board_key));
CREATE UNIQUE INDEX IF NOT EXISTS source_document_identity ON app_records((data->>'source_id'),(data->>'board_key'),(data->>'external_post_id'))
 WHERE kind='document' AND data->>'source_id' IS NOT NULL;
