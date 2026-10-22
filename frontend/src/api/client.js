/*
==============================================================================
FMS_FILE_SPEC
client.js - 프런트 공통 API client
==============================================================================
설명:
    - 프런트 공통 API client
입력·출력 명세:
    - 입력: 버전 API 경로·method·body·ETag
    - 출력: JSON 응답·ETag 또는 표준 API 오류
실행 가정:
    - 세션·CSRF·업무 변경 키를 연결하며 비밀값을 문서/로그에 적지 않음
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

    상세 Git 이력: git log --follow -- frontend/src/api/client.js
    공통 규칙: doc/file-header-policy.md
==============================================================================
*/
let csrf='',authEpoch=0,unauthorizedHandler=()=>{};
export function setUnauthorizedHandler(handler){unauthorizedHandler=handler}
export function clearCsrf(){csrf='';authEpoch++}
export class ApiError extends Error {constructor(status,data){super(data?.error?.message||'요청을 처리할 수 없습니다.');this.status=status;this.data=data}}
export async function refreshCsrf(){const epoch=authEpoch,r=await fetch('/api/v1/auth/csrf',{cache:'no-store',credentials:'same-origin'});const token=(await r.json()).csrf_token;if(epoch===authEpoch)csrf=token}
export async function api(path,options={}){
 const method=options.method||'GET';if(method!=='GET'&&!csrf)await refreshCsrf();
 const headers={...options.headers};if(method!=='GET'){headers['X-CSRF-Token']=csrf;headers['Idempotency-Key']=options.key||crypto.randomUUID()}
 if(options.etag)headers['If-Match']=options.etag;
 let body=options.body;if(body&&!(body instanceof FormData)){headers['Content-Type']='application/json';body=JSON.stringify(body)}
 const requestEpoch=authEpoch;const r=await fetch('/api/v1'+path,{method,headers,body,signal:options.signal,cache:'no-store',credentials:'same-origin'});const data=r.status===204?null:await r.json();if(!r.ok){if(r.status===401&&requestEpoch===authEpoch){csrf='';if(path!=='/auth/session')unauthorizedHandler()}throw new ApiError(r.status,data);}
 if(data?.csrf_token&&requestEpoch===authEpoch)csrf=data.csrf_token;return {data,etag:r.headers.get('ETag')}
}
export const get=async(path)=>(await api(path)).data;
