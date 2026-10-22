/*
==============================================================================
FMS_FILE_SPEC
agentLogs.test.js - 기능·경계·회귀 검증
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

    2026-10-22  김재현(Finn) v0.1.0   자료·Agent·검수 승인·식품 DB 중심 흐름 및 알레르기 표기 정리

    상세 Git 이력: git log --follow -- frontend/tests/agentLogs.test.js
    공통 규칙: doc/file-header-policy.md
==============================================================================
*/
import test from 'node:test';
import assert from 'node:assert/strict';
import {jobNotices,agentSteps} from '../src/utils/agentLogs.js';

test('수집 범위 안내는 오류와 분리하고 게시판별로 한 번만 표시한다',()=>{
 const notices=jobNotices([{code:'SOURCE_SIZE',filename:'big.pdf'},{code:'SCAN_CONTINUES',board:'product_01'},{code:'SCAN_CONTINUES',board:'product_01'},{code:'SCAN_CONTINUES',board:'product_del'}]);
 assert.equal(notices.errors.length,1);assert.deepEqual(notices.continuation.boards,['공산품','단종제품']);
 assert.equal(jobNotices([]).continuation,null);
});
test('도구 선택·실행 중·입력 준비·검수 필요를 서로 구분한다',()=>{
 const report={status:'interpreting',plan:{routes:[{source_id:'D1',tool:'extract_text'},{source_id:'D2',tool:'extract_image_regions'},{source_id:'D3',tool:'request_review'}]},tool_results:{D1:{trace:{source_id:'D1'}},D3:{trace:{source_id:'D3',review_required:{code:'IMAGE_REGION_SOURCE'}}}},active_tool:{source_id:'D2'}};
 assert.deepEqual(agentSteps(report).map(s=>s.state),['prepared','running','review']);
 report.status='completed';delete report.active_tool;
 assert.deepEqual(agentSteps(report).map(s=>s.state),['completed','pending','review']);
});
