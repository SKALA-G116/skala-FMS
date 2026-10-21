/*
==============================================================================
FMS_FILE_SPEC
useJob.js - Vue 애플리케이션 useJob
==============================================================================
설명:
    - Vue 애플리케이션 useJob
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

    상세 Git 이력: git log --follow -- frontend/src/composables/useJob.js
    공통 규칙: doc/file-header-policy.md
==============================================================================
*/
import {ref,onUnmounted} from 'vue';import {api} from '../api/client';
export function useJob(){const job=ref(null);let timer,controller,attempt=0,disposed=false;
 const stop=()=>{clearTimeout(timer);controller?.abort()};
 async function poll(id,done){if(disposed)return;if(document.hidden){timer=setTimeout(()=>poll(id,done),5000);return}controller=new AbortController();try{job.value=(await api('/jobs/'+id,{signal:controller.signal})).data;if(['succeeded','partial','failed','cancelled'].includes(job.value.status)){done?.(job.value);return}}catch(e){if(e.name==='AbortError')return}timer=setTimeout(()=>poll(id,done),[2000,5000,10000][Math.min(attempt++,2)])}
 const start=(id,done)=>{stop();attempt=0;poll(id,done)};onUnmounted(()=>{disposed=true;stop()});return {job,start,stop}}
