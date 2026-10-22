<!--
==============================================================================
FMS_FILE_SPEC
ApprovedPrices.vue - ApprovedPrices UI 컴포넌트
==============================================================================
설명:
    - ApprovedPrices UI 컴포넌트
입력·출력 명세:
    - 입력: props·표준 DTO·상위 화면 상태
    - 출력: 표시 결과와 emit 이벤트
실행 가정:
    - 업무 반영은 권한 있는 API를 통해 수행하고 컴포넌트가 직접 DB에 접근하지 않음
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

    상세 Git 이력: git log --follow -- frontend/src/components/ApprovedPrices.vue
    공통 규칙: doc/file-header-policy.md
==============================================================================
-->
<script setup>
defineProps({prices:{type:Array,default:()=>[]}})
defineEmits(['evidence'])
</script>
<template><section class="approved-prices" aria-label="승인된 단가"><h3>승인된 단가</h3><p class="small muted">승인·반영된 금액입니다. 아래 원본 자료의 참고 가격과 구분해 확인하세요.</p><p v-if="!prices.length" class="muted">등록된 단가가 없습니다.</p><article v-for="price in prices" :key="price.id"><div class="row between"><b>{{Number(price.value.amount).toLocaleString()}}원 / {{price.value.quantity}}{{price.value.unit}}</b><span>{{price.effective_state==='scheduled'?'적용 예정':'현재 적용'}}</span></div><p class="small">{{price.supplier.name}} · {{price.period.effective_from}}부터<span v-if="price.period.effective_to"> ~ {{price.period.effective_to}} 전까지</span></p><button class="link small" @click="$emit('evidence',price.evidence_ids)">변경 근거 보기 ↗</button></article></section></template>
<style scoped>.approved-prices{padding:16px;margin-bottom:20px;background:#f1f7f3;border:1px solid #d7e6dc;border-radius:10px}.approved-prices h3{margin:0 0 8px}.approved-prices article{padding:12px 0;border-top:1px solid #d7e6dc}.approved-prices article span{font-size:11px}.approved-prices article p{margin:8px 0}</style>
