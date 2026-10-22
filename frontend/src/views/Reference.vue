<!--
==============================================================================
FMS_FILE_SPEC
Reference.vue - 원본 자료·근거·표 조회
==============================================================================
설명:
    - 원본 자료·근거·표 조회
입력·출력 명세:
    - 입력: 라우트·사용자 입력·API 조회 DTO
    - 출력: 사용자 여정에 맞는 화면과 명시적 API 요청
실행 가정:
    - 미확인 값과 저장 전 수정·서버 권한/검증 상태를 구분
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

    2026-10-22  김재현(Finn) v0.1.0   자료·Agent·검수 승인·식품 DB 중심 흐름 및 알레르기 표기 정리

    상세 Git 이력: git log --follow -- frontend/src/views/Reference.vue
    공통 규칙: doc/file-header-policy.md
==============================================================================
-->
<script setup>
import {ref,onMounted} from 'vue';import {useRoute} from 'vue-router';import {get} from '../api/client';import EvidenceViewer from '../components/EvidenceViewer.vue';import FoodRecordForm from '../components/FoodRecordForm.vue';const route=useRoute(),data=ref(null),rev=ref(null),error=ref('');const evidence=route.path.startsWith('/evidence');onMounted(async()=>{try{data.value=await get((evidence?'/evidence/':'/audit-events/')+route.params.id);if(evidence)rev.value=await get('/document-revisions/'+data.value.document_revision_id)}catch(e){error.value=e.message}});async function original(id){const a=await get('/assets/'+id+'/access');window.open(a.url,'_blank','noopener')}
const labels={name:'식품명',spec_original:'규격',status:'상태',amount:'금액',quantity:'기준 수량',unit:'단위',currency:'통화',effective_from:'적용 시작',effective_to:'적용 종료',sales_unit:'판매 단위',supplier_code:'업체 품목코드'};function summary(value){if(!value)return [];const flat={...value,...value.value,...value.period};return Object.entries(labels).filter(([key])=>flat[key]!=null).map(([key,label])=>[label,flat[key]])}
</script><template><div class="page-heading"><div><div class="eyebrow">TRACEABLE RECORD</div><h1>{{evidence?'원문 근거':'변경 이력 상세'}}</h1><p class="muted">정보가 어디에서 왔는지, 무엇이 바뀌었는지 확인하세요.</p></div><button class="secondary" @click="$router.back()">뒤로</button></div><p v-if="error" class="error">{{error}}</p><template v-if="data"><template v-if="evidence"><EvidenceViewer :ids="[data.id]"/><section v-if="rev" class="panel document-detail"><h2>{{rev.title}}</h2><p class="small muted">원문 v{{rev.revision_number}} · {{rev.content_sha256}}</p><pre class="source-text">{{rev.body_text}}</pre><button v-for="a in rev.assets" class="secondary" @click="original(a.id)">{{a.filename}} 원본 다운로드 ↓</button><div v-if="data.locator.bbox" class="notice">원본 이미지 좌표 (왼쪽 위 원점): {{data.locator.bbox}} · {{data.locator.image_width}} × {{data.locator.image_height}}</div></section></template><template v-else><section class="panel document-detail"><div class="row between"><h2>{{data.kind==='edit_food_profile'?'식품 정보 수정':data.kind==='set_food_profile'?'식품 정보 반영':'식품 변경 기록'}}</h2><span class="small muted">{{new Date(data.recorded_at).toLocaleString('ko-KR')}}</span></div><p v-if="data.reason" class="notice">수정 사유: {{data.reason}}</p><div class="two-col"><div><h3>변경 전</h3><FoodRecordForm v-if="data.before?.schema_version" :model-value="data.before" readonly/><dl v-else-if="data.before"><template v-for="[label,value] in summary(data.before)" :key="label"><dt>{{label}}</dt><dd>{{value}}</dd></template></dl><p v-else>신규 등록</p></div><div><h3>변경 후</h3><FoodRecordForm v-if="data.after?.schema_version" :model-value="data.after" readonly/><dl v-else><template v-for="[label,value] in summary(data.after)" :key="label"><dt>{{label}}</dt><dd>{{value}}</dd></template></dl></div></div><RouterLink v-if="data.proposal_id" :to="'/reviews/'+data.proposal_id">승인·검토 기록 보기 ↗</RouterLink></section><EvidenceViewer :ids="data.evidence_ids"/></template></template></template>
