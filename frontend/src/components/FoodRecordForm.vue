<!--
==============================================================================
FMS_FILE_SPEC
FoodRecordForm.vue - 표준 식품 정보 편집
==============================================================================
설명:
    - 표준 식품 정보 편집
입력·출력 명세:
    - 입력: props·표준 DTO·상위 화면 상태
    - 출력: 표시 결과와 emit 이벤트
실행 가정:
    - 업무 반영은 권한 있는 API를 통해 수행하고 컴포넌트가 직접 DB에 접근하지 않음
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

    2026-10-21  미지정      v0.1.0   원본 속성 누락 복구·재정리 API·검토 동선 개선

    2026-10-21  김재현(Finn) v0.1.0   Agent 도구 선택 기반 리빌드·업무 경계 및 검증

    2026-10-22  김재현(Finn) v0.1.0   자료·Agent·검수 승인·식품 DB 중심 흐름 및 알레르기 표기 정리

    2026-10-22  김재현(Finn) v0.1.0   승인 단가 조회·참고 가격 표시 분리 및 승인 후 연결 검증

    상세 Git 이력: git log --follow -- frontend/src/components/FoodRecordForm.vue
    공통 규칙: doc/file-header-policy.md
==============================================================================
-->
<script setup>
import {computed} from 'vue';
const props=defineProps({modelValue:Object,companies:{type:Array,default:()=>[]},readonly:Boolean,compact:Boolean});const emit=defineEmits(['update:modelValue']);
const food=computed(()=>props.modelValue);
function set(path,value){const next=JSON.parse(JSON.stringify(food.value));const keys=path.split('.');let obj=next;for(const key of keys.slice(0,-1))obj=obj[key];obj[keys.at(-1)]=value===''?null:value;if(path==='company_name')next.company_id=props.companies.find(c=>c.name===value)?.id||null;emit('update:modelValue',next)}
const attrs={flavor:'맛·종류',origin_region:'산지',size_grade:'크기 구분',quality_grade:'품질 등급',intended_use:'사용 용도',labeling_requirement:'표시 기준',origin_country:'원산지'};
const specs={piece_quantity:'낱개 중량·용량',piece_unit:'낱개 단위',pack_count:'포장 수량',quantity:'전체 중량·용량',unit:'전체 단위',sales_unit:'판매 단위'};
const prices={source_applied:'자료의 적용가',survey_1:'조사가 1',survey_2:'조사가 2',survey_3:'조사가 3'};
const allergens={egg:'난류',milk:'우유',buckwheat:'메밀',peanut:'땅콩',soy:'대두',wheat:'밀',mackerel:'고등어',crab:'게',shrimp:'새우',pork:'돼지고기',peach:'복숭아',tomato:'토마토',sulfite:'아황산류',walnut:'호두',chicken:'닭고기',beef:'쇠고기',squid:'오징어',shellfish:'조개류',pine_nut:'잣'};
const list=value=>(value||[]).map(c=>allergens[c]||c).join(', ');
function allergy(key,event){const values=[...event.target.selectedOptions].map(o=>o.value);set('allergens.'+key,values.length?values:null)}
function ingredient(index,key,value){const next=JSON.parse(JSON.stringify(food.value));next.attributes.ingredients[index][key]=value===''?null:value;emit('update:modelValue',next)}
function other(value){set('attributes.other',value.split('\n').map(v=>v.trim()).filter(Boolean).slice(0,100))}
</script>
<template><div v-if="food" class="food-record-form" :class="{compact}"><p class="small muted">확인되지 않은 항목은 공란으로 남겨 주세요.</p><fieldset :disabled="readonly"><label>식품명<input :value="food.food_name" @input="set('food_name',$event.target.value)" aria-label="표준 식품명"></label><label>업체<input :value="food.company_name" @input="set('company_name',$event.target.value)" list="food-companies" placeholder="업체명 또는 공란" aria-label="업체"><datalist id="food-companies"><option v-for="c in companies" :key="c.id" :value="c.name"/></datalist></label><p v-if="food.raw_food_name" class="original-value">원문 식품명: {{food.raw_food_name}}</p><label>규격 원문<input :value="food.specification.original_text" @input="set('specification.original_text',$event.target.value)" placeholder="예: 100g × 10개 / 1kg"></label><slot/><details :open="!compact"><summary>규격 세부 정보·식품코드 <span v-if="compact">선택 입력</span></summary><p class="small muted">낱개 규격과 전체 규격을 구분합니다. 확인할 수 없는 값은 공란으로 남겨 주세요.</p><div class="two-col"><label v-for="(label,key) in specs" :key="key">{{label}}<input :value="food.specification[key]" @input="set('specification.'+key,$event.target.value)" :aria-label="label"></label></div><p v-if="food.specification.normalized_quantity" class="small muted">환산: {{food.specification.normalized_quantity}} {{food.specification.normalized_unit}}</p><label>공통식품코드<input :value="food.food_code" @input="set('food_code',$event.target.value)" aria-label="공통식품코드"></label></details><details :open="!!food.attributes.original_text"><summary>식품 속성·원재료</summary><div class="two-col"><label v-for="(label,key) in attrs" :key="key">{{label}}<input :value="food.attributes[key]" @input="set('attributes.'+key,$event.target.value)"></label></div><label>공통식품속성 원문<textarea :value="food.attributes.original_text" @input="set('attributes.original_text',$event.target.value)" rows="2"/></label><div v-for="(item,index) in food.attributes.ingredients" :key="index" class="ingredient-row"><label>원재료<input :value="item.name" @input="ingredient(index,'name',$event.target.value)"></label><label>함량 (%)<input :value="item.percentage" inputmode="decimal" @input="ingredient(index,'percentage',$event.target.value)"></label><label>원재료 원산지<input :value="item.origin_country" @input="ingredient(index,'origin_country',$event.target.value)"></label><small class="muted">근거: {{item.original_text}}</small></div><label>기타 속성·숙성·보관 정보<textarea :value="(food.attributes.other||[]).join('\n')" @input="other($event.target.value)" rows="2" placeholder="항목마다 한 줄씩 입력"/></label><label>친환경 구분<input :value="food.eco_classification" @input="set('eco_classification',$event.target.value)"></label><label>업체군<input :value="food.supplier_group" @input="set('supplier_group',$event.target.value)"></label></details><details><summary>알레르기 정보 · {{{unknown:'미확인',source_declared:'원문 표시 있음',reviewed:'표시사항 검토 완료'}[food.allergens.review_status]}}</summary><p class="small muted">공란은 미확인입니다. 식품명·원재료에서 찾은 후보는 함유 확정 정보가 아닙니다.</p><p v-if="food.allergens.candidates.length" class="notice small">확인할 후보: {{list(food.allergens.candidates)}}</p><label v-for="(label,key) in {contains:'원문 함유 표시',may_contain:'같은 시설·혼입 가능 표시',free_from_claims:'원문 불포함 주장'}" :key="key">{{label}}<span v-if="readonly">{{list(food.allergens[key])||'—'}}</span><select v-else multiple :value="food.allergens[key]||[]" @change="allergy(key,$event)"><option v-for="(name,code) in allergens" :value="code">{{name}}</option></select></label><label>알레르기 표시 원문·확인 근거<textarea :value="food.allergens.original_text" @input="set('allergens.original_text',$event.target.value)" rows="2"/></label><label>확인 상태<select :value="food.allergens.review_status" @change="set('allergens.review_status',$event.target.value)"><option value="unknown">미확인</option><option value="source_declared">원문 표시 있음</option><option value="reviewed">표시사항 검토 완료</option></select></label></details><details :open="!!food.prices.source_columns?.length"><summary>원본 자료의 가격 (참고)</summary><div v-if="food.prices.source_columns?.length" class="table-scroll"><table><thead><tr><th>원본 가격 열</th><th>금액</th><th>기준</th></tr></thead><tbody><tr v-for="(price,index) in food.prices.source_columns" :key="index"><td>{{price.label}}</td><td><span v-if="readonly">{{price.amount??price.original_text??'—'}}</span><input v-else :value="price.amount" @input="set('prices.source_columns.'+index+'.amount',$event.target.value)" inputmode="decimal"></td><td>{{{kg:'1kg',piece:'1개',package:'포장 규격 기준'}[price.basis]}}<small v-if="price.tax_included" class="cell-sub">부가세 포함</small></td></tr></tbody></table></div><p class="small muted">이곳은 자료에서 읽은 가격입니다. 수정해도 승인된 단가는 바뀌지 않습니다. 실제 단가는 승인된 단가 영역에서 확인하세요. 공란과 0원은 다릅니다.</p><div class="two-col"><label v-for="(label,key) in prices" :key="key">{{label}}<input :value="food.prices[key]" @input="set('prices.'+key,$event.target.value)" inputmode="decimal"></label></div></details><details v-if="compact" :open="!!food.note"><summary>비고·업체 확인 단서</summary><p class="small muted">비고의 이름은 업체로 확정하지 않습니다. 원문 확인 후 업체란에 입력해 주세요.</p><label>추가 메모<textarea :value="food.note" @input="set('note',$event.target.value)" rows="2"/></label></details><label v-else>비고<textarea :value="food.note" @input="set('note',$event.target.value)" rows="2"/></label></fieldset></div></template>
<style scoped>.food-record-form details{border-top:1px solid #e2e7eb;padding:12px 0}.food-record-form summary{cursor:pointer;font-weight:600;margin-bottom:10px}.food-record-form select[multiple]{min-height:110px}.food-record-form fieldset{margin:0;padding:0;border:0;min-width:0}.food-record-form label>span{display:block;padding:6px 0}.compact>p{margin:0 0 16px;font-size:11px}.compact .original-value{margin:0 0 16px;padding:9px 11px}.compact details{margin:0;border-top:1px solid #e2e9e4;padding:13px 0 2px}.compact summary{font-size:12px;margin-bottom:10px;line-height:1.6}.compact summary>span{font-weight:400;color:#91a096;font-size:10px;margin-left:8px}.compact details[open]{padding-bottom:12px}.compact details label{margin-top:12px}.compact details:not([open]) summary{margin-bottom:0}.compact .change-fields{margin:0 0 16px}.compact fieldset{display:flex;flex-direction:column;gap:0}.compact label{margin-bottom:14px}.ingredient-row{display:grid;grid-template-columns:minmax(0,2fr) minmax(0,1fr) minmax(0,1fr);gap:10px;padding:12px;background:#f7f9f7;margin:10px 0;border-radius:6px}.ingredient-row label,.ingredient-row input{min-width:0}.ingredient-row small{grid-column:1/-1}@media(max-width:600px){.ingredient-row{grid-template-columns:1fr}} </style>
