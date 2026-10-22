/*
==============================================================================
FMS_FILE_SPEC
auth.js - Vue 애플리케이션 auth
==============================================================================
설명:
    - Vue 애플리케이션 auth
입력·출력 명세:
    - 입력: 애플리케이션·라우트·상태·빌드 설정
    - 출력: 화면·공유 상태·빌드 산출물
실행 가정:
    - 설치 의존성과 생성 lock 파일은 원본 형식을 유지
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

    상세 Git 이력: git log --follow -- frontend/src/api/auth.js
    공통 규칙: doc/file-header-policy.md
==============================================================================
*/
/** Shared authentication state; no credential or session-token storage in JavaScript. */
import {ref} from 'vue';
import {api,get,refreshCsrf,clearCsrf,setUnauthorizedHandler} from './client.js';

export function createAuthSession(transport={api,get,refreshCsrf,clearCsrf}){
 const user=ref(null),ready=ref(false);let generation=0,pending=null,signingOut=false;
 function clear(){transport.clearCsrf?.();generation++;pending=null;user.value=null;ready.value=true}
 async function check(){
  if(signingOut)return null;
  if(pending)return pending;
  const version=generation;
  const request=(async()=>{
   try{const identity=await transport.get('/auth/me');if(version===generation)user.value=identity;return version===generation?identity:null}
   catch(e){if(version===generation)clear();if(e.status!==401)throw e;return null}
   finally{if(version===generation){ready.value=true;pending=null}}
  })();pending=request;return request;
 }
 async function signIn(credentials){
  clear();const version=generation;
  if(transport.refreshCsrf)await transport.refreshCsrf();
  const result=await transport.api('/auth/session',{method:'POST',body:credentials});
  if(version===generation){user.value=result.data.user;ready.value=true}
  return user.value;
 }
 async function signOut(){
  // Hide protected content before waiting for the server, including late requests.
  signingOut=true;clear();
  try{await transport.api('/auth/session',{method:'DELETE'})}
  catch(e){if(e.status!==401)throw e}
  finally{transport.clearCsrf?.();signingOut=false}
 }
 return {user,ready,check,clear,signIn,signOut};
}
export const auth=createAuthSession();
setUnauthorizedHandler(()=>auth.clear());

export function safeReturnPath(value){return typeof value==='string'&&value.startsWith('/')&&!value.startsWith('//')&&!value.startsWith('/login')&&!value.includes('\\')?value:'/'}

export async function requireSession(to,session=auth){
 try{await session.check()}catch{return to.path==='/login'?true:{path:'/login',query:{redirect:to.fullPath,reason:'unavailable'}}}
 if(!session.user.value)return to.path==='/login'?true:{path:'/login',query:{redirect:to.fullPath}};
 if(to.path==='/login')return safeReturnPath(to.query.redirect);
 return true;
}
