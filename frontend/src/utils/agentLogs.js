/*
==============================================================================
FMS_FILE_SPEC
agentLogs.js - Vue 애플리케이션 agentLogs
==============================================================================
설명:
    - Vue 애플리케이션 agentLogs
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

    2026-10-22  김재현(Finn) v0.1.0   자료·Agent·검수 승인·식품 DB 중심 흐름 및 알레르기 표기 정리

    상세 Git 이력: git log --follow -- frontend/src/utils/agentLogs.js
    공통 규칙: doc/file-header-policy.md
==============================================================================
*/
/** User-facing action logs, with continuation notices separated from failures. */
export const boardNames={product_01:'공산품',product_02:'농수축산물',product_del:'단종제품'};
export function jobNotices(issues=[]){
 const continuation=issues.filter(i=>i.code==='SCAN_CONTINUES');
 return {errors:issues.filter(i=>i.code!=='SCAN_CONTINUES'),continuation:continuation.length?{count:continuation.length,boards:[...new Set(continuation.map(i=>boardNames[i.board]||i.board).filter(Boolean))]}:null};
}
export function agentSteps(report){
 if(!report)return [];
 const executed=[...(report.tool_executions||[]),...Object.values(report.tool_results||{}).map(r=>r.trace)];
 return (report.plan?.routes||[]).map(step=>{
  const result=executed.find(r=>r.source_id===step.source_id);
  return {...step,...result,state:result?.review_required?'review':report.active_tool?.source_id===step.source_id?'running':result?(report.status==='completed'?'completed':'prepared'):'pending'};
 });
}
