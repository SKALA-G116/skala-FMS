<!--
==============================================================================
FMS_FILE_SPEC
Dashboard.vue - 업무 집계와 주요 화면 진입
==============================================================================
설명:
    - 업무 집계와 주요 화면 진입
입력·출력 명세:
    - 입력: 라우트·사용자 입력·API 조회 DTO
    - 출력: 사용자 여정에 맞는 화면과 명시적 API 요청
실행 가정:
    - 미확인 값과 저장 전 수정·서버 권한/검증 상태를 구분
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

    상세 Git 이력: git log --follow -- frontend/src/views/Dashboard.vue
    공통 규칙: doc/file-header-policy.md
==============================================================================
-->
<script setup>
import {ref,onMounted,computed} from 'vue';import {get} from '../api/client';import StatusBadge from '../components/StatusBadge.vue';import {ArrowUpRight,ArrowRight,ClipboardCheck,Clock3,TriangleAlert,CalendarDays,FileText,Package,Upload,ReceiptText,Activity,Plus} from 'lucide-vue-next';
const stats=ref({}),proposals=ref([]),docs=ref([]),jobs=ref([]),error=ref('');onMounted(async()=>{try{[stats.value,{items:proposals.value},{items:docs.value},{items:jobs.value}]=await Promise.all([get('/dashboard'),get('/proposals?limit=12'),get('/documents?limit=5'),get('/jobs?limit=5')])}catch(e){error.value=e.message}});const inbox=computed(()=>proposals.value.filter(p=>['ready','draft','on_hold','conflict'].includes(p.summary.status)).slice(0,4));const cards=[['관리 중인 식품','food_count',Package,'/products'],['보관된 자료','document_count',FileText,'/documents'],['반영 준비','review_ready_count',ClipboardCheck,'/reviews'],['확인 필요한 작업','failed_job_count',TriangleAlert,'/jobs']];const jobTitle={collect:'사이트 자료 수집',analyze:'자료 분석',apply:'식품 정보 반영'};
</script><template><div class="page-heading"><div><div class="section-kicker">워크스페이스</div><h1>대시보드</h1><p class="muted">새 자료를 정리하고, 확인한 식품 정보만 반영하세요.</p></div><RouterLink to="/documents" class="primary"><Plus :size="17"/> 자료 가져오기</RouterLink></div><p v-if="error" class="error">{{error}}</p><div class="dashboard-metrics"><RouterLink v-for="[label,key,icon,path] in cards" :key="key" :to="path" class="metric-card"><div class="metric-icon"><component :is="icon" :size="20"/></div><span>{{label}}</span><strong>{{stats[key]??'—'}}<small>건</small></strong><ArrowUpRight class="metric-arrow" :size="17"/></RouterLink></div><div class="dashboard-primary-grid"><section class="panel"><div class="panel-heading"><div><h2>다음으로 할 일</h2><p class="muted small">자료에서 식품 정보까지, 세 단계로 관리합니다.</p></div></div><div class="action-path"><RouterLink v-for="[n,title,description,path,icon] in [['01','자료 가져오기','파일을 등록하거나 사이트에서 수집하세요.','/documents',Upload],['02','추출 결과 확인','같은 양식의 표에서 원문과 비교하세요.','/reviews',ClipboardCheck],['03','식품·단가 관리','반영한 정보를 조회하고 이력을 확인하세요.','/products',Package]]" :key="n" :to="path"><span class="action-path-number">{{n}}</span><div class="grow"><b>{{title}}</b><p>{{description}}</p></div><ArrowRight :size="18"/></RouterLink></div></section><section class="panel"><div class="panel-heading"><h2>최근 자료</h2><RouterLink to="/documents" class="text-link">자료함 <ArrowRight :size="15"/></RouterLink></div><RouterLink v-for="d in docs" :key="d.id" :to="'/documents/'+d.id" class="dashboard-material"><div class="file-type-icon"><FileText :size="18"/></div><div class="grow"><b>{{d.title}}</b><span>{{new Date(d.collected_at).toLocaleDateString('ko-KR')}}</span></div><StatusBadge :value="d.analysis_status"/></RouterLink><div v-if="!docs.length" class="directory-empty"><FileText :size="28"/><h3>첫 자료를 가져와 보세요.</h3><p>텍스트·표·이미지를 식품 정보로 정리합니다.</p><RouterLink to="/documents" class="secondary">자료 가져오기</RouterLink></div></section></div><div class="dashboard-secondary-grid"><section class="panel"><div class="panel-heading"><h2>검토 중인 변경안</h2><RouterLink to="/reviews" class="text-link">검수함 <ArrowRight :size="15"/></RouterLink></div><RouterLink v-for="p in inbox" :key="p.summary.id" :to="'/reviews/'+p.summary.id" class="dashboard-review"><div class="grow"><b>{{p.summary.title}}</b><span>{{p.changes.length}}개 변경 · {{new Date(p.summary.created_at).toLocaleDateString('ko-KR')}}</span></div><StatusBadge :value="p.summary.status"/><ArrowUpRight :size="16"/></RouterLink><p v-if="!inbox.length" class="empty">검토 중인 변경안이 없습니다.</p></section><section class="panel"><div class="panel-heading"><h2>최근 작업</h2><RouterLink to="/jobs" class="text-link">작업 기록 <ArrowRight :size="15"/></RouterLink></div><RouterLink v-for="j in jobs" :key="j.id" :to="'/jobs/'+j.id" class="dashboard-job"><Activity :size="17" class="muted"/><div class="grow"><b>{{jobTitle[j.type]||j.type}}</b><span>{{j.stage}}</span></div><StatusBadge :value="j.status"/></RouterLink><p v-if="!jobs.length" class="empty">아직 실행한 작업이 없습니다.</p></section></div><p class="workspace-footnote">원문과 변경 이력은 함께 보관됩니다. 초기 예제 식품과 실제 자료의 정보는 원문 근거를 확인해 구별해 주세요.</p></template>
