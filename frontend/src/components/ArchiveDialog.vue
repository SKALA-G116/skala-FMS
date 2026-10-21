<!--
==============================================================================
FMS_FILE_SPEC
ArchiveDialog.vue - 삭제 보관·복구 결정
==============================================================================
설명:
    - 삭제 보관·복구 결정
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

    상세 Git 이력: git log --follow -- frontend/src/components/ArchiveDialog.vue
    공통 규칙: doc/file-header-policy.md
==============================================================================
-->
<script setup>
import {ref,onMounted} from 'vue';import {api} from '../api/client';import {Trash2,RotateCcw,X} from 'lucide-vue-next';
const props=defineProps({item:Object,kind:{type:String,default:'food'}});const emit=defineEmits(['close','done']);const dialog=ref(null),busy=ref(false),error=ref(''),reason=ref('');onMounted(()=>dialog.value.showModal());
async function submit(){busy.value=true;error.value='';try{const restore=props.item.archived;const result=await api('/'+(props.kind==='food'?'foods':'documents')+'/'+props.item.id+(restore?'/restore':''),{method:restore?'POST':'DELETE',body:{archive_version:props.item.archive_version||0,reason:reason.value.trim()||(restore?'사용자 요청으로 복구':'사용자 요청으로 목록에서 삭제')}});emit('done',result.data)}catch(e){error.value=e.message}finally{busy.value=false}}
</script><template><dialog ref="dialog" class="archive-dialog" @cancel.prevent="!busy&&emit('close')" aria-labelledby="archive-title"><button class="close" @click="emit('close')" :disabled="busy" aria-label="닫기"><X :size="20"/></button><div :class="['archive-mark',{restore:item.archived}]"><RotateCcw v-if="item.archived" :size="24"/><Trash2 v-else :size="24"/></div><h2 id="archive-title">{{item.archived?'복구할까요?':'목록에서 삭제할까요?'}}</h2><p class="archive-item-name">{{item.title||item.food_record?.food_name}}</p><p class="muted">{{item.archived?'복구하면 원래 목록에 다시 표시됩니다.':kind==='food'?'이 규격의 식품을 식품·단가 조회에서 숨깁니다. 원문과 변경 이력은 보관되며, 삭제한 항목에서 복구할 수 있습니다.':'자료 목록과 연결된 원본 표 목록에서 숨깁니다. 이미 반영된 식품 정보와 근거 파일은 보관되며, 삭제한 자료에서 복구할 수 있습니다.'}}</p><label class="form-label">메모 <span class="muted">선택</span><input v-model="reason" maxlength="500" placeholder="삭제·복구 사유를 남겨 주세요."></label><p v-if="error" class="error" role="alert">{{error}}</p><div class="dialog-actions"><button class="secondary" @click="emit('close')" :disabled="busy">취소</button><button :class="item.archived?'primary':'danger-button'" @click="submit" :disabled="busy">{{busy?'처리 중…':item.archived?'복구':'목록에서 삭제'}}</button></div></dialog></template>
