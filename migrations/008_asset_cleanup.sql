CREATE TABLE IF NOT EXISTS asset_cleanup (
 storage_key text PRIMARY KEY, created_at timestamptz NOT NULL DEFAULT now(),
 attempts integer NOT NULL DEFAULT 0, last_error text);
CREATE TABLE IF NOT EXISTS purged_source_posts (
 source_id text NOT NULL, board_key text NOT NULL, external_post_id text NOT NULL,
 purged_at timestamptz NOT NULL DEFAULT now(),
 PRIMARY KEY(source_id,board_key,external_post_id));
