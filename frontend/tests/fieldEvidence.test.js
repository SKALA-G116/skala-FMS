/*
==============================================================================
FMS_FILE_SPEC
fieldEvidence.test.js - 기능·경계·회귀 검증
==============================================================================
설명:
    - 기능·경계·회귀 검증
입력·출력 명세:
    - 입력: 테스트 fixture·가상 입력·명시적 mock/테스트 대역
    - 출력: assert 결과와 실패 사유
실행 가정:
    - DB 통합 테스트는 별도 _test DB·임시 assets 사용; 대역과 실제 모델 검증을 구분
작성 정보:
    - 작성자: 김재현(Finn)
    - 이메일: penguin.klg@gmail.com
    - 작성일: 2026-10-22 (최초 Git 등록일 기준)
    - 라이선스: 미지정
    - 버전: 0.1.0
    - 상태: Development
변경 이력 (Revision History):
    DATE        AUTHOR      VERSION  DESCRIPTION
    --------------------------------------------------------------------
    2026-10-22  미지정      v0.1.0   파일 역할·입출력·가정·이력 명세 추가

    상세 Git 이력: git log --follow -- frontend/tests/fieldEvidence.test.js
    공통 규칙: doc/file-header-policy.md
==============================================================================
*/
import test from 'node:test';
import assert from 'node:assert/strict';
import {fieldEvidenceOptions} from '../src/utils/fieldEvidence.js';

test('선택한 상품의 원재료와 알레르기 근거를 구분하고 다른 상품 참조를 제외한다',()=>{
 const options=fieldEvidenceOptions({ingredients:{evidence_ids:['I1','I2','I1']},allergens:{evidence_ids:['A1','OTHER']},amount:{evidence_ids:['OTHER']}},['I1','I2','A1']);
 assert.deepEqual(options,[{key:'ingredients',label:'원재료',ids:['I1','I2']},{key:'allergens',label:'알레르기',ids:['A1']}]);
});
test('근거가 없는 과거 DTO는 전체 근거 보기로 유지한다',()=>{
 assert.deepEqual(fieldEvidenceOptions({},['E1']),[]);
 assert.deepEqual(fieldEvidenceOptions({ingredients:{evidence_ids:['E2']}},['E1']),[]);
});
