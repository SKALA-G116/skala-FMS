<!--
==============================================================================
FMS_FILE_SPEC
SourceComparison.vue - 원본 이미지·추출 텍스트 비교
==============================================================================
설명:
    - 원본 이미지·추출 텍스트 비교
입력·출력 명세:
    - 입력: props·표준 DTO·상위 화면 상태
    - 출력: 표시 결과와 emit 이벤트
실행 가정:
    - 업무 반영은 권한 있는 API를 통해 수행하고 컴포넌트가 직접 DB에 접근하지 않음
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

    2026-10-22  김재현(Finn) v0.1.0   25MB·표 삽입 이미지 근거 보완 및 검수 오류 개선

    2026-10-22  김재현(Finn) v0.1.0   OCR 문장 좌표·상품 소속·필드 근거 보존 및 발표 자료 단순화

    상세 Git 이력: git log --follow -- frontend/src/components/SourceComparison.vue
    공통 규칙: doc/file-header-policy.md
==============================================================================
-->
<script setup>
import {ref,watch,computed} from 'vue';import {fieldEvidenceOptions} from '../utils/fieldEvidence';import {get} from '../api/client';
const emit=defineEmits(['ready']);const props=defineProps({ids:{type:Array,default:()=>[]},fieldSources:{type:Object,default:()=>({})}});const evidence=ref([]),images=ref([]),error=ref(''),loading=ref(false),mode=ref('preview'),zoom=ref(false),marks=ref(true);const sourceUrl=computed(()=>evidence.value.find(e=>e.source_url)?.source_url);let serial=0;
const focus=ref('');const fieldOptions=computed(()=>fieldEvidenceOptions(props.fieldSources,props.ids));const focusedIds=computed(()=>fieldOptions.value.find(option=>option.key===focus.value)?.ids||props.ids);
watch(()=>props.ids,()=>{focus.value=''})
watch(()=>focusedIds.value,async ids=>{const version=++serial;zoom.value=false;loading.value=true;evidence.value=[];images.value=[];emit('ready',false);error.value='';try{const rows=await Promise.all(ids.map(id=>get('/evidence/'+id)));if(version!==serial)return;evidence.value=rows;const groups=new Map();for(const ev of rows){const l=ev.locator;if(!['image','pdf'].includes(l.kind))continue;const key=l.asset_id+':'+l.page_number+':'+(l.embedded_image||'');if(!groups.has(key))groups.set(key,{key,kind:l.kind,asset:l.asset_id,page:l.page_number,embedded:l.embedded_image,sheet:l.sheet_name,rowStart:l.row_start,rowEnd:l.row_end,regions:[]});if(l.bbox)groups.get(key).regions.push(l.bbox)}const previews=await Promise.all([...groups.values()].map(async g=>({...g,url:(await get('/assets/'+g.asset+'/access')).url+'&preview=true'+(g.embedded?'&embedded_image='+g.embedded:'')})));if(version===serial){images.value=previews;if(!previews.length)mode.value='text';emit('ready',rows.length>0)}}catch(e){if(version===serial)error.value=e.message}finally{if(version===serial)loading.value=false}},{immediate:true});
const region=b=>({left:b[0]*100+'%',top:b[1]*100+'%',width:(b[2]-b[0])*100+'%',height:(b[3]-b[1])*100+'%'});
</script>
<template>
<section class="source-comparison">
  <header class="source-heading"><div><span class="source-kicker">선택한 품목의 근거</span><h3>원본 자료</h3></div><a v-if="sourceUrl" :href="sourceUrl" target="_blank" rel="noopener noreferrer">게시글 원문 ↗</a></header>
  <div v-if="fieldOptions.length" class="field-evidence-picker" aria-label="항목별 원문 근거"><span>근거 보기</span><button :aria-pressed="!focus" @click="focus=''">전체</button><button v-for="option in fieldOptions" :key="option.key" :aria-pressed="focus===option.key" @click="focus=option.key">{{option.label}}</button></div>
  <div class="source-tabs" aria-label="원문 보기 방식"><button :aria-pressed="mode==='preview'" @click="mode='preview'">원본 보기 <span>{{images.length}}</span></button><button :aria-pressed="mode==='text'" @click="mode='text'">추출 텍스트 <span>{{evidence.length}}</span></button></div>
  <div class="source-content">
    <p v-if="loading" class="muted" role="status">이 품목의 원문을 불러오는 중…</p><p v-if="error" class="error" role="alert">{{error}}</p>
    <template v-if="!loading">
      <template v-if="mode==='preview'&&images.length">
        <div class="preview-controls"><label><input type="checkbox" v-model="marks">근거 위치 표시</label><button :aria-pressed="zoom" @click="zoom=!zoom">{{zoom?'화면에 맞추기':'크게 보기 ＋'}}</button></div>
        <p class="source-help">원문의 강조된 부분과 추출된 정보를 대조해 주세요.</p>
        <article v-for="g in images" :key="g.key" class="preview-page"><div class="source-caption">{{g.embedded?g.sheet+' · 삽입 이미지 '+g.embedded:(g.kind==='image'?'이미지':'PDF')+' · '+g.page+'페이지'}}</div><div class="preview-scroll"><div v-if="g.kind==='image'" class="evidence-image" :class="{zoomed:zoom}"><img :src="g.url" alt="선택한 품목의 원문 이미지"><template v-if="marks"><div v-for="(box,i) in g.regions" :key="i" class="evidence-region" :style="region(box)"></div></template></div><iframe v-else :src="g.url+'#page='+g.page" title="선택 품목의 원본 PDF 페이지"></iframe></div></article>
        <button class="read-text-button" @click="mode='text'">읽기 어려우신가요? 추출 텍스트 보기 →</button>
      </template>
      <template v-if="mode==='text'||!images.length">
        <p class="source-help">이 품목과 연결된 본문·표·OCR 텍스트입니다. 이미지에서 읽은 값은 원본과 비교해 주세요.</p>
        <article v-for="ev in evidence" :key="ev.id" class="source-quote"><div class="quote-caption"><span>{{ev.locator.kind==='spreadsheet'?`${ev.locator.sheet_name} · ${ev.locator.cell_range}`:ev.locator.kind==='image'?'이미지 OCR':ev.locator.kind==='pdf'?'PDF':'게시글 본문'}}</span><span v-if="ev.ocr_confidence!=null">인식 신뢰도 {{Math.round(ev.ocr_confidence*100)}}%</span></div><blockquote>{{ev.quote}}</blockquote></article>
      </template>
      <div v-if="!evidence.length" class="empty">연결된 원문 근거가 없습니다.</div>
    </template>
  </div>
  <footer class="source-footer">원문 근거는 검토 결과와 함께 보관됩니다.</footer>
