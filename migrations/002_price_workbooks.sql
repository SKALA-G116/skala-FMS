-- ==============================================================================
-- FMS_FILE_SPEC
-- 002_price_workbooks.sql - DB 스키마 002_price_workbooks
-- ==============================================================================
-- 설명:
--     - DB 스키마 002_price_workbooks
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
--     상세 Git 이력: git log --follow -- migrations/002_price_workbooks.sql
--     공통 규칙: doc/file-header-policy.md
-- ==============================================================================
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
