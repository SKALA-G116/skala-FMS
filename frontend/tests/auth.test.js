/*
==============================================================================
FMS_FILE_SPEC
auth.test.js - 기능·경계·회귀 검증
==============================================================================
설명:
    - 기능·경계·회귀 검증
입력·출력 명세:
    - 입력: 테스트 fixture·가상 입력·명시적 mock/테스트 대역
    - 출력: assert 결과와 실패 사유
실행 가정:
    - DB 통합 테스트는 별도 _test DB·임시 assets 사용; 대역과 실제 모델 검증을 구분
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

    2026-10-22  김재현(Finn) v0.1.0   세션 복원·만료·로그아웃 경계와 접근 제어 검증

    상세 Git 이력: git log --follow -- frontend/tests/auth.test.js
    공통 규칙: doc/file-header-policy.md
==============================================================================
*/
import test from 'node:test';
import assert from 'node:assert/strict';
import {createAuthSession,requireSession,safeReturnPath} from '../src/api/auth.js';
import {api,clearCsrf,setUnauthorizedHandler} from '../src/api/client.js';
const identity={username:'tester',roles:['reader']};
const unauthorized=()=>Object.assign(new Error('로그인 필요'),{status:401});
const route=path=>({path,fullPath:path,query:{}});

test('익명 사용자는 업무 화면 대신 로그인으로 이동한다',async()=>{
 const auth=createAuthSession({get:async()=>{throw unauthorized()}});
 const result=await requireSession(route('/products'),auth);
 assert.deepEqual(result,{path:'/login',query:{redirect:'/products'}});
 assert.equal(auth.user.value,null);assert.equal(auth.ready.value,true);
 assert.equal(await requireSession(route('/login'),auth),true);
});

test('유효 세션을 서버로 확인하고 로그인 화면에서 안전한 원래 경로로 복귀한다',async()=>{
 let count=0;const auth=createAuthSession({get:async()=>{count++;return identity}});
 assert.equal(await requireSession(route('/products'),auth),true);
 assert.equal(await requireSession({...route('/login'),query:{redirect:'/documents'}},auth),'/documents');
 assert.equal(count,2);
 for(const path of ['https://evil.example','//evil.example','/\\evil','/login'])assert.equal(safeReturnPath(path),'/');
});

test('로그아웃 전에 시작한 인증 응답이 뒤늦게 도착해도 로그인 상태가 복원되지 않는다',async()=>{
 let resolveIdentity,finishLogout;const auth=createAuthSession({get:()=>new Promise(resolve=>{resolveIdentity=resolve}),api:()=>new Promise(resolve=>{finishLogout=resolve})});
 const checking=auth.check();auth.user.value=identity;
 const logout=auth.signOut();assert.equal(auth.user.value,null);
 assert.equal(await auth.check(),null);
 resolveIdentity(identity);await checking;assert.equal(auth.user.value,null);
 finishLogout({});await logout;assert.equal(auth.user.value,null);
});

test('서버 장애를 로그인 성공으로 취급하지 않고 로그인 경로에서 재이동을 반복하지 않는다',async()=>{
 const auth=createAuthSession({get:async()=>{throw new Error('offline')}});auth.user.value=identity;
 const result=await requireSession(route('/products'),auth);
 assert.equal(result.path,'/login');assert.equal(result.query.reason,'unavailable');assert.equal(auth.user.value,null);
 assert.equal(await requireSession(route('/login'),auth),true);
});

test('업무 API의 401은 즉시 로그인 상태 해제를 알린다',async()=>{
 const previous=globalThis.fetch;let expired=0;setUnauthorizedHandler(()=>expired++);
 globalThis.fetch=async(url,options)=>{assert.equal(options.cache,'no-store');assert.equal(options.credentials,'same-origin');return {ok:false,status:401,json:async()=>({error:{message:'로그인 필요'}})}};
 try{
  await assert.rejects(api('/products'),e=>e.status===401);assert.equal(expired,1);
 }finally{globalThis.fetch=previous;setUnauthorizedHandler(()=>{})}
});


test('로그아웃 뒤 새 CSRF 토큰으로 로그인하고 실패한 비밀번호로 사용자를 만들지 않는다',async()=>{
 let refreshed=0,cleared=0;
 const auth=createAuthSession({get:async()=>identity,refreshCsrf:async()=>refreshed++,clearCsrf:()=>cleared++,api:async(path,options)=>{if(options.method==='POST')throw unauthorized();return {data:null}}});
 auth.user.value=identity;await auth.signOut();assert.equal(cleared,2);
 await assert.rejects(auth.signIn({username:'tester',password:'wrong'}),e=>e.status===401);
 assert.equal(refreshed,1);assert.equal(auth.user.value,null);
});


test('새 로그인 시도 전에 시작한 오래된 401 응답은 새 인증 상태를 지우지 않는다',async()=>{
 const previous=globalThis.fetch;let resolveResponse,expired=0;setUnauthorizedHandler(()=>expired++);
 globalThis.fetch=()=>new Promise(resolve=>{resolveResponse=resolve});
 try{
  const pending=api('/products');clearCsrf();
  resolveResponse({ok:false,status:401,json:async()=>({error:{message:'지난 세션 만료'}})});
  await assert.rejects(pending,e=>e.status===401);assert.equal(expired,0);
 }finally{globalThis.fetch=previous;setUnauthorizedHandler(()=>{})}
});
