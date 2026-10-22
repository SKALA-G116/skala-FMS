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

    2026-10-22  김재현(Finn) v0.1.0   세션 복원·만료·로그아웃 경계와 접근 제어 검증

    2026-10-22  김재현(Finn) v0.1.0   자료·Agent·검수 승인·식품 DB 중심 흐름 및 알레르기 표기 정리

    상세 Git 이력: git log --follow -- frontend/src/App.vue
    공통 규칙: doc/file-header-policy.md
==============================================================================
-->
<script setup>
import {ref,onMounted,onUnmounted,provide,watch} from 'vue';import {useRoute,useRouter} from 'vue-router';import {auth,safeReturnPath} from './api/auth';import {LayoutDashboard,Files,ClipboardCheck,PackageSearch,ReceiptText,Activity,ArrowUpRight,LogOut,Leaf,ArrowRight} from 'lucide-vue-next';const {user,ready}=auth;const signingIn=ref(false),error=ref(''),login=ref({username:'admin',password:''});const router=useRouter(),route=useRoute();provide('user',user);const nav=[['/documents','자료 가져오기',Files],['/reviews','검수·승인',ClipboardCheck],['/products','식품 DB',PackageSearch],['/agent-logs','Agent 로그',Activity]];
function loginPath(){return {path:'/login',query:route.path==='/login'?route.query:{redirect:route.fullPath}}}
watch(user,value=>{if(!value&&ready.value&&route.path!=='/login')router.replace(loginPath())});
async function recheck(){if(document.hidden||!user.value)return;try{await auth.check()}catch{auth.clear();error.value='로그인 상태를 확인할 수 없습니다. 다시 로그인해 주세요.'}}
onMounted(()=>{window.addEventListener('focus',recheck);document.addEventListener('visibilitychange',recheck)});
onUnmounted(()=>{window.removeEventListener('focus',recheck);document.removeEventListener('visibilitychange',recheck)});
async function signIn(){if(signingIn.value)return;signingIn.value=true;error.value='';try{const target=safeReturnPath(route.query.redirect);await auth.signIn(login.value);login.value.password='';await router.replace(target)}catch(e){error.value=e.message}finally{signingIn.value=false}}
async function signOut(){error.value='';try{await auth.signOut();login.value.password='';await router.replace('/login')}catch(e){error.value='로그아웃을 완료하지 못했습니다. 다시 시도해 주세요.'}}
</script><template><div v-if="!ready" class="boot">식품장부를 준비하고 있습니다.</div><div v-else-if="!user" class="login-layout"><div class="login-art"><div class="brand"><Leaf/> 식품장부<span>FOOD LEDGER</span></div><div><div class="eyebrow">A CLEARER FOOD WORKFLOW</div><h1>자료는 Agent가 정리하고,<br>DB 반영은 사람이 결정합니다.</h1><p>게시글·이미지·파일을 가져오면 자동으로 분석합니다.<br>원문과 비교해 승인한 정보만 DB에 저장합니다.</p><div class="flow-pills"><span>자료 가져오기</span><ArrowRight/><span>Agent 처리</span><ArrowRight/><span>검수·DB 반영</span></div></div><small>식품 정보 관리 워크스페이스</small></div><div class="login-form"><div class="eyebrow">WELCOME BACK</div><h2>워크스페이스 로그인</h2><p class="muted">담당자 계정으로 업무를 시작하세요.</p><p v-if="route.query.reason==='unavailable'" class="error">서버에서 로그인 상태를 확인할 수 없습니다. 연결을 확인한 뒤 다시 로그인해 주세요.</p><form @submit.prevent="signIn"><label>아이디<input v-model="login.username" autocomplete="username" required></label><label>비밀번호<input v-model="login.password" type="password" autocomplete="current-password" required></label><p class="error" v-if="error">{{error}}</p><button class="primary wide" :disabled="signingIn">{{signingIn?'로그인 확인 중…':'로그인'}} <ArrowRight :size="16"/></button></form><div class="notice">로컬 예제 계정: admin<br>초기 비밀번호는 프로젝트 실행 안내를 확인하세요.</div></div></div><div v-else class="shell"><aside class="sidebar"><RouterLink to="/" class="brand"><div class="brand-mark"><Leaf :size="23"/></div><div>식품장부<small>FOOD LEDGER</small></div></RouterLink><div class="workspace"><span class="workspace-dot"></span> 내 워크스페이스</div><div class="nav-label">식품 정보 관리</div><nav><RouterLink v-for="[path,label,icon] in nav" :key="path" :to="path" :class="{selected:path==='/'?route.path==='/':(route.path.startsWith(path)||(path==='/reviews'&&route.path.startsWith('/analysis-runs/'))||(path==='/documents'&&(route.path.startsWith('/materials/')||route.path.startsWith('/collection')||route.path.startsWith('/jobs')))||(path==='/products'&&route.path==='/prices'))}"><component :is="icon" :size="19"/>{{label}}</RouterLink></nav><div class="sidebar-note"><div class="pulse"></div><strong>가져오기 → 검수 → 식품 DB</strong><p>도구 선택과 전처리는 Agent가 맡습니다.</p><RouterLink to="/reviews">검수함 열기 <ArrowUpRight :size="15"/></RouterLink></div><div class="user"><div class="avatar">{{user.display_name?.slice(0,1)}}</div><div><b>{{user.display_name}}</b><small>{{user.roles.join(' · ')}}</small></div><button @click="signOut" aria-label="로그아웃" class="icon-button"><LogOut :size="17"/></button></div></aside><main><header class="topbar"><span>워크스페이스 <span class="slash">/</span> {{nav.find(([p])=>p!=='/'&&route.path.startsWith(p))?.[1]||(route.path.startsWith('/analysis-runs/')?'검수·승인':route.path==='/collection'?'사이트 연결':route.path.startsWith('/jobs')?'처리 현황':route.path==='/prices'?'단가표':'식품 DB')}}</span><div class="row"><span class="small muted">Asia/Seoul</span><span class="top-avatar">{{user.display_name?.slice(0,1)}}</span></div></header><div class="page" :key="route.path"><RouterView/></div><footer>식품장부 · 모든 변경에는 근거가 남습니다.<span>검수 후 반영 · 변경 이력 보관</span></footer></main></div></template>
