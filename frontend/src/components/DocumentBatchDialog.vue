<!--
==============================================================================
FMS_FILE_SPEC
DocumentBatchDialog.vue - 선택 자료의 일괄 작업
==============================================================================
설명:
    - 선택 자료의 일괄 작업
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

    상세 Git 이력: git log --follow -- frontend/src/components/DocumentBatchDialog.vue
    공통 규칙: doc/file-header-policy.md
==============================================================================
-->
<script setup>
import {ref,onMounted,computed} from 'vue';import {api} from '../api/client';import {Trash2,RotateCcw,AlertTriangle,X} from 'lucide-vue-next';
const props=defineProps({items:Array,action:String});const emit=defineEmits(['close','done']);const dialog=ref(null),busy=ref(false),error=ref(''),confirmation=ref('');const labels={archive:'삭제',restore:'복구',purge:'영구 삭제'};const permanent=computed(()=>props.action==='purge');onMounted(()=>dialog.value.showModal());
async function submit(){busy.value=true;error.value='';try{const result=await api('/document-actions',{method:'POST',body:{action:props.action,items:props.items.map(d=>({id:d.id,archive_version:d.archive_version||0})),reason:'자료함에서 선택한 자료 '+labels[props.action],...(permanent.value?{confirmation:confirmation.value}:{})}});emit('done',result.data)}catch(e){error.value=e.message}finally{busy.value=false}}
</script><template><dialog ref="dialog" class="archive-dialog" @cancel.prevent="!busy&&emit('close')" aria-labelledby="batch-title"><button class="close" @click="emit('close')" :disabled="busy" aria-label="닫기"><X :size="20"/></button><div :class="['archive-mark',{restore:action==='restore'}]"><AlertTriangle v-if="permanent" :size="24"/><RotateCcw v-else-if="action==='restore'" :size="24"/><Trash2 v-else :size="24"/></div><h2 id="batch-title">{{items.length}}개 자료를 {{labels[action]}}할까요?</h2><ul class="batch-titles"><li v-for="d in items.slice(0,3)" :key="d.id">{{d.title}}</li><li v-if="items.length>3">외 {{items.length-3}}개</li></ul><p v-if="permanent" class="purge-warning"><b>복구할 수 없습니다.</b> 원문·첨부·추출 결과·미승인 변경안을 영구 삭제합니다. 다른 자료가 쓰지 않는 파일도 삭제합니다. 승인·반영 이력의 근거로 쓰인 자료는 삭제하지 않습니다.</p><p v-else class="muted">{{action==='restore'?'선택한 자료를 자료함으로 되돌립니다.':'선택한 자료를 삭제한 자료 목록으로 옮깁니다. 필요하면 복구할 수 있습니다.'}}</p><label v-if="permanent" class="form-label">계속하려면 <b>영구 삭제</b>를 입력하세요.<input v-model="confirmation" autocomplete="off" placeholder="영구 삭제" aria-label="영구 삭제 확인 문구"></label><p v-if="error" class="error" role="alert">{{error}}</p><div class="dialog-actions"><button class="secondary" @click="emit('close')" :disabled="busy">취소</button><button :class="action==='restore'?'primary':'danger-button'" @click="submit" :disabled="busy||(permanent&&confirmation!=='영구 삭제')">{{busy?'처리 중…':`${items.length}개 ${labels[action]}`}}</button></div></dialog></template>
