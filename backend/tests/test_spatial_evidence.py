"""
==============================================================================
FMS_FILE_SPEC
test_spatial_evidence.py - 기능·경계·회귀 검증
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
    - 작성일: 2026-10-22 (최초 Git 등록일 기준)
    - 라이선스: 미지정
    - 버전: 0.1.0
    - 상태: Development
변경 이력 (Revision History):
    DATE        AUTHOR      VERSION  DESCRIPTION
    --------------------------------------------------------------------
    2026-10-22  미지정      v0.1.0   파일 역할·입출력·가정·이력 명세 추가

    상세 Git 이력: git log --follow -- backend/tests/test_spatial_evidence.py
    공통 규칙: doc/file-header-policy.md

기존 모듈 설명:
    Adversarial OCR ownership, coordinate and field-reference regressions.
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

import asyncio
from copy import deepcopy
import pytest
from backend.app.domains.analysis.agent import model_mapping,extraction_payload
from backend.app.domains.analysis.planning import image_regions,group_references,restore_groups
from backend.app.domains.analysis.spatial import ground_fields
from backend.app.domains.catalog.record import from_event
from backend.app.infrastructure.database import Problem


def line(text,id,box,role='product'):
    return {'text':text,'evidence_id':id,'region_label':'상품A','source_role':role,'locator':{'kind':'image','page_number':1,'bbox':box}}


def test_shared_allergen_legend_cannot_become_product_declaration():
    mapping=model_mapping([line('상품 A','A',[0,.1,.4,.2]),line('알레르기 범례: 우유 함유','L',[0,.8,1,.9],'context')])
    event={'product_name':'상품 A','allergen_text':'우유 함유','field_evidence':[{'field':'allergen_text','source_ids':['S2']} ]}
    manual=ground_fields(event,mapping)
    assert event['allergen_text'] is None and set(manual)=={'A','L'}
    assert from_event(event)['allergens']['contains'] is None


def test_exact_field_sources_preserve_boxes_and_split_declarations():
    mapping=model_mapping([line('설탕','I2',[.1,.3,.4,.4]),line('우유,','I1',[.1,.2,.4,.3]),line('우유 함유','A',[.1,.4,.4,.5])])
    event={'ingredients_text':'우유, 설탕','allergen_text':'우유 함유','field_evidence':[{'field':'ingredients_text','source_ids':['S1','S2']},{'field':'allergen_text','source_ids':['S3']}]}
    assert ground_fields(event,mapping)==[]
    record=from_event(event)
    assert record['field_sources']['ingredients']['evidence_ids']==['I1','I2']
    assert record['field_sources']['allergens']['evidence_ids']==['A']
    assert record['field_sources']['allergens']['locators'][0]['bbox']==[.1,.4,.4,.5]
    assert [x['name'] for x in record['attributes']['ingredients']]==['우유','설탕']
    payload=extraction_payload({'title':'식품'},'marketing',mapping)
    assert payload['segments'][0]['bbox']==[100,200,400,300]


def test_field_reference_to_a_different_regions_line_is_rejected():
    mapping=model_mapping([line('상품 A 원재료: 정제수','A',[0,0,.4,.2])])
    event={'ingredients_text':'정제수','field_evidence':[{'field':'ingredients_text','source_ids':['S99']}]}
    assert ground_fields(event,mapping)==['A']
    assert event['ingredients_text'] is None


def test_nearby_products_cannot_share_owned_lines_as_context_and_resume_roles():
    rows=[line('상품A 우유 함유','A',[0,0,.4,.2]),line('상품B 대두 함유','B',[.5,0,.9,.2]),line('업체: 공통업체','C',[0,.8,1,.9])]
    source={'location':{'kind':'image','page_number':1},'segments':rows}
    async def call(task,payload,schema):
        assert payload['lines'][0][2]=='상품A 우유 함유'
        return {'regions':[{'label':'A','source_ids':['1'],'context_ids':['2','3']},{'label':'B','source_ids':['2'],'context_ids':['3']}],'unassigned_ids':[]}
    groups,manual,result=asyncio.run(image_regions(source,call))
    assert not manual
    assert [s['evidence_id'] for s in groups[0]]==['A','C']
    assert [s['source_role'] for s in groups[0]]==['product','context']
    restored=restore_groups(group_references(groups),rows)
    assert [s['source_role'] for s in restored[0]]==['product','context']
    event={'product_name':'상품A','allergen_text':'대두 함유'}
    assert ground_fields(event,model_mapping(restored[0]))
    assert event['allergen_text'] is None


def test_layout_keeps_text_beyond_sixteen_characters():
    text='이 상품은 같은 제품명으로 시작하지만 끝에 표시된 상품B'
    source={'location':{'kind':'image'},'segments':[line(text,'A',[0,0,1,.1])]}
    async def call(task,payload,schema):
        assert payload['lines'][0][2]==text
        return {'regions':[{'label':'B','source_ids':['1'],'context_ids':[]}],'unassigned_ids':[]}
    assert asyncio.run(image_regions(source,call))[0][0][0]['text']==text


def test_layout_budget_does_not_silently_cut_product_text():
    source={'location':{'kind':'image'},'segments':[line('원재료'*3000,'A',[0,0,1,1])]}
    async def call(*args):pytest.fail('초과 입력은 잘라 추론하면 안 됩니다.')
    with pytest.raises(Problem) as error:asyncio.run(image_regions(source,call))
    assert error.value.code=='IMAGE_LAYOUT_BUDGET'


def test_old_checkpoints_recover_roles_from_saved_layout_without_new_inference():
    rows=[{**line('상품A','A',[0,0,.4,.2]),'asset_id':'image'},{**line('공통 안내','C',[0,.8,1,.9]),'asset_id':'image'}]
    refs=[[{'evidence_id':'A','region_label':'상품A'},{'evidence_id':'C','region_label':'상품A'}]]
    traces=[{'source_id':'D1','layout':{'regions':[{'label':'상품A','source_ids':['1'],'context_ids':['2']}]}}]
    restored=restore_groups(refs,rows,traces)
    assert [s['source_role'] for s in restored[0]]==['product','context']
    assert all(s['source_role']=='context' for s in restore_groups(refs,rows)[0])



def test_text_tool_on_ocr_source_still_receives_coordinates():
    row=line('본문 OCR','E1',[.2,.3,.4,.5]);row.pop('region_label')
    payload=extraction_payload({'title':'공지'},'notice',model_mapping([row]))
    assert payload['segments'][0]['bbox']==[200,300,400,500]
