-- ==============================================================================
-- FMS_FILE_SPEC
-- 003_source_connections.sql - DB 스키마 003_source_connections
-- ==============================================================================
-- 설명:
--     - DB 스키마 003_source_connections
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
--     상세 Git 이력: git log --follow -- migrations/003_source_connections.sql
--     공통 규칙: doc/file-header-policy.md
-- ==============================================================================
CREATE TABLE IF NOT EXISTS source_connections (
 source_id uuid PRIMARY KEY, encrypted_config text NOT NULL,
 state text NOT NULL DEFAULT 'saved', last_checked_at timestamptz, updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS collection_cursors (
 source_id uuid NOT NULL, board_key text NOT NULL, high_water bigint NOT NULL DEFAULT 0,
 continuation_page integer, cycle_max bigint NOT NULL DEFAULT 0, last_success_at timestamptz,
 PRIMARY KEY(source_id,board_key));
CREATE UNIQUE INDEX IF NOT EXISTS source_document_identity ON app_records((data->>'source_id'),(data->>'board_key'),(data->>'external_post_id'))
 WHERE kind='document' AND data->>'source_id' IS NOT NULL;
