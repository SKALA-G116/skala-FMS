"""
==============================================================================
FMS_FILE_SPEC
spatial.py - 프로젝트 설정 spatial.py
==============================================================================
설명:
    - 프로젝트 설정 spatial.py
입력·출력 명세:
    - 입력: 도구별 설정·실행 환경
    - 출력: 해당 도구의 구성 또는 실행 결과
실행 가정:
    - 실제 비밀값과 로컬 실행 데이터는 Git에서 제외
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

    상세 Git 이력: git log --follow -- backend/app/domains/analysis/spatial.py
    공통 규칙: doc/file-header-policy.md

기존 모듈 설명:
    Preserve OCR ownership and field evidence without extra model calls.
==============================================================================
"""

# FMS_MODULE_METADATA_BEGIN
__author__ = '김재현(Finn)'
__email__ = 'penguin.klg@gmail.com'
__version__ = "0.1.0"
__status__ = "Development"
# FMS_MODULE_METADATA_END

# ---------------------------------------------------------------------------
# 1. Imports / Module implementation
# ---------------------------------------------------------------------------

from copy import deepcopy
import re

PRODUCT_FIELDS=('product_name','food_code','spec','amount','quantity','unit','attributes_text','ingredients_text','allergen_text')
FIELD_KEYS={'product_name':'food_name','spec':'specification','attributes_text':'attributes','ingredients_text':'ingredients','allergen_text':'allergens'}

def canonical(value):return re.sub(r'\W+','',str(value or '')).casefold()

def ordered_lines(segments):
    # Keep all content. Geometric order is only a reading aid, never proof of ownership.
    def position(s):
        box=s.get('locator',{}).get('bbox')
        return (box[1],box[0]) if box and len(box)==4 else (0,0)
    return sorted(segments,key=position)

def field_evidence_schema(ids):
    return {'type':'array','maxItems':12,'items':{'type':'object','additionalProperties':False,'properties':{'field':{'enum':list(PRODUCT_FIELDS)+['company_name','effective_from','effective_to','reason']},'source_ids':{'type':'array','minItems':1,'maxItems':100,'uniqueItems':True,'items':{'type':'string','enum':ids}}},'required':['field','source_ids']}}

def ground_fields(event,mapping):
    """Reject context-only product attributes and retain per-field OCR locators.

    Explicit field references are checked against the region-local mapping. Older
    responses may omit them; verbatim matching then derives the supporting lines.
    """
    if not any(s.get('region_label') for s in mapping.values()):
        event.pop('field_evidence',None)
        return []
    claims={};invalid=set()
    for claim in event.pop('field_evidence',[]) or []:
        field=claim['field'];ids=claim['source_ids']
        if field in claims or any(key not in mapping for key in ids):invalid.add(field)
        claims[field]=ids
    sources={};manual=[]
    for field in (*PRODUCT_FIELDS,'company_name'):
        value=event.get(field)
        if value is None:continue
        keys=claims.get(field,list(mapping))
        eligible=[key for key in keys if key in mapping and (field not in PRODUCT_FIELDS or mapping[key].get('source_role','product')!='context')]
        needle=canonical(value)
        joined=canonical(' '.join(mapping[key]['text'] for key in eligible))
        # Numeric and raw field values must be grounded. Names and specs may be
        # normalized, so reject only explicit invalid references for those fields.
        strict=field in ('product_name','amount','food_code','attributes_text','ingredients_text','allergen_text')
        if field in invalid or (field in claims and not eligible) or (strict and (not needle or needle not in joined)):
            event[field]=None
            event.setdefault('validation_warnings',[]).append('상품 전용 근거를 확인할 수 없는 '+field+' 값을 제외했습니다.')
            manual.extend(s['evidence_id'] for s in mapping.values())
            continue
        matched=[key for key in eligible if needle and needle in canonical(mapping[key]['text'])]
        if not matched and needle and needle in joined:
            # Find the minimal source span without repeatedly joining every window.
            normalized=[canonical(mapping[key]['text']) for key in eligible]
            offset=joined.find(needle);end=offset+len(needle);cursor=0
            for key,line in zip(eligible,normalized):
                next_cursor=cursor+len(line)
                if next_cursor>offset and cursor<end:matched.append(key)
                cursor=next_cursor
        if not matched and field in claims:matched=eligible
        if matched:
            sources[FIELD_KEYS.get(field,field)]={'origin':'ocr_llm','raw_value':value,'evidence_ids':list(dict.fromkeys(mapping[key]['evidence_id'] for key in matched)),'locators':[deepcopy(mapping[key]['locator']) for key in matched]}
    event['extracted_field_sources']=sources
    return list(dict.fromkeys(manual))
