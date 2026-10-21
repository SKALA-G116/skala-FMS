<!--
==============================================================================
FMS_FILE_SPEC
App.vue - Vue 애플리케이션 App
==============================================================================
설명:
    - Vue 애플리케이션 App
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

    상세 Git 이력: git log --follow -- frontend/src/App.vue
    공통 규칙: doc/file-header-policy.md
==============================================================================
-->
<script setup>
import {ref,onMounted,provide} from 'vue';import {useRoute,useRouter} from 'vue-router';import {get,api,refreshCsrf} from './api/client';import {LayoutDashboard,Files,ClipboardCheck,PackageSearch,ReceiptText,Activity,ArrowUpRight,LogOut,Leaf,ArrowRight} from 'lucide-vue-next';const user=ref(null),ready=ref(false),error=ref(''),login=ref({username:'admin',password:''});const router=useRouter(),route=useRoute();provide('user',user);const nav=[['/','대시보드',LayoutDashboard],['/documents','자료함',Files],['/reviews','검수함',ClipboardCheck],['/products','식품 목록',PackageSearch],['/prices','단가표',ReceiptText],['/collection','사이트 연결·수집',Activity],['/jobs','작업 기록',Activity]];
onMounted(async()=>{try{await refreshCsrf();user.value=await get('/auth/me')}catch{}ready.value=true});async function signIn(){error.value='';try{user.value=(await api('/auth/session',{method:'POST',body:login.value})).data.user;await router.replace('/')}catch(e){error.value=e.message}}async function signOut(){await api('/auth/session',{method:'DELETE'});user.value=null;login.value.password='';await refreshCsrf()}
</script><template><div v-if="!ready" class="boot">식품장부를 준비하고 있습니다.</div><div v-else-if="!user" class="login-layout"><div class="login-art"><div class="brand"><Leaf/> 식품장부<span>FOOD LEDGER</span></div><div><div class="eyebrow">A CLEARER FOOD WORKFLOW</div><h1>흩어진 식품 정보,<br>하나의 믿을 수 있는 장부로.</h1><p>공지에서 변경을 찾고, 근거를 검토하고,<br>확인된 정보만 장부에 남깁니다.</p><div class="flow-pills"><span>자료 수집</span><ArrowRight/><span>사람의 검토</span><ArrowRight/><span>이력 보관</span></div></div><small>식품 정보 관리 워크스페이스</small></div><div class="login-form"><div class="eyebrow">WELCOME BACK</div><h2>워크스페이스 로그인</h2><p class="muted">담당자 계정으로 업무를 시작하세요.</p><form @submit.prevent="signIn"><label>아이디<input v-model="login.username" autocomplete="username" required></label><label>비밀번호<input v-model="login.password" type="password" autocomplete="current-password" required></label><p class="error" v-if="error">{{error}}</p><button class="primary wide">로그인 <ArrowRight :size="16"/></button></form><div class="notice">로컬 예제 계정: admin<br>초기 비밀번호는 프로젝트 실행 안내를 확인하세요.</div></div></div><div v-else class="shell"><aside class="sidebar"><RouterLink to="/" class="brand"><div class="brand-mark"><Leaf :size="23"/></div><div>식품장부<small>FOOD LEDGER</small></div></RouterLink><div class="workspace"><span class="workspace-dot"></span> 내 워크스페이스</div><div class="nav-label">식품 정보 관리</div><nav><RouterLink v-for="[path,label,icon] in nav" :key="path" :to="path" :class="{selected:path==='/'?route.path==='/':(route.path.startsWith(path)||(path==='/reviews'&&route.path.startsWith('/analysis-runs/'))||(path==='/documents'&&route.path.startsWith('/materials/')))}"><component :is="icon" :size="19"/>{{label}}</RouterLink></nav><div class="sidebar-note"><div class="pulse"></div><strong>원문에서 식품 정보까지</strong><p>자료를 모으고, 확인한 정보만 남깁니다.</p><RouterLink to="/reviews">검수함 열기 <ArrowUpRight :size="15"/></RouterLink></div><div class="user"><div class="avatar">{{user.display_name?.slice(0,1)}}</div><div><b>{{user.display_name}}</b><small>{{user.roles.join(' · ')}}</small></div><button @click="signOut" aria-label="로그아웃" class="icon-button"><LogOut :size="17"/></button></div></aside><main><header class="topbar"><span>워크스페이스 <span class="slash">/</span> {{nav.find(([p])=>p!=='/'&&route.path.startsWith(p))?.[1]||(route.path.startsWith('/analysis-runs/')?'추출 결과 검토':'대시보드')}}</span><div class="row"><span class="small muted">Asia/Seoul</span><span class="top-avatar">{{user.display_name?.slice(0,1)}}</span></div></header><div class="page" :key="route.path"><RouterView/></div><footer>식품장부 · 모든 변경에는 근거가 남습니다.<span>검수 후 반영 · 변경 이력 보관</span></footer></main></div></template>
