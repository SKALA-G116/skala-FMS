-- ==============================================================================
-- FMS_FILE_SPEC
-- 001_initial.sql - DB 스키마 001_initial
-- ==============================================================================
-- 설명:
--     - DB 스키마 001_initial
-- 입력·출력 명세:
--     - 입력: 순서대로 실행하는 PostgreSQL migration
--     - 출력: 테이블·인덱스·제약 또는 저장 구조 변경
-- 실행 가정:
--     - 배포 환경 DB와 변경 순서를 확인하고 운영 데이터를 임의 초기화하지 않음
-- 작성 정보:
--     - 작성자: 미지정
--     - 이메일: 미지정
--     - 작성일: 2026-10-21 (최초 Git 등록일 기준)
--     - 라이선스: 미지정
--     - 버전: 0.1.0
--     - 상태: Development
-- 변경 이력 (Revision History):
--     DATE        AUTHOR      VERSION  DESCRIPTION
--     --------------------------------------------------------------------
--     2026-10-21  미지정      v0.1.0   최초 Git 등록 a11ef05a
--     2026-10-21  미지정      v0.1.0   파일 역할·입출력·가정·이력 명세 추가
--
--     상세 Git 이력: git log --follow -- migrations/001_initial.sql
--     공통 규칙: doc/file-header-policy.md
-- ==============================================================================
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
