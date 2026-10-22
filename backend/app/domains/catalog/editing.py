"""
==============================================================================
FMS_FILE_SPEC
editing.py - 프로젝트 설정 editing.py
==============================================================================
설명:
    - 프로젝트 설정 editing.py
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

    2026-10-22  김재현(Finn) v0.1.0   자료·Agent·검수 승인·식품 DB 중심 흐름 및 알레르기 표기 정리

    상세 Git 이력: git log --follow -- backend/app/domains/catalog/editing.py
    공통 규칙: doc/file-header-policy.md

기존 모듈 설명:
    Manual canonical food edits with optimistic locking and an append-only audit.
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
from psycopg.types.json import Jsonb
from backend.app.infrastructure.database import Problem,entity,get,put,uid,now
from backend.app.api.http import match
from backend.app.domains.catalog.record import from_event,validate_record,specification
from backend.app.domains.ingestion.archives import state


def update_food(c,id,payload,request,actor):
    if not isinstance(payload,dict) or set(payload)!={'food_record','reason'}:
        raise Problem(422,'FOOD_EDIT_INPUT','식품 정보와 수정 사유를 입력하세요.')
    reason=payload['reason']
    if not isinstance(reason,str) or not 1<=len(reason.strip())<=1000:
        raise Problem(422,'FOOD_EDIT_REASON','수정 사유를 1~1000자로 입력하세요.')
    c.execute("SELECT pg_advisory_xact_lock(hashtext('food-catalog-apply'))")
    c.execute('SELECT pg_advisory_xact_lock(hashtext(%s))',(f'archive:food:{id}',))
    variant=entity(c,id,True)
    if variant.get('product_id') is None:raise Problem(422,'FOOD_TARGET','식품 규격을 선택하세요.')
    if state(c,'food',id)['archived']:raise Problem(409,'FOOD_ARCHIVED','삭제한 식품을 복구한 뒤 수정하세요.')
    profile=c.execute('SELECT data,version FROM food_profiles WHERE variant_id=%s FOR UPDATE',(id,)).fetchone()
    product=entity(c,variant['product_id'])
    version=profile['version'] if profile else variant['version']
    match(request,{'version':version})
    before=profile['data'] if profile else from_event({'product_name':product['name'],'spec':variant['spec_original']})
    record=deepcopy(payload['food_record']);validate_record(record)
    if not record['food_name'] or not record['food_name'].strip():raise Problem(422,'FOOD_NAME','식품명을 입력하세요.')
    if record['company_id']:
        company=get(c,'supplier',record['company_id'])
        if company['name']!=record['company_name']:raise Problem(422,'FOOD_COMPANY','업체명과 선택한 업체를 확인하세요.')
    spec=record['specification'];normalized=specification(spec['original_text'],spec['quantity'],spec['unit'],spec['sales_unit'])
    for key in ('normalized_quantity','normalized_unit'):spec[key]=normalized[key]
    # The caller may correct values, but cannot rewrite original provenance.
    record['field_sources']=deepcopy(before['field_sources'])
    changes=[]
    def compare(old,new,path=''):
        for key,value in new.items():
            if not path and key in ('field_sources','issues'):continue
            previous=old.get(key);field=path+'/'+key
            if isinstance(value,dict) and isinstance(previous,dict):compare(previous,value,field)
            elif previous!=value:changes.append(field)
    compare(before,record)
    for field in changes:
        old_source=record['field_sources'].get(field,{})
        record['field_sources'][field]={**old_source,'origin':'manual','actor_id':actor,'recorded_at':now(),'reason':reason.strip()}
    validate_record(record)
    version+=1
    c.execute("UPDATE catalog_entities SET version=version+1,data=jsonb_set(data,'{version}',to_jsonb(version+1)) WHERE id=%s",(id,))
    c.execute('INSERT INTO food_profiles(variant_id,product_id,food_code,schema_version,version,data) VALUES(%s,%s,%s,%s,%s,%s) ON CONFLICT(variant_id) DO UPDATE SET food_code=excluded.food_code,schema_version=excluded.schema_version,version=excluded.version,data=excluded.data,updated_at=now()', (id,variant['product_id'],record['food_code'],record['schema_version'],version,Jsonb(record)))
    audit=put(c,'audit',{'id':uid(),'application_id':None,'proposal_id':None,'product_id':variant['product_id'],'kind':'edit_food_profile','entity_id':id,'before':before,'after':{**record,'id':id,'version':version},'evidence_ids':variant.get('evidence_ids',[]),'actor':actor,'recorded_at':now(),'reason':reason.strip(),'changed_fields':changes,'period':None})
    return {'id':id,'product_id':variant['product_id'],'version':version,'food_record':record,'evidence_ids':variant.get('evidence_ids',[]),'archived':False,'archive_version':state(c,'food',id)['archive_version'],'status':product['status'],'has_stored_profile':True,'audit_event_id':audit['id']}
