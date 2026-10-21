CREATE TABLE IF NOT EXISTS record_archives (
 record_kind text NOT NULL CHECK(record_kind IN ('food','document')),
 record_id uuid NOT NULL, archived boolean NOT NULL DEFAULT false,
 version integer NOT NULL CHECK(version>0), actor_id text NOT NULL,
 reason text NOT NULL, updated_at timestamptz NOT NULL DEFAULT now(),
 PRIMARY KEY(record_kind,record_id));
CREATE INDEX IF NOT EXISTS record_archives_deleted ON record_archives(record_kind,record_id) WHERE archived;
