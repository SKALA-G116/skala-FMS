-- ==============================================================================
-- FMS_FILE_SPEC
-- 004_workbook_assets.sql - DB 스키마 004_workbook_assets
-- ==============================================================================
-- 설명:
--     - DB 스키마 004_workbook_assets
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
--     상세 Git 이력: git log --follow -- migrations/004_workbook_assets.sql
--     공통 규칙: doc/file-header-policy.md
-- ==============================================================================
ALTER TABLE price_workbooks ADD COLUMN IF NOT EXISTS asset_id uuid;
UPDATE price_workbooks w SET asset_id=(r.data->>'snapshot_asset_id')::uuid FROM app_records r WHERE r.kind='revision' AND r.id=w.revision_id AND w.asset_id IS NULL;
ALTER TABLE price_workbooks DROP CONSTRAINT IF EXISTS price_workbooks_revision_id_key;
CREATE UNIQUE INDEX IF NOT EXISTS workbook_asset_revision ON price_workbooks(revision_id,asset_id);
