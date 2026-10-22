<!--
==============================================================================
FMS_FILE_SPEC
Sources.vue - 사이트 연결·업데이트 수집
==============================================================================
설명:
    - 사이트 연결·업데이트 수집
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

    상세 Git 이력: git log --follow -- frontend/src/views/Sources.vue
    공통 규칙: doc/file-header-policy.md
==============================================================================
-->
<script setup>
import {ref,onMounted,inject,computed} from 'vue';import {useRouter} from 'vue-router';import {api,get} from '../api/client';import {Link,ShieldCheck,RefreshCw,Check,KeyRound} from 'lucide-vue-next';const user=inject('user'),router=useRouter(),isAdmin=computed(()=>user.value.roles.includes('admin'));const source=ref(null),tag=ref(''),connection=ref(null),form=ref({username:'',password:'',auto_login:true}),schedule=ref(false),interval=ref(30),busy=ref(false),error=ref(''),message=ref(''),limit=ref(15),autoAnalyze=ref(true);
async function load(){try{source.value=(await get('/sources')).items[0];const r=await api('/sources/'+source.value.id);source.value=r.data;tag.value=r.etag;schedule.value=!!source.value.schedule_enabled;interval.value=source.value.poll_interval_minutes||30;if(isAdmin.value){connection.value=await get('/sources/'+source.value.id+'/connection');form.value.username=connection.value.username||'';form.value.auto_login=connection.value.auto_login}}catch(e){error.value=e.message}}onMounted(load);
async function save(){busy.value=true;error.value='';try{connection.value=(await api('/sources/'+source.value.id+'/connection',{method:'POST',body:form.value})).data;form.value.password='';message.value='회원 정보를 암호화해 저장했습니다. 연결 확인을 실행해 주세요.'}catch(e){error.value=e.message}finally{busy.value=false}}
async function test(){busy.value=true;try{const r=await api('/sources/'+source.value.id+'/connection/test',{method:'POST',body:{}});router.push('/jobs/'+r.data.id)}catch(e){error.value=e.message}finally{busy.value=false}}
async function saveSchedule(){busy.value=true;try{const r=await api('/sources/'+source.value.id,{method:'PATCH',etag:tag.value,body:{enabled:true,schedule_enabled:schedule.value,poll_interval_minutes:Number(interval.value)}});tag.value=r.etag;message.value=schedule.value?'자동 수집을 켰습니다. 새 글과 최근 수집 글의 수정을 주기적으로 확인합니다.':'자동 수집을 껐습니다.'}catch(e){error.value=e.message}finally{busy.value=false}}
async function collect(){busy.value=true;try{const r=await api('/collection-runs',{method:'POST',body:{source_id:source.value.id,board_keys:['product_01','product_02','product_del'],max_posts_per_board:Number(limit.value),revisit_days:14,auto_analyze:true}});router.push('/jobs/'+r.data.id)}catch(e){error.value=e.message}finally{busy.value=false}}
</script><template><div class="page-heading"><div><div class="eyebrow">SOURCE CONNECTION</div><h1>사이트에서 자료 가져오기</h1><p class="muted">school062.com 회원 계정으로 연결하고, 새 공지와 수정된 자료를 이어서 가져옵니다.</p></div><RouterLink to="/documents" class="secondary">자료 가져오기로</RouterLink><a href="https://school062.com" target="_blank" rel="noopener" class="secondary">사이트 열기 ↗</a></div><p v-if="error" class="error" role="alert">{{error}}</p><p v-if="message" class="success" role="status">{{message}}</p><div class="two-col"><section v-if="isAdmin" class="panel manual-form"><div class="row"><KeyRound :size="20"/><h2>사이트 회원 정보</h2></div><p class="small muted">서비스 로그인과 별도로, 사이트에 이미 가입한 회원 계정을 입력하세요. 저장한 비밀번호는 다시 표시되지 않습니다.</p><div v-if="connection" class="row"><span class="badge" :class="connection.state==='connected'?'succeeded':'draft'">{{{connected:'연결 확인 완료',saved:'연결 확인 필요',login_failed:'로그인 확인 필요',not_configured:'계정 미등록'}[connection.state]||connection.state}}</span><span v-if="connection.last_checked_at" class="small muted">{{new Date(connection.last_checked_at).toLocaleString('ko-KR')}}</span></div><form @submit.prevent="save" class="manual-form nested-form"><label>회원 아이디<input v-model="form.username" autocomplete="off" required maxlength="100" aria-label="사이트 회원 아이디"></label><label>회원 비밀번호<input v-model="form.password" type="password" autocomplete="off" :placeholder="connection?.password_stored?'변경할 때만 입력':'사이트 비밀번호 입력'" :required="!connection?.password_stored" aria-label="사이트 회원 비밀번호"></label><label class="inline-label"><input type="checkbox" v-model="form.auto_login">자동 로그인 유지</label><div class="row"><button class="primary" :disabled="busy"><Check :size="15"/> 회원 정보 저장</button><button type="button" class="secondary" @click="test" :disabled="busy||!connection?.configured">연결 확인</button></div></form><div v-if="connection?.state==='login_failed'" class="warning">로그인 확인에 실패하여 자동 수집은 대기합니다. 회원 정보를 수정하고 연결 확인을 다시 실행하세요.</div><div class="notice"><ShieldCheck :size="15"/> 회원 정보와 사이트 세션은 서버에서 암호화해 보관합니다. 자동 로그인이 만료되면 저장한 계정으로 다시 연결합니다. 추가 인증이나 권한 제한이 있으면 작업을 멈추고 알려드립니다.</div></section><section class="panel manual-form"><div class="row"><RefreshCw :size="20"/><h2>업데이트 가져오기</h2></div><p class="small muted">공산품·농수축산물·단종제품 게시판을 확인합니다. 처음에는 선택한 범위만 가져오고, 이후에는 새 글과 최근 14일에 수집한 글의 변경을 확인합니다.</p><label>게시판당 한 번에 확인할 새 글 수<select v-model="limit"><option :value="5">5개 · 빠른 확인</option><option :value="15">15개</option><option :value="30">30개</option><option :value="50">50개</option></select></label><p class="notice">새 자료와 수정 자료는 Agent가 자동 분석합니다. 검수·승인 전에는 식품 DB를 변경하지 않습니다.</p><button class="primary" @click="collect" :disabled="busy||!source">지금 업데이트 가져오기 →</button><p v-if="source?.last_collected_at" class="small muted">마지막 수집 {{new Date(source.last_collected_at).toLocaleString('ko-KR')}}</p><div v-if="source?.last_collection_counts" class="collection-counts"><span>신규 <b>{{source.last_collection_counts.new}}</b></span><span>수정 <b>{{source.last_collection_counts.updated}}</b></span><span>변경 없음 <b>{{source.last_collection_counts.unchanged}}</b></span></div><template v-if="isAdmin"><hr><h3>자동 수집</h3><label class="inline-label"><input type="checkbox" v-model="schedule">자동 수집 사용</label><label>확인 간격<select v-model="interval"><option :value="10">10분</option><option :value="30">30분</option><option :value="60">1시간</option><option :value="180">3시간</option></select></label><button class="secondary" @click="saveSchedule" :disabled="busy">수집 설정 저장</button><small class="muted">이 컴퓨터의 서비스와 작업자가 실행 중일 때 동작합니다.</small></template></section></div></template>
