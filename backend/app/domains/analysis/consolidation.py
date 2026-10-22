"""
==============================================================================
FMS_FILE_SPEC
consolidation.py - 원본 표 정규화·추출 후보 중복 통합
==============================================================================
설명:
    - 원본 표 정규화·추출 후보 중복 통합
입력·출력 명세:
    - 입력: 근거 ID를 가진 원문 구간·표 행·AI 추출 후보
    - 출력: 표준 DTO 후보·통합 출처·분리한 충돌 및 제외 이력
실행 가정:
    - OCR/LLM을 호출하지 않고 모호한 업체·규격·가격·기간을 합치지 않음
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
    2026-10-21  미지정      v0.1.0   파일 역할·입출력·가정·이력 명세 추가

    2026-10-21  미지정      v0.1.0   원본 속성 누락 복구·재정리 API·검토 동선 개선

    2026-10-21  김재현(Finn) v0.1.0   Agent 도구 선택 기반 리빌드·업무 경계 및 검증

    2026-10-22  김재현(Finn) v0.1.0   자료·Agent·검수 승인·식품 DB 중심 흐름 및 알레르기 표기 정리

    상세 Git 이력: git log --follow -- backend/app/domains/analysis/consolidation.py
    공통 규칙: doc/file-header-policy.md

기존 모듈 설명:
    Deterministic table recovery and conservative, provenance-preserving candidate merging.
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

from copy import deepcopy
import re
from backend.app.infrastructure.database import uid
from backend.app.domains.catalog.record import (
    from_table_row, header_mapping, from_event, upgrade_event, company_display,
    ingredient_details, merge_profile,
)

VERSION = 'food-consolidation-v4'


def canonical(value):
    return re.sub(r'\W+', '', value or '').casefold()


def enrich_tables(segments):
    """Recover vendor tables from cached text without repeating OCR or inference."""
    result=deepcopy(segments);mapping=None;key=None;company=None;company_segment=None
    for segment in result:
        loc=segment['locator'];scope=(segment.get('asset_id'),loc.get('kind'),loc.get('sheet_name'))
        if scope!=key:mapping=None;company=None;company_segment=None;key=scope
        if loc.get('kind') not in ('spreadsheet','html'):continue
        row=[cell.strip() for cell in segment['text'].split('|')]
        nonempty=[value for value in row if value]
        if not mapping and len(nonempty)==1 and re.match(r'^(?:(?:농업|어업)회사법인\s*)?(?:㈜|\(주\)|주식회사)',nonempty[0]):
            company=company_display(nonempty[0]);company_segment=segment
        detected=header_mapping(row)
        if detected:
            mapping=detected;segment['structured_table_header']=True;continue
        if not mapping or len(row)<=max(mapping.values()):continue
        existing=segment.get('food_record')
        if existing and (existing.get('prices',{}).get('source_columns') or any(v.get('origin')=='merged_cell' for v in existing.get('field_sources',{}).values())):continue
        record=from_table_row(row,mapping,loc,company_name=company)
        if not record:continue
        for field,source in record['field_sources'].items():
            origin=company_segment if field=='company_name' and source['origin']=='parser_context' else segment
            source['evidence_ids']=[origin['evidence_id']] if origin.get('evidence_id') else []
            source['locator']=deepcopy(origin['locator'])
            prior=origin.get('food_record',{}).get('field_sources',{}).get(field,{})
            if prior.get('document_revision_id'):source['document_revision_id']=prior['document_revision_id']
        segment['food_record']=record
    return result


def table_event(segment):
    record=deepcopy(segment['food_record']);spec=record['specification']
    amount=record['prices']['source_applied'] if 'supply_price' in record['field_sources'] else None
    price=amount is not None
    evidence=list(dict.fromkeys([segment['evidence_id']]+[eid for source in record['field_sources'].values() for eid in source.get('evidence_ids',[])]))
    unit=spec['unit'] if spec['quantity'] else {'개':'ea','EA':'ea','ea':'ea'}.get(spec['sales_unit'])
    return {'id':uid(),'kind':'price' if price else 'food_profile','product_name':record['food_name'],
        'company_name':record['company_name'],'spec':spec['original_text'],'amount':amount,
        'quantity':(spec['quantity'] or ('1' if unit else None)) if price else None,'unit':unit if price else None,
        'effective_from':None,'effective_to':None,'reason':None,'replacements':[],
        'price_basis':record['field_sources'].get('supply_price',{}).get('raw_value') and '원본 공급 가격 열',
        'uncertainties':[],'validation_warnings':record['issues'],'evidence_ids':evidence,
        'food_record':record,'extraction_origin':'parser'}


def _clean(event):
    event=deepcopy(event);record=from_event(event)
    record['company_name']=company_display(record.get('company_name'))
    # A comma-separated ingredient declaration is not a sales specification.
    raw=event.get('spec') or ''
    if '%' in raw and not record['specification'].get('quantity'):
        record['attributes']['ingredients']=record['attributes']['ingredients'] or ingredient_details(raw)
        record['specification'].update(original_text=None)
        event['spec']=None
        event.setdefault('validation_warnings',[]).append('규격으로 잘못 분류된 원재료를 속성으로 이동했습니다.')
    event['food_record']=record
    return upgrade_event(event)


def _compatible(source,target,allow_alias=False):
    a,b=source['food_record'],target['food_record']
    if a.get('food_code') and b.get('food_code') and a['food_code']!=b['food_code']:return False
    if a.get('company_name') and b.get('company_name') and canonical(a['company_name'])!=canonical(b['company_name']):return False
    an,bn=canonical(a['food_name']),canonical(b['food_name'])
    if an!=bn and not (allow_alias and len(an)>=3 and an in bn):return False
    if a['attributes']['flavor'] and b['attributes']['flavor'] and a['attributes']['flavor']!=b['attributes']['flavor']:return False
    sa,sb=a['specification'],b['specification']
    if sa['normalized_quantity'] and sb['normalized_quantity']:
        if (sa['normalized_quantity'],sa['normalized_unit'])!=(sb['normalized_quantity'],sb['normalized_unit']):return False
    elif sa['original_text'] and sb['original_text'] and canonical(sa['original_text'])!=canonical(sb['original_text']):return False
    for key in ('pack_count','piece_quantity','piece_unit','sales_unit'):
        if sa[key] and sb[key]:
            left,right=canonical(sa[key]),canonical(sb[key])
            if key=='sales_unit':left={'개':'ea','ea개':'ea'}.get(left,left);right={'개':'ea','ea개':'ea'}.get(right,right)
            if left!=right:return False
    if source['kind'] in ('food_profile','new_product'):
        return target['kind'] in ('food_profile','new_product','price')
    if source['kind']!=target['kind']:return False
    if (source.get('effective_from'),source.get('effective_to'))!=(target.get('effective_from'),target.get('effective_to')):return False
    if source['kind']=='price':
        if source.get('amount') is None:return False
        if source['amount']!=target.get('amount'):return False
        a_basis,b_basis=source.get('price_basis') or '',target.get('price_basis') or ''
        if any(word in a_basis+b_basis for word in ('행사','조사','회원','정상','배송','부가','도매','소매')) and canonical(a_basis)!=canonical(b_basis):return False
        if source.get('price_basis') and target.get('price_basis') and source.get('extraction_origin')==target.get('extraction_origin') and source['price_basis']!=target['price_basis']:return False
    return True


def _merge(target,source):
    # The structured row stays authoritative. Only empty fields are supplemented.
    before=target['food_record'];extra=source['food_record']
    merged=merge_profile(extra,before)
    for key in ('field_sources',):
        merged[key]=deepcopy(before[key])
        for field,origin in extra[key].items():
            if field not in merged[key]:merged[key][field]=deepcopy(origin)
            elif origin!=merged[key][field]:merged[key][field].setdefault('additional_sources',[]).append(deepcopy(origin))
    target['food_record']=merged
    target['evidence_ids']=list(dict.fromkeys(target.get('evidence_ids',[])+source.get('evidence_ids',[])))
    target.setdefault('source_event_ids',[]).extend([source['id']]+source.get('source_event_ids',[]))
    target['source_event_ids']=list(dict.fromkeys(target['source_event_ids']))
    for key in ('uncertainties','validation_warnings'):
        if key=='validation_warnings' and target.get('extraction_origin')=='parser':continue
        target[key]=list(dict.fromkeys(target.get(key,[])+source.get(key,[])))
    return upgrade_event(target)


def consolidate(events):
    """Merge only an unambiguous compatible identity; retain conflicting facts separately."""
    cleaned=[_clean(e) for e in events];kept=[];archive=[]
    # Rich structured rows are representatives; exact duplicates preserve all sources.
    ordered=sorted(cleaned,key=lambda e:(e.get('extraction_origin')!='parser',not bool(e.get('spec')),e['kind'] in ('food_profile','new_product')))
    companies={}
    for item in cleaned:
        company=item['food_record'].get('company_name')
        if company:companies.setdefault(canonical(item['product_name']),set()).add(canonical(company))
    for event in ordered:
        matches=[]
        for i,target in enumerate(kept):
            known=companies.get(canonical(event['product_name']),set())|companies.get(canonical(target['product_name']),set())
            if len(known)>1 and (not event['food_record'].get('company_name') or not target['food_record'].get('company_name')):continue
            if _compatible(event,target,allow_alias=target.get('extraction_origin')=='parser'):matches.append(i)
        if len(matches)==1:
            i=matches[0];archive.append({**event,'merged_into_event_id':kept[i]['id']});kept[i]=_merge(kept[i],event)
        elif event['kind']=='price' and event.get('amount') is None and event.get('excluded_reason'):
            # Invalid price assertions remain available in the audit, not as an empty pending item.
            archive.append(event)
        else:
            if len(matches)>1:event.setdefault('uncertainties',[]).append('같은 이름의 업체·규격 후보가 여럿 있어 자동 통합을 보류했습니다.')
            kept.append(event)
    return kept,archive