</section>
</template>
<style scoped>.field-evidence-picker{display:flex;gap:6px;flex-wrap:wrap;align-items:center;padding:10px 18px;border-bottom:1px solid #e0e8e3;font-size:11px}.field-evidence-picker button{border:1px solid #dce6df;border-radius:5px;padding:5px 8px;background:white;color:#526c5c;cursor:pointer}.field-evidence-picker button[aria-pressed=true]{background:#e9f4ed;border-color:#78a88c;color:#17664e}
.source-heading{padding:18px 22px;display:flex;justify-content:space-between;align-items:center;gap:10px;border-bottom:1px solid #e0e8e3}.source-kicker{font-size:11px;color:#718579}.source-heading h3{margin:5px 0 0;font-size:15px;color:#203b32}.source-heading a{font-size:11px;color:#42795b;white-space:nowrap}.source-tabs{padding:12px 18px 0;display:flex;gap:18px;border-bottom:1px solid #e0e8e3}.source-tabs button{background:none;border:0;border-bottom:2px solid transparent;color:#8a988f;font-size:12px;padding:0 3px 12px;cursor:pointer}.source-tabs button[aria-pressed=true]{border-color:#237151;color:#237151;font-weight:600}.source-tabs span{font-size:10px;margin-left:5px}.source-content{height:531px;overflow:auto;padding:16px 20px;overscroll-behavior:contain;background:#f8faf8;flex:1}.preview-controls{display:flex;justify-content:space-between;align-items:center;gap:8px}.preview-controls label{display:flex;align-items:center;gap:6px;font-size:11px;color:#6b8071}.preview-controls input{width:13px;height:13px;margin:0;accent-color:#287755}.preview-controls button,.read-text-button{border:1px solid #dce6de;background:white;color:#45745a;padding:7px 9px;border-radius:6px;font-size:11px;cursor:pointer}.source-help{font-size:11px;line-height:1.8;color:#859389;margin:12px 0 18px}.source-caption{font-size:10px;color:#829085;margin:12px 0 9px}.preview-scroll{overflow:auto;max-width:100%;border:1px solid #e3e9e4;border-radius:6px;background:white}.evidence-image{margin:0!important;max-width:none;width:100%}.evidence-image.zoomed{width:1000px}.evidence-image img{width:100%;display:block}.evidence-region{border-width:1px;background:#e9b62b16}.preview-scroll iframe{width:100%;height:500px;border:0}.read-text-button{margin-top:18px;display:block;width:100%;padding:12px;background:#f1f6f2;border:0}.source-quote{padding:12px 0;border-top:1px solid #e4eae5}.quote-caption{display:flex;justify-content:space-between;gap:8px;color:#829187;font-size:10px}.source-quote blockquote{margin:10px 0 0;background:white;border:1px solid #e3ebe5;border-radius:7px;padding:12px;white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.8;color:#4b6253;font-size:13px}.source-footer{padding:16px 20px;color:#91a094;border-top:1px solid #e0e8e3;font-size:10px;background:white;margin-top:auto}button:focus-visible,a:focus-visible{outline:3px solid #86b89c;outline-offset:3px}
@media(min-width:1400px){.source-content{height:581px}}
@media(max-width:760px){.source-content{height:auto;max-height:70vh;min-height:360px}.source-heading{padding:18px}.source-content{padding:14px}.source-help{font-size:11px}}
</style>
