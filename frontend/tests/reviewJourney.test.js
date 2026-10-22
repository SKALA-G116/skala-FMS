/*
==============================================================================
FMS_FILE_SPEC
reviewJourney.test.js - 기능·경계·회귀 검증
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
    - 작성일: 2026-10-21 (최초 Git 등록일 기준)
    - 라이선스: 미지정
    - 버전: 0.1.0
    - 상태: Development
변경 이력 (Revision History):
    DATE        AUTHOR      VERSION  DESCRIPTION
    --------------------------------------------------------------------
    2026-10-21  미지정      v0.1.0   최초 Git 등록 a11ef05a
    2026-10-21  미지정      v0.1.0   파일 역할·입출력·가정·이력 명세 추가

    2026-10-22  김재현(Finn) v0.1.0   다중 원문 근거 승인·검증 오류 표시·조회 재사용 개선

    2026-10-22  김재현(Finn) v0.1.0   25MB·표 삽입 이미지 근거 보완 및 검수 오류 개선

    상세 Git 이력: git log --follow -- frontend/tests/reviewJourney.test.js
    공통 규칙: doc/file-header-policy.md
==============================================================================
*/
import test from 'node:test';
import assert from 'node:assert/strict';
import {filterReviewItems, nextPendingItem, requiredReviewFields, draftSnapshot} from '../src/utils/reviewJourney.js';

const rows = [
  {id:'a', food_record:{food_name:'우유', company_name:'가업체'}},
  {id:'b', review:{status:'confirmed', fields:{food_record:{food_name:'순살 생선', specification:{original_text:'50g'}}}}},
  {id:'c', review:{status:'skipped'}, food_record:{food_name:'두부'}},
  {id:'d', food_record:{food_name:'우유', company_name:'나업체'}},
];
test('검토 상태와 수정된 표준값으로 검색한다', () => {
  assert.deepEqual(filterReviewItems(rows, 'confirmed', '50g').map(x=>x.id), ['b']);
  assert.deepEqual(filterReviewItems(rows, 'pending', '업체').map(x=>x.id), ['a','d']);
  assert.equal(filterReviewItems(rows, 'all', '없는식품').length, 0);
});
test('다음 대기 품목을 순환 탐색하고 완료 항목은 건너뛴다', () => {
  assert.equal(nextPendingItem(rows,'a').id, 'd');
  assert.equal(nextPendingItem(rows,'d').id, 'a');
  assert.equal(nextPendingItem(rows.filter(x=>x.review), 'b'), undefined);
});
test('공란 허용 속성은 필수 입력으로 취급하지 않는다', () => {
  assert.deepEqual(requiredReviewFields({kind:'food_profile',food_record:{food_name:'우유'}}), []);
  assert.deepEqual(requiredReviewFields({kind:'available',food_record:{food_name:'우유'}}), ['업체','적용 시작일']);
});
test('저장되지 않은 메모와 중첩 속성 변경을 구별한다', () => {
  const draft={food_record:{specification:{quantity:null}}};
  const saved=draftSnapshot(draft,'');
  assert.notEqual(draftSnapshot(draft,'메모'), saved);
  draft.food_record.specification.quantity='0';
  assert.notEqual(draftSnapshot(draft,''), saved);
});
test('구버전 검토 필드에 DTO가 없어도 표준 정보로 검색한다', () => {
  const legacy={id:'old',review:{status:'confirmed',fields:{spec:'old'}},food_record:{food_name:'순살',company_name:'업체',specification:{original_text:'50g'}}};
  assert.deepEqual(filterReviewItems([legacy],'confirmed','순살'), [legacy]);
  assert.deepEqual(filterReviewItems([legacy],'confirmed','50g'), [legacy]);
});

test('승인 오류는 내부 UUID 덤프를 제외하고 중복 안내를 짧게 표시한다', async () => {
  const {reviewErrorMessage}=await import('../src/utils/reviewJourney.js');
  const error={message:'입력값의 형식이 올바르지 않습니다.',data:{error:{details:[{message:"['3dc4886a-aa78-430a-90ec-61b2c043c1d1'] is too long"},...Array(10).fill({message:'항목 수가 허용 범위를 초과했습니다.'})]}}};
  const message=reviewErrorMessage(error);
  assert.equal(message,'입력값의 형식이 올바르지 않습니다. 항목 수가 허용 범위를 초과했습니다.');
  assert.ok(message.length<300);
});
