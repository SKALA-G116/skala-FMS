<!--
==============================================================================
FMS_FILE_SPEC
Jobs.vue - 비동기 작업 상태·취소·재시도
==============================================================================
설명:
    - 비동기 작업 상태·취소·재시도
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

    2026-10-21  미지정      v0.1.0   작업 목록 갱신·상세 경로 전환 시 조회 재개

    2026-10-21  미지정      v0.1.0   원본 속성 누락 복구·재정리 API·검토 동선 개선

    2026-10-21  김재현(Finn) v0.1.0   Agent 도구 선택 기반 리빌드·업무 경계 및 검증

    상세 Git 이력: git log --follow -- frontend/src/views/Jobs.vue
    공통 규칙: doc/file-header-policy.md
==============================================================================
-->
<script setup>
import {ref,watch,onUnmounted,inject,computed} from 'vue';import {useRoute,useRouter} from 'vue-router';import {get,api} from '../api/client';import {useJob} from '../composables/useJob';import StatusBadge from '../components/StatusBadge.vue';import CursorPager from '../components/CursorPager.vue';import {Activity,ArrowRight} from 'lucide-vue-next';const route=useRoute(),router=useRouter(),user=inject('user');const data=ref({items:[]}),error=ref(''),{job,start,stop}=useJob();const canOperate=computed(()=>user.value.roles.some(x=>['admin','operator'].includes(x)));let listTimer,disposed=false,currentCursor='';
async function load(cursor=''){
 currentCursor=cursor;clearTimeout(listTimer);
 try{const result=await get('/jobs'+(cursor?'?cursor='+cursor:''));if(!disposed)data.value=result}catch(e){if(!disposed)error.value=e.message}
 finally{if(!disposed&&!route.params.id)listTimer=setTimeout(()=>{if(document.hidden)listTimer=setTimeout(()=>load(currentCursor),5000);else load(currentCursor)},5000)}
}
async function action(a){try{const {data:j}=await api('/jobs/'+job.value.id+'/'+a,{method:'POST',body:{}});if(a==='retry'){report.value=null;router.push('/jobs/'+j.id)}else start(job.value.id)}catch(e){error.value=e.message}}const relatedDocument=ref(null),report=ref(null);async function loadReport(id){const jobId=route.params.id;try{const next=await get('/analysis-runs/'+id+'/report');if(route.params.id===jobId)report.value=next}catch(e){if(route.params.id===jobId)error.value='추출 결과를 불러오지 못했습니다. '+e.message}}async function download(){try{const a=await get('/assets/'+report.value.export_asset_id+'/access');window.open(a.url,'_blank','noopener')}catch(e){error.value=e.message}}const progressPercent=computed(()=>{const j=job.value;if(!j)return 0;if(j.status==='succeeded')return 100;if(!j.total_count)return 0;return Math.max(0,Math.min(j.status==='running'?99:100,Math.round(100*j.processed_count/j.total_count)))});const toolLabels={normalize_table:'표 정보 정리',extract_text:'텍스트 의미 추출',extract_image_regions:'상품 영역별 이미지 추출',request_review:'원문 확인 요청'};const eventLabels={food_profile:'식품 기준정보',price:'단가',temporarily_unavailable:'일시중단',supply_ended:'공급 종료',discontinued:'단종',available:'공급 가능',substitution:'대체품',new_product:'신제품'};const types={analyze:'문서 분석',collect:'사이트 자료 수집',apply:'장부 반영'};
watch(()=>route.params.id,id=>{
 clearTimeout(listTimer);stop();job.value=null;report.value=null;relatedDocument.value=null;error.value='';
 if(id)start(id,async j=>{if(j.analysis_run_id){try{await loadReport(j.analysis_run_id);const r=await get('/analysis-runs/'+j.analysis_run_id);const rev=await get('/document-revisions/'+r.document_revision_id);if(route.params.id===id)relatedDocument.value=rev.document_id}catch{}}});
 else load();
},{immediate:true});
onUnmounted(()=>{disposed=true;clearTimeout(listTimer)});
</script><template><div class="page-heading"><div><div class="eyebrow">ACTIVITY MONITOR</div><h1>작업 현황</h1><p class="muted">수집부터 장부 반영까지, 처리 상태를 확인하세요.</p></div><RouterLink v-if="route.params.id" to="/jobs" class="secondary">전체 작업</RouterLink></div><p v-if="error" class="error">{{error}}</p><section v-if="job" class="panel job-detail"><div class="job-visual"><Activity :size="36"/></div><StatusBadge :value="job.status"/><h2>{{types[job.type]}}</h2><p class="muted">{{job.stage}}</p><div class="progress" role="progressbar" aria-label="현재 단계 진행률" :aria-valuenow="job.total_count?progressPercent:undefined" aria-valuemin="0" aria-valuemax="100"><span :style="{width:progressPercent+'%'}"></span></div><p class="small muted">시작 {{job.started_at?new Date(job.started_at).toLocaleString('ko-KR'):'대기 중'}} · 처리 진행 {{job.processed_count}} / {{job.total_count??'—'}}</p><div v-for="i in job.issues" class="warning"><b>{{i.code}}</b><p>{{i.message}}</p></div><div v-if="job.result?.counts" class="collection-counts center"><span>신규 <b>{{job.result.counts.new}}</b></span><span>수정 <b>{{job.result.counts.updated}}</b></span><span>변경 없음 <b>{{job.result.counts.unchanged}}</b></span></div><div v-if="job.result?.connected" class="success">사이트 회원 계정으로 연결되었습니다.</div><div class="row wrap center job-actions">
<RouterLink v-if="report" :to="'/analysis-runs/'+report.analysis_run_id+'/review'" class="primary">식품 정보 검토 <ArrowRight :size="16"/></RouterLink>
<RouterLink v-else-if="job.result?.proposal_ids?.length" to="/reviews" class="primary">검수함 열기 →</RouterLink>
<RouterLink v-if="relatedDocument" :to="'/documents/'+relatedDocument" class="secondary">원본 자료 보기</RouterLink>
<button v-if="report?.export_asset_id" class="secondary" @click="download">검토용 Excel 다운로드</button>
<RouterLink v-if="job.type==='collect'" to="/documents" class="primary">수집 자료 확인</RouterLink>
<RouterLink v-if="job.type==='collect'" to="/collection" class="secondary">수집 설정</RouterLink>
<RouterLink v-if="job.type==='apply'&&job.status==='succeeded'" to="/products" class="primary">반영된 식품 정보 확인 →</RouterLink>
<button v-for="a in canOperate?job.allowed_actions:[]" :key="a" class="secondary" @click="action(a)">{{a==='retry'?'다시 시도':'작업 취소'}}</button>
</div><div v-if="job.result?.analysis_job_ids?.length" class="notice">새 자료 {{job.result.analysis_job_ids.length}}건의 분석 작업을 등록했습니다. <RouterLink to="/jobs">분석 진행 보기 →</RouterLink></div><section v-if="report" class="job-result">
<div class="result-heading"><div><span class="eyebrow">EXTRACTION RESULT</span><h2>추출 결과</h2><p class="muted">{{report.model_calls?.length?'AI 해석과 표 읽기로 정리했습니다.':'표의 열을 읽어 식품 정보를 정리했습니다. 추가 AI 호출은 없습니다.'}}</p></div><strong>{{report.events.length}}<small>개 품목</small></strong></div>
<section v-if="report.plan.routes?.length" class="agent-decisions"><h3>Agent가 선택한 작업</h3><ol><li v-for="step in report.plan.routes" :key="step.source_id"><b>{{toolLabels[step.tool]}}</b><p>{{step.reason}}</p></li></ol></section><p v-for="(warning,i) in report.warnings" :key="i" class="warning">{{warning}}</p><p class="notice">원문과 비교하여 수정한 뒤, 확인한 정보만 DB에 반영하세요.</p>
<details><summary>품목 미리보기 · 처음 {{Math.min(5,report.events.length)}}개 / 전체 {{report.events.length}}개</summary><div class="table-scroll"><table><thead><tr><th>식품명</th><th>업체</th><th>규격</th><th>작업</th></tr></thead><tbody><tr v-for="e in report.events.slice(0,5)" :key="e.id"><td>{{e.product_name||'식별 필요'}}</td><td>{{e.food_record?.company_name||'—'}}</td><td>{{e.spec||'—'}}</td><td>{{eventLabels[e.kind]}}</td></tr></tbody></table></div></details>
<p v-if="!report.events.length" class="notice">추출된 식품 정보가 없습니다. 원본 자료와 처리 기록을 확인해 주세요.</p>
<details><summary>처리 기록</summary><p class="small muted">실제 AI 호출 {{report.model_calls?.length||0}}회 · 원문 {{report.coverage.processed_segments}} / {{report.coverage.source_segments}}개 구간 처리</p><p>{{report.plan.summary}}</p><pre>{{JSON.stringify({plan:report.plan,calls:report.model_calls,coverage:report.coverage,performance:report.performance},null,2)}}</pre></details>
</section><details v-if="job.performance" class="job-runtime"><summary>처리 내역</summary><p>완료한 구간 {{job.processed_count}} / {{job.total_count||'—'}} · AI 호출 {{job.performance.model_calls}}회 · AI 처리 누적 {{Math.round(job.performance.model_seconds)}}초</p><p class="small muted">대용량 자료는 완료한 구간을 저장하고 이어서 처리합니다.</p></details><small class="muted">작업 ID {{job.id}}</small></section><section v-else-if="!route.params.id" class="panel"><div class="table-scroll"><table><thead><tr><th>작업</th><th>상태</th><th>단계</th><th>시작일</th><th></th></tr></thead><tbody><tr class="clickable" v-for="j in data.items" @click="router.push('/jobs/'+j.id)"><td><b>{{types[j.type]}}</b><small class="cell-sub">{{j.id.slice(0,8)}}</small></td><td><StatusBadge :value="j.status"/></td><td>{{j.stage}}</td><td class="muted">{{new Date(j.created_at).toLocaleString('ko-KR')}}</td><td><ArrowRight :size="16"/></td></tr></tbody></table></div><p v-if="!data.items.length" class="empty">등록된 작업이 없습니다.</p><CursorPager :next="data.next_cursor" @next="load"/></section><div v-else class="empty">작업 정보를 가져오는 중입니다.</div></template>

<style scoped>
.job-detail{max-width:980px;padding:32px}.job-actions{padding:20px 0;border-top:1px solid var(--line);border-bottom:1px solid var(--line)}.job-result{text-align:left;margin-top:28px;padding:24px;background:#f8faf8;border:1px solid var(--line);border-radius:10px}.result-heading{display:flex;gap:20px;justify-content:space-between;align-items:center}.result-heading h2{margin:8px 0}.result-heading strong{font-size:32px;white-space:nowrap}.result-heading strong small{display:block;font-size:12px;color:#64736c;font-weight:400}.agent-decisions ol{padding-left:20px}.agent-decisions li{padding:7px 0}.agent-decisions li p{margin:5px 0;color:#68786e}.job-result details{margin-top:18px}.job-result summary{cursor:pointer;font-weight:600}.job-result pre{max-height:300px;overflow:auto;font-size:11px}.job-result .table-scroll{margin-top:12px}@media(max-width:700px){.job-detail{padding:24px 16px}.job-result{padding:16px}.job-actions>*{justify-content:center;flex:1 1 100%}.result-heading{align-items:flex-start}.result-heading strong{font-size:26px}}
</style>
