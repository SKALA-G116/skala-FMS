"""
==============================================================================
FMS_FILE_SPEC
seed.py - 가상 예제·초기 계정 명시적 생성
==============================================================================
설명:
    - 가상 예제·초기 계정 명시적 생성
입력·출력 명세:
    - 입력: 초기 비밀번호·빈 개발 DB
    - 출력: 가상 식품·단가·계정·예제 작업
실행 가정:
    - API 시작 시 자동 실행하지 않고 기존 사용자가 있으면 덮어쓰지 않음
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

    상세 Git 이력: git log --follow -- backend/app/seed.py
    공통 규칙: doc/file-header-policy.md

기존 모듈 설명:
    Explicit local demo seed. Never run automatically on API startup.
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

import os
from argon2 import PasswordHasher
from psycopg.types.json import Jsonb
from backend.app.infrastructure.database import init
from backend.app.infrastructure.database import now
from backend.app.infrastructure.database import pool
from backend.app.infrastructure.database import put
from backend.app.infrastructure.database import records
from backend.app.infrastructure.database import save_entity
from backend.app.infrastructure.database import tx
from backend.app.infrastructure.database import uid
from backend.app.domains.ingestion.documents import import_document
from backend.app.domains.jobs.service import enqueue

def seed():
    init()
    with tx() as c:
        if records(c,'user'):print('기존 데이터가 있어 시드를 건너뜁니다.');return
        password=os.getenv('FOOD_SEED_PASSWORD','local-food-2026')
        for username,role,name in [('admin','admin','관리자'),('reviewer','reviewer','검토 담당자'),('operator','operator','수집 담당자'),('reader','reader','조회 담당자')]:
            put(c,'user',{'id':uid(),'username':username,'display_name':name,'roles':[role],'password_hash':PasswordHasher().hash(password)})
        supplier=put(c,'supplier',{'id':uid(),'name':'예제푸드 (가상 업체)','roles':['supplier','manufacturer'],'aliases':[]})
        source=put(c,'source',{'id':uid(),'name':'학교급식 식품 공지','base_url':'https://school062.com','enabled':False,'version':1,'boards':[{'key':b,'name':n,'enabled':True} for b,n in [('product_01','제품 공지'),('product_02','단가표'),('product_del','중단·대체 공지')]],'last_collected_at':None})
        sample=import_document(c,'[예제] 초기 단가표 · 실제 거래에 사용하지 마세요',b'DEMO seed data - not real food pricing.','demo-reference.txt')
        ev=put(c,'evidence',{'id':uid(),'document_revision_id':sample['revision']['id'],'source_url':None,'quote':'가상 예제: 초기 상품과 단가표입니다. 실제 게시글이나 거래 정보가 아닙니다.','locator':{'kind':'html','block_id':'demo-seed','start_offset':0,'end_offset':44},'extraction_id':None,'ocr_confidence':None,'created_at':now()})
        for name,spec,code,amount in [('바삭한 순살 생선까스','40–50g / 1kg','DEMO-001','12800'),('국산 두부 스테이크','60g × 20개','DEMO-002','16500'),('우리밀 미니 핫도그','50g × 20개','DEMO-003','18900')]:
            p=save_entity(c,'product',{'id':uid(),'name':name,'manufacturer':supplier,'brand':None,'status':'active','version':1,'created_at':now(),'evidence_ids':[ev['id']]})
            v=save_entity(c,'variant',{'id':uid(),'product_id':p['id'],'spec_original':spec,'spec_normalized':spec,'barcode':None,'version':1,'evidence_ids':[ev['id']]},p['id'])
            item=save_entity(c,'supplier_item',{'id':uid(),'variant_id':v['id'],'supplier_id':supplier['id'],'supplier_code':code,'sales_unit':'kg','version':1,'evidence_ids':[ev['id']]},v['id'],supplier['id'])
            value={'amount':amount,'currency':'KRW','quantity':'1','unit':'kg','tax':'unknown','price_kind':'regular','condition_key':'public'}
            fact={'id':uid(),'kind':'set_price','value':value,'period':{'effective_from':'2026-01-01','effective_to':None},'reason':{'original_text':'가상 예제 초기 단가','summary':'가상 예제','code':None},'supersedes_fact_id':None,'evidence_ids':[ev['id']]}
            c.execute('INSERT INTO facts(id,kind,target_id,condition_key,amount,effective_from,data) VALUES(%s,%s,%s,%s,%s,%s,%s)',(fact['id'],'set_price',item['id'],'public',amount,'2026-01-01',Jsonb(fact)))
            put(c,'audit',{'id':uid(),'application_id':None,'proposal_id':None,'product_id':p['id'],'kind':'create_product','entity_id':p['id'],'before':None,'after':p,'evidence_ids':[ev['id']],'actor':'demo-seed','recorded_at':now(),'period':None})
        text='[가상 예제 공지] 원료 수급에 따른 일시중단\nitem DEMO-001 | 공급 일시중단 | 2026-11-01 | 원료 수급 불안정. 재개일 미정.\n'
        result=import_document(c,'[예제] 생선까스 공급 일시중단 안내',text.encode(),'demo-notice.txt')
        run=put(c,'analysis_run',{'id':uid(),'document_revision_id':result['revision']['id'],'workflow_profile':'notice','status':'queued','created_at':now(),'mode':'rules'})
        job=enqueue(c,'analyze',{'document_revision_id':result['revision']['id'],'workflow_profile':'notice'},run['id']);run['job_id']=job['id'];put(c,'analysis_run',run)
    print('가상 예제 데이터와 계정을 생성했습니다. 로그인: admin / 설정한 FOOD_SEED_PASSWORD (기본값은 실행 안내 참조)')

if __name__=='__main__':
    try:seed()
    finally:pool.close()
