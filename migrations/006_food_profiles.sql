-- ==============================================================================
-- FMS_FILE_SPEC
-- 006_food_profiles.sql - DB 스키마 006_food_profiles
-- ==============================================================================
-- 설명:
--     - DB 스키마 006_food_profiles
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
--     상세 Git 이력: git log --follow -- migrations/006_food_profiles.sql
--     공통 규칙: doc/file-header-policy.md
-- ==============================================================================
CREATE TABLE IF NOT EXISTS food_profiles (
 variant_id uuid PRIMARY KEY REFERENCES catalog_entities(id),
 product_id uuid NOT NULL REFERENCES catalog_entities(id),
 food_code text, schema_version text NOT NULL,
 version integer NOT NULL CHECK(version>0), data jsonb NOT NULL,
 updated_at timestamptz NOT NULL DEFAULT now());
CREATE INDEX IF NOT EXISTS food_profiles_code ON food_profiles(food_code);
CREATE INDEX IF NOT EXISTS food_profiles_product ON food_profiles(product_id);
CREATE INDEX IF NOT EXISTS food_profiles_attributes ON food_profiles USING gin(data);
