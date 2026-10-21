CREATE TABLE IF NOT EXISTS price_workbooks (
 id uuid PRIMARY KEY, document_id uuid NOT NULL, revision_id uuid NOT NULL UNIQUE,
 filename text NOT NULL, content_sha256 text NOT NULL, created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS price_sheets (
 id uuid PRIMARY KEY, workbook_id uuid NOT NULL REFERENCES price_workbooks(id),
 name text NOT NULL, position integer NOT NULL, header_row integer NOT NULL,
 columns jsonb NOT NULL, row_count integer NOT NULL, UNIQUE(workbook_id,position));
CREATE TABLE IF NOT EXISTS price_sheet_rows (
 sheet_id uuid NOT NULL REFERENCES price_sheets(id), row_number integer NOT NULL,
 cells jsonb NOT NULL, numbers jsonb NOT NULL, PRIMARY KEY(sheet_id,row_number));
