<!--
==============================================================================
FMS_FILE_SPEC
StatusBadge.vue - 상태 표시
==============================================================================
설명:
    - 상태 표시
입력·출력 명세:
    - 입력: props·표준 DTO·상위 화면 상태
    - 출력: 표시 결과와 emit 이벤트
실행 가정:
    - 업무 반영은 권한 있는 API를 통해 수행하고 컴포넌트가 직접 DB에 접근하지 않음
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

    상세 Git 이력: git log --follow -- frontend/src/components/StatusBadge.vue
    공통 규칙: doc/file-header-policy.md
==============================================================================
-->
<script setup>defineProps({value:String});const labels={ready:'검토 대기',draft:'확인 필요',on_hold:'보류',approved:'승인 완료',applying:'반영 중',applied:'반영 완료',conflict:'충돌 확인',apply_failed:'반영 실패',rejected:'반려',queued:'대기 중',running:'진행 중',succeeded:'완료',partial:'일부 완료',failed:'실패',cancelled:'취소',not_analyzed:'분석 전',completed:'분석 완료',active:'정상',available:'공급 가능',temporarily_unavailable:'일시중단',supply_ended:'공급 종료',scheduled:'적용 예정',unknown:'미확인',discontinued:'단종'};</script><template><span class="badge" :class="value"><i></i>{{labels[value]||value}}</span></template>
