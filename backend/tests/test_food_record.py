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
    assert r['prices']=={'source_applied':'0','survey_1':'1','survey_2':'0','survey_3':'0'}
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
