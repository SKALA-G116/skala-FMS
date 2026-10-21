<!--
==============================================================================
FMS_FILE_SPEC
FoodRecordTable.vue - 표준 식품 DTO의 공통 열 표시
==============================================================================
설명:
    - 표준 식품 DTO의 공통 열 표시
입력·출력 명세:
    - 입력: props·표준 DTO·상위 화면 상태
    - 출력: 표시 결과와 emit 이벤트
실행 가정:
    - 업무 반영은 권한 있는 API를 통해 수행하고 컴포넌트가 직접 DB에 접근하지 않음
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

    2026-10-21  미지정      v0.1.0   업체 표 직접 정규화·중복 통합·원문 이력 보존

    상세 Git 이력: git log --follow -- frontend/src/components/FoodRecordTable.vue
    공통 규칙: doc/file-header-policy.md
==============================================================================
-->
<script setup>
defineProps({rows:{type:Array,default:()=>[]},selected:String});defineEmits(['select']);const food=row=>row.review?.fields?.food_record||row.food_record;const allergy={unknown:'미확인',source_declared:'원문 표시 있음',reviewed:'표시사항 검토 완료'};
</script><template><div class="table-scroll standardized-food-table"><table><thead><tr><th>식품명</th><th>업체</th><th>공통식품코드</th><th>맛·종류</th><th>낱개 규격</th><th>포장 수량</th><th>전체 규격</th><th>판매 단위</th><th>원본 단가</th><th>산지·원산지</th><th>등급</th><th>알레르기 확인</th><th>검토</th></tr></thead><tbody><tr v-for="row in rows" :key="row.id" :class="['clickable',{chosen:selected===row.id}]" @click="$emit('select',row.id)"><template v-if="food(row)"><td><button class="link" @click.stop="$emit('select',row.id)">{{food(row).food_name}}</button></td><td>{{food(row).company_name}}</td><td>{{food(row).food_code}}</td><td>{{food(row).attributes.flavor}}</td><td>{{food(row).specification.piece_quantity}}{{food(row).specification.piece_unit}}</td><td>{{food(row).specification.pack_count}}</td><td>{{food(row).specification.quantity}}{{food(row).specification.unit}}</td><td>{{food(row).specification.sales_unit}}</td><td>{{food(row).prices.source_applied!=null?Number(food(row).prices.source_applied).toLocaleString()+'원':''}}</td><td>{{food(row).attributes.origin_region||food(row).attributes.origin_country}}</td><td>{{food(row).attributes.quality_grade}}</td><td>{{allergy[food(row).allergens.review_status]}}</td><td>{{{confirmed:'확인',skipped:'제외',pending:'대기'}[row.review?.status]||'대기'}}</td></template></tr></tbody></table></div></template>
<style scoped>.standardized-food-table{max-height:300px;overflow:auto}.standardized-food-table th{position:sticky;top:0;background:#f5f8f6;z-index:1}.standardized-food-table td{white-space:nowrap}.chosen{background:#edf6ef}</style>
