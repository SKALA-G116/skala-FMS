<!--
==============================================================================
FMS_FILE_SPEC
EvidenceViewer.vue - 변경 필드와 원문 근거 조회
==============================================================================
설명:
    - 변경 필드와 원문 근거 조회
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

    상세 Git 이력: git log --follow -- frontend/src/components/EvidenceViewer.vue
    공통 규칙: doc/file-header-policy.md
==============================================================================
-->
<script setup>
import {ref,watch} from 'vue';import ImageEvidence from './ImageEvidence.vue';import {get} from '../api/client';const props=defineProps({ids:{type:Array,default:()=>[]}});const evidence=ref([]);const error=ref('');watch(()=>props.ids,async(ids)=>{try{evidence.value=await Promise.all(ids.map(id=>get('/evidence/'+id)))}catch(e){error.value=e.message}},{immediate:true});async function download(asset){const a=await get('/assets/'+asset+'/access');window.open(a.url,'_blank','noopener')}
</script><template><section class="evidence-box"><div class="eyebrow">SOURCE EVIDENCE</div><h3>판단의 근거</h3><p v-if="!ids.length" class="muted">연결된 근거가 없습니다.</p><p v-if="error" class="error">{{error}}</p><article v-for="ev in evidence" :key="ev.id"><blockquote>{{ev.quote}}</blockquote><div class="small muted">{{ev.locator.kind==='spreadsheet'?`${ev.locator.sheet_name} · ${ev.locator.cell_range}`:ev.locator.kind==='image'?`이미지 ${ev.locator.page_number}페이지 · OCR ${Math.round((ev.ocr_confidence||0)*100)}%`:ev.locator.block_id}}</div><ImageEvidence v-if="['image','pdf'].includes(ev.locator.kind)" :locator="ev.locator"/><div class="row small"><RouterLink :to="'/evidence/'+ev.id">근거 상세 ↗</RouterLink><a v-if="ev.source_url" :href="ev.source_url" target="_blank" rel="noopener noreferrer">게시글 원문 ↗</a><button v-if="ev.locator.asset_id" class="link" @click="download(ev.locator.asset_id)">원본 파일 ↓</button></div></article></section></template>
