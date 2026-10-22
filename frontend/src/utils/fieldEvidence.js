/*
==============================================================================
FMS_FILE_SPEC
fieldEvidence.js - Vue 애플리케이션 fieldEvidence
==============================================================================
설명:
    - Vue 애플리케이션 fieldEvidence
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

    상세 Git 이력: git log --follow -- frontend/src/utils/fieldEvidence.js
    공통 규칙: doc/file-header-policy.md
==============================================================================
*/
// Return only field references belonging to the currently selected product.
export function fieldEvidenceOptions(sources={},allowed=[]){
 const scope=new Set(allowed);
 const labels={food_name:'식품명',specification:'규격',amount:'단가',attributes:'식품 속성',ingredients:'원재료',allergens:'알레르기'};
 return Object.entries(labels).flatMap(([key,label])=>{
  const ids=[...new Set((sources[key]?.evidence_ids||[]).filter(id=>scope.has(id)))];
  return ids.length?[{key,label,ids}]:[];
 });
}
