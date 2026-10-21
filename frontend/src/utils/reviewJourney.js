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
