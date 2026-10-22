"""
==============================================================================
FMS_FILE_SPEC
test_food_record.py - 기능·경계·회귀 검증
==============================================================================
설명:
    - 기능·경계·회귀 검증
입력·출력 명세:
    - 입력: 테스트 fixture·가상 입력·명시적 mock/테스트 대역
    - 출력: assert 결과와 실패 사유
실행 가정:
    - DB 통합 테스트는 별도 _test DB·임시 assets 사용; 대역과 실제 모델 검증을 구분
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

    2026-10-21  미지정      v0.1.0   원본 속성 누락 복구·재정리 API·검토 동선 개선

    2026-10-21  김재현(Finn) v0.1.0   Agent 도구 선택 기반 리빌드·업무 경계 및 검증

    2026-10-22  김재현(Finn) v0.1.0   자료·Agent·검수 승인·식품 DB 중심 흐름 및 알레르기 표기 정리

    2026-10-22  김재현(Finn) v0.1.0   원재료 전용 추출·함량 없는 표시사항 보존·OCR 근거 연결 검증

    상세 Git 이력: git log --follow -- backend/tests/test_food_record.py
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
import copy
import pytest
from backend.app.domains.catalog.record import *

def test_company_name_flavor_and_package_are_separate():
    original='CJ씨푸드 맛있는빅후랑크(오리지날_100g*10입 1Kg/EA)'
    record=from_event({'product_name':original,'spec':None})
    validate_record(record)
    assert record['food_name']=='맛있는빅후랑크' and record['company_name']=='CJ씨푸드'
    assert record['raw_food_name']==original and record['attributes']['flavor']=='오리지날'
    s=record['specification'];assert (s['piece_quantity'],s['piece_unit'],s['pack_count'],s['quantity'],s['normalized_unit'])==('100','g','10','1','kg')
    assert not {'manufacturer','brand','manufacturer_id','brand_id'} & record.keys()

def milk():
    header=['통식품코드','공통식품명','공통식품속성','규격수','규격','규격(kg.l)','단위','적용가','조사가1','조사가2','조사가3','비고','업체군','친환경구분']
    row=['4150250003','우유/소(小)','200ml/EA(개)/소(小)/식품표시기준:내용준수/우유급식용/국산원유100%,1등급',200,'ml','0.20l','EA(개)',0,1,0,0,None,None,None]
    return header,row

def test_common_food_columns_null_zero_allergy_provenance():
    header,row=milk();r=from_table_row(row,header_mapping(header),{'kind':'spreadsheet','sheet_name':'단가','cell_range':'A2:N2'});validate_record(r)
    assert r['food_code']=='4150250003' and r['food_name']=='우유'
    assert r['attributes']['ingredients'][0]['origin_country']=='KR' and r['attributes']['origin_country'] is None
    assert r['attributes']['quality_grade']=='1등급' and r['attributes']['intended_use']=='우유급식용'
    assert r['specification']['normalized_quantity']=='0.2' and r['specification']['normalized_unit']=='l'
    assert r['prices']=={'source_applied':'0','survey_1':'1','survey_2':'0','survey_3':'0','source_columns':None}
    assert r['company_name'] is None and r['allergens']['contains'] is None
    assert 'milk' in r['allergens']['candidates'] and r['allergens']['review_status']=='unknown'
    assert r['field_sources']['survey_1']['column_index']==8

def test_allergy_same_facility_and_unknown_are_separate():
    a=allergens_from_text('우유 함유;대두를 사용하는 같은 제조시설에서 생산')
    assert a['contains']==['milk'] and a['may_contain']==['soy']
    assert allergens_from_text(None)['contains'] is None
    assert allergens_from_text('우유 미함유')['contains'] is None

def test_merge_keeps_nullable_contract_and_known_values():
    a=empty_record();a['food_name']='테스트';a['company_name']='업체'
    assert merge_profile(None,a)==a
    b=empty_record();b['food_name']='수정'
    merged=merge_profile(a,b);validate_record(merged)
    assert merged['company_name']=='업체' and merged['food_name']=='수정'

def test_invalid_quantities_and_conflicting_allergy_fail():
    a=empty_record();a['specification']['pack_count']='1.5'
    with pytest.raises(Problem):validate_record(a)
    a=empty_record();a['allergens'].update(contains=['milk'],free_from_claims=['milk'])
    with pytest.raises(Problem):validate_record(a)

def test_csv_markdown_html_and_excel_rows_have_the_same_dto(tmp_path):
    import csv,io,openpyxl
    from backend.app.parsers.documents import parse
    header,row=milk();values=[str(v) if v is not None else '' for v in row]
    stream=io.StringIO();writer=csv.writer(stream);writer.writerow(header);writer.writerow(values)
    samples={'table.csv':stream.getvalue(),'table.md':'| '+' | '.join(header)+' |\n| '+' | '.join(['---']*len(header))+' |\n| '+' | '.join(values)+' |','table.html':'<table><tr>'+''.join('<th>'+h+'</th>' for h in header)+'</tr><tr>'+''.join('<td>'+v+'</td>' for v in values)+'</tr></table>'}
    records=[]
    for filename,body in samples.items():
        path=tmp_path/filename;path.write_text(body);parsed=parse(path,filename);records.append(next(s['food_record'] for s in parsed if s.get('food_record')))
    wb=openpyxl.Workbook();ws=wb.active;ws.append(header);ws.append(row);path=tmp_path/'table.xlsx';wb.save(path);records.append(next(s['food_record'] for s in parse(path,path.name) if s.get('food_record')))
    for record in records:
        validate_record(record);record['field_sources']={}
    assert all(r==records[0] for r in records)

def test_text_description_uses_the_same_nullable_contract():
    r=from_event({'product_name':'맛있는빅후랑크','company_name':'CJ씨푸드','spec':'100g*10입 1Kg/EA','attributes_text':'국산원유100%,1등급','allergen_text':'우유 함유','evidence_ids':['source']})
    validate_record(r)
    assert set(r)==set(empty_record()) and r['company_name']=='CJ씨푸드'
    assert r['specification']['pack_count']=='10' and r['allergens']['contains']==['milk']


def test_fish_sauce_attributes_preserve_ingredients_process_and_zero_prices():
    header=['공통식품코드','공통식품명','공통식품속성','규격수','규격','규격_x000D_\n(kg.l)','단위','적용가','조사가1','비고']
    raw='1300ml/통/식품표시기준:내용준수/국산생멸치75%,천일염25%,2년숙성'
    row=['4170030001','간장(어간장)',raw,1300,'ml','1.30l','통',0,22900,'바다천지']
    record=from_table_row(row,header_mapping(header),{'kind':'spreadsheet','sheet_name':'조사','cell_range':'A5:J5'})
    validate_record(record)
    assert [(i['name'],i['percentage'],i['origin_country']) for i in record['attributes']['ingredients']]==[('생멸치','75','KR'),('천일염','25',None)]
    assert record['attributes']['other']==['2년숙성']
    assert record['attributes']['original_text']==raw and record['attributes']['origin_country'] is None
    assert record['company_name'] is None and record['note']=='바다천지'
    assert record['prices']['survey_1']=='22900' and record['prices']['source_applied']=='0'
    assert record['specification']['normalized_quantity']=='1.3'
    assert record['field_sources']['normalized']['raw_value']=='1.30l'
    assert record['allergens']['contains'] is None


def test_ingredient_origin_brackets_and_generic_names_do_not_split_or_infer_allergens():
    raw='돼지고기(국산, 제주) 70%, 정제수 20%, 전분 10%'
    record=from_event({'product_name':'가공식품','attributes_text':raw})
    validate_record(record)
    assert len(record['attributes']['ingredients'])==3
    assert record['attributes']['ingredients'][0]['name']=='돼지고기(국산, 제주)'
    assert record['allergens']['candidates']==['pork'] and record['allergens']['contains'] is None


@pytest.mark.parametrize('raw,expected',[
    ('(5,6,12)',['soy','wheat','tomato']),
    ('(5,6,15,18)',['soy','wheat','chicken','shellfish']),
    ('5,6,15,18',['soy','wheat','chicken','shellfish']),
    ('알러지: 1,2,5,6,10,12,15,16',['egg','milk','soy','wheat','pork','tomato','chicken','beef']),
    ('알레르기 5.6.12',['soy','wheat','tomato']),
    ('같은 제조시설 알레르기: 5,6',['soy','wheat']),
])
def test_school_allergen_numbers_with_or_without_parentheses(raw,expected):
    from backend.app.domains.catalog.record import allergens_from_text
    result=allergens_from_text(raw)
    assert (result['may_contain'] if '시설' in raw else result['contains'])==expected
    assert result['original_text']==raw and result['review_status']=='source_declared'


@pytest.mark.parametrize('raw',['규격 (5,6,12)cm','사이즈 (5,6,12)','2026.10.22','(5,6,99)','1.92kg (60g*32EA)'])
def test_non_allergen_numeric_values_do_not_become_contains(raw):
    from backend.app.domains.catalog.record import allergens_from_text
    assert allergens_from_text(raw)['contains'] is None


def test_numeric_name_allergens_are_not_hidden_by_ingredient_attributes():
    record=from_event({'product_name':'혼합식품 (5,6,12)','attributes_text':'국산 원료 사용','spec':'1kg'})
    assert record['allergens']['contains']==['soy','wheat','tomato']
    assert '(5,6,12)' in record['allergens']['original_text']


def test_vendor_school_price_headers_keep_different_price_bases():
    headers=['품 목','개별중량','학교가\n(vat포함)\n규격가격','학교가\n(vat포함)\nkg가격','학교가\n(vat포함)\n개당가격','성분 및 함량','알러지 유발물질','알러지 유발물질 NO.']
    mapping=header_mapping(headers)
    record=from_table_row(['피자설기','60g',54100,None,1690,'쌀 54.22%',None,'5,6,12'],mapping,{'kind':'spreadsheet','cell_range':'A3:H3'},headers=headers)
    validate_record(record)
    assert record['food_name']=='피자설기' and record['specification']['quantity']=='60'
    assert record['prices']['source_applied'] is None
    assert [(p['basis'],p['amount']) for p in record['prices']['source_columns']]==[('package','54100'),('piece','1690')]
    assert all(p['tax_included'] for p in record['prices']['source_columns'])
    assert record['allergens']['contains']==['soy','wheat','tomato']


def test_legacy_food_price_dto_without_source_columns_remains_valid():
    record=empty_record();record['food_name']='기존 식품'
    record['prices'].pop('source_columns')
    validate_record(record)


@pytest.mark.parametrize('raw',[
    '원재료명: 밀가루, 설탕, 정제수\n보관방법: 냉동',
    '원재료명 및 함량\n밀가루, 설탕, 정제수\n알레르기: 밀 함유',
])
def test_labelled_ingredients_without_percentages(raw):
    record=from_event({'product_name':'빵','attributes_text':raw})
    validate_record(record)
    assert [i['name'] for i in record['attributes']['ingredients']]==['밀가루','설탕','정제수']
    assert all(i['percentage'] is None for i in record['attributes']['ingredients'])


def test_dedicated_ingredient_text_preserves_unquantified_and_foreign_origin():
    record=from_event({'product_name':'만두','ingredients_text':'밀가루(미국산) 30%, 대두유, 마늘','evidence_ids':['E1']})
    validate_record(record)
    assert [i['name'] for i in record['attributes']['ingredients']]==['밀가루(미국산)','대두유','마늘']
    assert record['attributes']['ingredients'][0]['origin_country'] is None
    assert record['field_sources']['ingredients']['evidence_ids']==['E1']


def test_storage_description_is_not_an_ingredient_declaration():
    record=from_event({'product_name':'빵','attributes_text':'냉장/냉동'})
    assert record['attributes']['ingredients'] is None
