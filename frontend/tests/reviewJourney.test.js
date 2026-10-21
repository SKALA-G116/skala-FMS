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
