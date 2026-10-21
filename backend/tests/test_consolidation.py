"""
==============================================================================
FMS_FILE_SPEC
test_consolidation.py - 기능·경계·회귀 검증
==============================================================================
설명:
    - 기능·경계·회귀 검증
입력·출력 명세:
    - 입력: 테스트 fixture·가상 입력·명시적 mock/테스트 대역
    - 출력: assert 결과와 실패 사유
실행 가정:
    - DB 통합 테스트는 별도 _test DB·임시 assets 사용; 대역과 실제 모델 검증을 구분
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
    2026-10-21  미지정      v0.1.0   파일 역할·입출력·가정·이력 명세 추가

    상세 Git 이력: git log --follow -- backend/tests/test_consolidation.py
    공통 규칙: doc/file-header-policy.md

기존 모듈 설명:
    Verify lossless, conservative merging of vendor tables and repeated OCR facts.
==============================================================================
"""

# FMS_MODULE_METADATA_BEGIN
__author__ = "미지정"
__email__ = "미지정"
__version__ = "0.1.0"
__status__ = "Development"
# FMS_MODULE_METADATA_END

# ---------------------------------------------------------------------------
# 1. Imports / Module implementation
# ---------------------------------------------------------------------------

from copy import deepcopy
from backend.app.domains.analysis.consolidation import enrich_tables,table_event,consolidate
from backend.app.domains.catalog.record import from_event,validate_record


def segments():
    texts=['㈜ 더자람 | | | | | | |','사진 | 상품명 | 맛&구별 | 규격 | 단위 | 학교가 | 영양성분 | 원재료',
        ' | 팥 찰보리빵 | 간편한 한 끼 | 25g | 개 | 720 | 열량 295kcal | 찰보리믹스 38%, 계란(국산) 20.9%, 물엿',
        ' | 크림치즈 케이크 | 소개 | 35g | 개 | 1600 | 열량 93kcal | 우유 24.89%, 계란, 쌀가루']
    return [{'text':text,'evidence_id':f'E{i}','asset_id':'sheet','locator':{'kind':'spreadsheet','sheet_name':'상품','cell_range':f'A{i+1}:H{i+1}'}} for i,text in enumerate(texts)]


def event(name='찰보리빵',spec='25g',kind='food_profile',amount=None,company='㈜ 더자람',id='ocr'):
    out={'id':id,'kind':kind,'product_name':name,'company_name':company,'spec':spec,'amount':amount,'quantity':None,'unit':None,'effective_from':None,'effective_to':None,'reason':None,'replacements':[],'price_basis':None,'uncertainties':[],'validation_warnings':[],'evidence_ids':[id]}
    out['food_record']=from_event(out)
    return out


def test_vendor_headers_connect_price_ingredients_company_and_cell_sources():
    original=segments();parsed=enrich_tables(original)
    assert not any(s.get('food_record') for s in original)
    rows=[table_event(s) for s in parsed if s.get('food_record')]
    assert len(rows)==2
    first,second=rows
    for row in rows:validate_record(row['food_record'])
    assert (first['product_name'],first['amount'],first['spec'])==('팥 찰보리빵','720','25g')
    assert first['food_record']['company_name']=='더자람'
    assert first['food_record']['specification']['piece_quantity']=='25'
    assert first['food_record']['specification']['sales_unit']=='개'
    assert first['food_record']['allergens']['candidates']==['egg']
    assert second['food_record']['allergens']['candidates']==['egg','milk']
    assert second['food_record']['allergens']['contains'] is None
    assert first['food_record']['attributes']['origin_country'] is None
    assert first['food_record']['field_sources']['supply_price']['column_index']==5
    assert first['food_record']['field_sources']['company_name']['evidence_ids']==['E0']


def test_profile_price_and_repeated_ocr_merge_without_extra_model_call():
    rows=[table_event(s) for s in enrich_tables(segments()) if s.get('food_record')]
    duplicate=event(kind='price',amount='720',spec=None)
    duplicate['validation_warnings']=['이전 추출의 금액 오류']
    bad=event(id='bad',spec='25g',kind='price');bad['excluded_reason']='금액 근거 미확인'
    profile=event(id='ingredients',spec='100% 찰보리')
    items,archive=consolidate(rows+[event(),duplicate,bad,profile])
    assert len(items)==2 and len(archive)==4
    first=next(e for e in items if e['product_name']=='팥 찰보리빵')
    assert first['amount']=='720' and first['food_record']['prices']['source_applied']=='720'
    assert '이전 추출의 금액 오류' not in first['validation_warnings']
    assert any('이전 추출의 금액 오류' in e.get('validation_warnings',[]) for e in archive)
    assert {'E0','E2','ocr','ingredients'}<=set(first['evidence_ids'])
    assert any(e['id']=='bad' and e['excluded_reason'] for e in archive)


def test_different_company_spec_price_and_period_are_not_collapsed():
    base=event(name='빵',kind='price',amount='720',company='업체A')
    inputs=[base]
    for key,value in [('company_name','업체B'),('spec','35g'),('amount','800'),('effective_from','2030-01-01')]:
        other=deepcopy(base);other['id']=key;other[key]=value
        if key in ('company_name','spec'):other.pop('food_record');other['food_record']=from_event(other)
        inputs.append(other)
    kept,archive=consolidate(inputs)
    assert len(kept)==5 and not archive


def test_unspecified_spec_stays_ambiguous_when_two_sizes_exist():
    kept,archive=consolidate([event(spec='25g',id='a'),event(spec='35g',id='b'),event(spec=None,id='c')])
    assert len(kept)==3 and not archive
    assert next(e for e in kept if e['id']=='c')['uncertainties']
