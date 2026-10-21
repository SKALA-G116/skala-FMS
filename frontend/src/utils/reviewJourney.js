/*
==============================================================================
FMS_FILE_SPEC
reviewJourney.js - Vue 애플리케이션 reviewJourney
==============================================================================
설명:
    - Vue 애플리케이션 reviewJourney
입력·출력 명세:
    - 입력: 애플리케이션·라우트·상태·빌드 설정
    - 출력: 화면·공유 상태·빌드 산출물
실행 가정:
    - 설치 의존성과 생성 lock 파일은 원본 형식을 유지
작성 정보:
    - 작성자: 미지정
    - 이메일: 미지정
    - 작성일: 2026-10-21 (최초 Git 등록일 기준)
    - 라이선스: 미지정
    - 버전: 0.1.0
    - 상태: Development
변경 이력 (Revision History):
    DATE        AUTHOR      VERSION  DESCRIPTION
    --------------------------------------------------------------------
    2026-10-21  미지정      v0.1.0   최초 Git 등록 a11ef05a
    2026-10-21  미지정      v0.1.0   파일 역할·입출력·가정·이력 명세 추가

    상세 Git 이력: git log --follow -- frontend/src/utils/reviewJourney.js
    공통 규칙: doc/file-header-policy.md
==============================================================================
*/
export const reviewStatus = item => item.review?.status || 'pending';
export const reviewName = item => (item.review?.fields?.food_record || item.food_record)?.food_name || item.product_name || '이름 확인 필요';
export const draftSnapshot = (draft, reason) => JSON.stringify({draft, reason});

export function filterReviewItems(items, filter, query) {
  const term = query.trim().toLocaleLowerCase();
  return items.filter(item => {
    const current = item.review?.fields || item;
    return (filter === 'all' || reviewStatus(item) === filter)
      && (!term || [reviewName(item), current.food_record?.company_name || item.food_record?.company_name, (current.food_record || item.food_record)?.specification?.original_text || current.spec]
        .some(value => value?.toLocaleLowerCase().includes(term)));
  });
}

export function nextPendingItem(items, selected) {
  const index = items.findIndex(item => item.id === selected);
  return [...items.slice(index + 1), ...items.slice(0, index)].find(item => reviewStatus(item) === 'pending');
}

export function requiredReviewFields(draft) {
  const missing = [];
  if (!draft.food_record?.food_name?.trim()) missing.push('식품명');
  if (!['food_profile', 'new_product'].includes(draft.kind)) {
    if (!draft.food_record?.company_name?.trim()) missing.push('업체');
    if (!draft.effective_from) missing.push('적용 시작일');
  }
  return missing;
}
