<!--
==============================================================================
FMS_FILE_SPEC
Reviews.vue - 검토할 변경안 목록
==============================================================================
설명:
    - 검토할 변경안 목록
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

    2026-10-21  미지정      v0.1.0   검수함을 내부 변경 묶음에서 자료별 분석 결과로 전환

    2026-10-22  김재현(Finn) v0.1.0   자료·Agent·검수 승인·식품 DB 중심 흐름 및 알레르기 표기 정리

    상세 Git 이력: git log --follow -- frontend/src/views/Reviews.vue
    공통 규칙: doc/file-header-policy.md
==============================================================================
-->
<script setup>
import {ref,onMounted,watch} from 'vue';
import {useRoute,useRouter} from 'vue-router';
import {get} from '../api/client';
import StatusBadge from '../components/StatusBadge.vue';
import CursorPager from '../components/CursorPager.vue';
const route=useRoute(),router=useRouter();
const data=ref({items:[]}),filter=ref('ready'),query=ref(''),error=ref(''),legacy=ref(null),loading=ref(false);
async function load(cursor=''){
 loading.value=true;error.value='';
 try{
  if(route.params.id){
   const record=await get('/proposals/'+route.params.id);
   if(record.analysis_run_id){await router.replace('/analysis-runs/'+record.analysis_run_id+'/review');return}
   legacy.value=record;
  }else data.value=await get('/review-inbox?'+new URLSearchParams({kind:'analysis',status:filter.value,q:query.value,...(cursor?{cursor}:{})}));
 }catch(e){error.value=e.message}finally{loading.value=false}
}
onMounted(()=>load());watch(()=>route.params.id,()=>{legacy.value=null;load()});
</script>
<template>
 <div class="page-heading"><div><div class="section-kicker">2 · 검수하고 승인하기</div><h1>검수·승인</h1><p class="muted">Agent가 정리한 정보를 원문과 비교하고, 승인한 품목만 식품 DB에 반영하세요.</p></div><RouterLink to="/documents" class="secondary">자료 가져오기</RouterLink></div>
 <p v-if="error" class="error" role="alert">{{error}}</p>
 <section v-if="legacy" class="panel"><h2>{{legacy.summary.title}}</h2><p class="muted">이전 수동 등록 기록입니다. 새 자료는 자료 가져오기에서 Agent 분석을 시작해 주세요.</p><StatusBadge :value="legacy.summary.status"/><p v-for="d in legacy.decisions" :key="d.id">{{d.actor.display_name}} · {{d.reason}}</p></section>
 <section v-else class="panel"><div class="toolbar wrap"><div class="tabs"><button v-for="[value,label] in [['ready','검수 대기'],['applying','DB 반영 중'],['applied','반영 완료'],['','전체']]" :key="value" :class="{active:filter===value}" @click="filter=value;load()">{{label}}</button></div><form class="row" @submit.prevent="load()"><input v-model="query" aria-label="검수 자료 검색" placeholder="자료 제목 검색"><button class="secondary">검색</button></form></div>
 <div class="table-scroll"><table><thead><tr><th>자료</th><th>상태</th><th>추출한 품목</th><th>검수 대기</th><th></th></tr></thead><tbody><tr v-for="item in data.items" :key="item.id" class="clickable" @click="router.push(item.href)"><td><b>{{item.title}}</b><small class="cell-sub">{{new Date(item.created_at).toLocaleDateString('ko-KR')}}</small></td><td><StatusBadge :value="item.status"/></td><td>{{item.item_count}}개</td><td>{{item.pending_count}}개</td><td><RouterLink :to="item.href" class="link">{{item.status==='applied'?'반영 내역':'검수 시작'}} →</RouterLink></td></tr></tbody></table></div>
 <p v-if="!data.items.length" class="empty">{{loading?'불러오는 중…':'이 상태의 자료가 없습니다. 자료를 가져오면 Agent 분석 후 이곳에 표시됩니다.'}}</p><CursorPager :next="data.next_cursor" @next="load"/>
 </section>
</template>
