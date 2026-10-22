"""
==============================================================================
FMS_FILE_SPEC
schemas.py - LLM 계획·추출 응답 스키마
==============================================================================
설명:
    - LLM 계획·추출 응답 스키마
입력·출력 명세:
    - 입력: 문서 유형·지원하는 식품 변경 종류
    - 출력: 검증 가능한 JSON Schema 정의
실행 가정:
    - 스키마 적합성이 식품 사실의 정확성을 보장하지 않음
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

    2026-10-22  김재현(Finn) v0.1.0   라벨 응답 축소·형식 오류 격리·안전한 진단 및 부분 완료 검수

    2026-10-22  김재현(Finn) v0.1.0   원재료 전용 추출·함량 없는 표시사항 보존·OCR 근거 연결 검증

    2026-10-22  김재현(Finn) v0.1.0   OCR 문장 좌표·상품 소속·필드 근거 보존 및 발표 자료 단순화

    상세 Git 이력: git log --follow -- backend/app/domains/analysis/schemas.py
    공통 규칙: doc/file-header-policy.md
==============================================================================
"""

# FMS_MODULE_METADATA_BEGIN
__author__ = "김재현(Finn)"
__email__ = "penguin.klg@gmail.com"
__version__ = "0.1.0"
__status__ = "Development"
# FMS_MODULE_METADATA_END

# ---------------------------------------------------------------------------
# 1. Imports / Module implementation
# ---------------------------------------------------------------------------


def nullable(t):return {'type':[t,'null']}

PLAN={'type':'object','additionalProperties':False,'properties':{'document_type':{'type':'string','enum':['notice','price_table','mixed','marketing','other']},'summary':{'type':'string'},'tasks':{'type':'array','maxItems':6,'items':{'type':'string','enum':['extract_prices','extract_food_profiles','extract_supply_changes','extract_substitutions','match_catalog','create_review_excel','no_business_change']}}},'required':['document_type','summary','tasks']}

EVENT_FIELDS={
 'kind':{'type':'string','enum':['price','temporarily_unavailable','supply_ended','discontinued','available','substitution','new_product','food_profile']},
 'company_name':nullable('string'),'food_code':nullable('string'),'attributes_text':nullable('string'),'allergen_text':nullable('string'),
 'product_name':nullable('string'),'spec':nullable('string'),'amount':nullable('string'),
 'quantity':nullable('string'),'unit':{'type':['string','null'],'enum':['g','kg','ml','l','ea','bag','box','pack',None]},
 'effective_from':nullable('string'),'effective_to':nullable('string'),'reason':nullable('string'),
 'replacements':{'type':'array','maxItems':6,'items':{'type':'string'}},
 'price_basis':nullable('string'),'uncertainties':{'type':'array','maxItems':8,'items':{'type':'string'}},
 'source_ids':{'type':'array','minItems':1,'maxItems':12,'items':{'type':'string'}}}

def event_schema(ids,spatial=False):
    from backend.app.domains.analysis.spatial import field_evidence_schema
    properties={**EVENT_FIELDS,'ingredients_text':nullable('string'),'source_ids':{'type':'array','minItems':1,'maxItems':12,'items':{'type':'string','enum':ids}}}
    if spatial:properties['field_evidence']=field_evidence_schema(ids)
    event={'type':'object','additionalProperties':False,'properties':properties,'required':list(EVENT_FIELDS)}
    return {'type':'object','additionalProperties':False,'properties':{'events':{'type':'array','maxItems':24,'items':event}},'required':['events']}


def label_schema(ids):
    """One row's label supplements attributes, never proposes products or prices."""
    fields={key:EVENT_FIELDS[key] for key in ('attributes_text','allergen_text')}
    from backend.app.domains.analysis.spatial import field_evidence_schema
    fields['field_evidence']=field_evidence_schema(ids)
    fields['ingredients_text']=nullable('string')
    fields['source_ids']={'type':'array','minItems':1,'maxItems':min(12,len(ids)),'uniqueItems':True,'items':{'type':'string','enum':ids}}
    return {'type':'object','additionalProperties':False,'properties':fields,'required':['attributes_text','allergen_text','source_ids']}
