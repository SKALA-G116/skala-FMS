<!--
==============================================================================
FMS_FILE_SPEC
ImageEvidence.vue - 이미지 근거 위치 표시
==============================================================================
설명:
    - 이미지 근거 위치 표시
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

    상세 Git 이력: git log --follow -- frontend/src/components/ImageEvidence.vue
    공통 규칙: doc/file-header-policy.md
==============================================================================
-->
<script setup>
import {ref,computed,onUnmounted} from 'vue';import {api} from '../api/client';const props=defineProps({locator:Object});const url=ref(''),error=ref(''),busy=ref(false);let controller;async function show(){controller=new AbortController();busy.value=true;try{const r=await api('/assets/'+props.locator.asset_id+'/access',{signal:controller.signal});url.value=r.data.url+'&preview=true'}catch(e){if(e.name!=='AbortError')error.value=e.message}finally{busy.value=false}}onUnmounted(()=>controller?.abort());const region=computed(()=>{const [x0,y0,x1,y1]=props.locator.bbox;return {left:x0*100+'%',top:y0*100+'%',width:(x1-x0)*100+'%',height:(y1-y0)*100+'%'}})
</script><template><div class="image-evidence"><button v-if="!url" class="secondary" :disabled="busy" @click="show">{{busy?'원본 불러오는 중…':'원본에서 위치 보기'}}</button><p v-if="error" class="error">{{error}}</p><template v-if="url"><div v-if="locator.kind==='image'" class="evidence-image"><img :src="url" alt="근거가 포함된 원본 공지 이미지"><div :style="region" class="evidence-region" aria-label="추출 근거 영역"></div></div><iframe v-else :src="url+'#page='+locator.page_number" title="원본 PDF 근거 페이지"></iframe><button class="link small" @click="url=''">미리보기 닫기</button></template></div></template>
