CREATE TABLE IF NOT EXISTS app_records (
 kind text NOT NULL, id uuid NOT NULL, data jsonb NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now(), PRIMARY KEY(kind,id));
CREATE INDEX IF NOT EXISTS records_page ON app_records(kind,created_at DESC,id DESC);
CREATE INDEX IF NOT EXISTS records_json ON app_records USING gin(data);
CREATE TABLE IF NOT EXISTS catalog_entities (
 id uuid PRIMARY KEY, kind text NOT NULL CHECK(kind IN ('product','variant','supplier_item')),
 parent_id uuid REFERENCES catalog_entities(id), supplier_id uuid,
 name text, version integer NOT NULL DEFAULT 1 CHECK(version>0), data jsonb NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now());
CREATE INDEX IF NOT EXISTS entity_parent ON catalog_entities(parent_id);
CREATE UNIQUE INDEX IF NOT EXISTS supplier_item_code ON catalog_entities(supplier_id,(data->>'supplier_code'))
 WHERE kind='supplier_item' AND data->>'supplier_code' IS NOT NULL;
CREATE TABLE IF NOT EXISTS facts (
 id uuid PRIMARY KEY, kind text NOT NULL, target_id uuid NOT NULL REFERENCES catalog_entities(id),
 condition_key text NOT NULL DEFAULT '', amount numeric(20,4), effective_from date NOT NULL,
 effective_to date, supersedes_fact_id uuid REFERENCES facts(id), data jsonb NOT NULL,
 recorded_at timestamptz NOT NULL DEFAULT now(), CHECK(effective_to IS NULL OR effective_to>effective_from));
CREATE INDEX IF NOT EXISTS facts_target ON facts(target_id,kind,effective_from);
CREATE TABLE IF NOT EXISTS sessions (
 token_hash text PRIMARY KEY, user_id uuid NOT NULL, csrf text NOT NULL,
 expires_at timestamptz NOT NULL);
CREATE TABLE IF NOT EXISTS command_keys (
 scope text PRIMARY KEY, body_hash text NOT NULL, status integer NOT NULL, response jsonb NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS jobs (
 id uuid PRIMARY KEY, type text NOT NULL, status text NOT NULL DEFAULT 'queued', data jsonb NOT NULL,
 payload jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now(), lease_until timestamptz,
 fence integer NOT NULL DEFAULT 0);
CREATE INDEX IF NOT EXISTS jobs_claim ON jobs(status,created_at);
CREATE TABLE IF NOT EXISTS applications (
 id uuid PRIMARY KEY, proposal_id uuid NOT NULL, approved_revision integer NOT NULL, data jsonb NOT NULL,
 UNIQUE(proposal_id,approved_revision));
