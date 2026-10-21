<!--
==============================================================================
FMS_FILE_SPEC
CursorPager.vue - 커서 기반 페이지 이동
==============================================================================
설명:
    - 커서 기반 페이지 이동
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

    상세 Git 이력: git log --follow -- frontend/src/components/CursorPager.vue
    공통 규칙: doc/file-header-policy.md
==============================================================================
-->
<script setup>defineProps({next:String,history:Boolean});defineEmits(['next','reset'])</script><template><div class="pager"><button v-if="history" class="quiet" @click="$emit('reset')">처음으로</button><button v-if="next" class="secondary" @click="$emit('next',next)">다음 페이지 →</button></div></template>
