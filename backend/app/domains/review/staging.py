"""
==============================================================================
FMS_FILE_SPEC
staging.py - 프로젝트 설정 staging.py
==============================================================================
설명:
    - 프로젝트 설정 staging.py
입력·출력 명세:
    - 입력: 도구별 설정·실행 환경
    - 출력: 해당 도구의 구성 또는 실행 결과
실행 가정:
    - 실제 비밀값과 로컬 실행 데이터는 Git에서 제외
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

    2026-10-21  김재현(Finn) v0.1.0   Agent 도구 선택 기반 리빌드·업무 경계 및 검증

    상세 Git 이력: git log --follow -- backend/app/domains/review/staging.py
    공통 규칙: doc/file-header-policy.md

기존 모듈 설명:
    Build approval drafts from explicitly confirmed DTOs; never called by extraction.
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

from contextlib import nullcontext
from decimal import Decimal
import re
from backend.app.infrastructure.database import Problem,entities,get,put,tx,uid
from backend.app.infrastructure.contracts import schema_check
from backend.app.domains.review.proposals import create
from backend.app.domains.analysis.consolidation import canonical

def stage_confirmed(state,connection):
    if not state.get('review_mode'):raise Problem(403,'REVIEW_REQUIRED','검토를 완료한 품목만 변경안으로 준비할 수 있습니다.')
    with (nullcontext(connection) if connection is not None else tx()) as c:
        report=get(c,'agent_report',state['agent_report_id'],True);r=get(c,'revision',state['revision_id']);doc=get(c,'document',r['document_id'])
        if report['proposal_ids']:return {'proposal_ids':report['proposal_ids']}
        products=entities(c,'product');variants=entities(c,'variant');items=entities(c,'supplier_item')
        supplier=None;base_supplier=None
        bundles=[];pending=[];pending_events=[];local_products={};local_variants={};local_items={}
        def finish():
            nonlocal pending,pending_events,local_products,local_variants,local_items
            if not pending:return
            title=r['title']+f' · 확인한 식품 반영 {len(bundles)+1}'
            schema_check('ProposalCreate',{'title':title,'source_document_revision_ids':[r['id']],'changes':pending})
            p=create(c,title,[r['id']],pending,state['run_id']);bundles.append(p['summary']['id'])
            for event in pending_events:event['proposal_id']=p['summary']['id']
            pending=[];pending_events=[];local_products={};local_variants={};local_items={}
        for event in report['events']:
            item=None
            if state.get('review_mode') and event.get('review',{}).get('status')!='confirmed':event['proposal_id']=None;continue
            from backend.app.domains.catalog.record import from_event
            record=from_event(event);event['food_record']=record
            name=record['food_name'] or event['product_name'];event['product_name']=name
            event['review_reasons']=list(dict.fromkeys(event['uncertainties']+event['validation_warnings']));event['match_status']='unresolved';event['proposal_id']=None
            if event.get('excluded_reason'):event['review_reasons'].append(event['excluded_reason']);continue
            if not name:event['review_reasons'].append('원문의 품목을 특정할 수 없습니다.');continue
            if len(pending)>43:finish()
            if event.get('review',{}).get('fields',{}).get('supplier_id'):supplier=get(c,'supplier',event['review']['fields']['supplier_id'])
            elif record.get('company_id'):supplier=get(c,'supplier',record['company_id'])
            elif record.get('company_name'):
                found=c.execute("SELECT data FROM app_records WHERE kind='supplier' AND data->>'name'=%s LIMIT 1",(record['company_name'],)).fetchone();supplier=found['data'] if found else None
            else:supplier=base_supplier
            if supplier and not record.get('company_name'):record.update(company_id=supplier['id'],company_name=supplier['name'])
            selected_product=event.get('review',{}).get('fields',{}).get('product_id')
            exact=[p for p in products if p['id']==selected_product] if selected_product else ([p for p in products if p.get('common_food_code')==record['food_code']] if record.get('food_code') else [p for p in products if canonical(p['name'])==canonical(name) and p.get('record_type','commercial_product')=='commercial_product'])
            if len(exact)>1:event['review_reasons'].append('같은 이름의 제품이 여럿 있어 자동 연결을 보류했습니다.');continue
            ops=[];product=exact[0] if exact else None;pkey='common:'+record['food_code'] if record.get('food_code') else canonical(name)
            if product:pref={'id':product['id']};event['match_status']='exact_product';event['matched_product_id']=product['id']
            elif pkey in local_products:pref={'local_ref':local_products[pkey]}
            else:
                ref='p'+str(len(local_products));local_products[pkey]=ref;pref={'local_ref':ref};ops.append({'kind':'create_product','local_ref':ref,'name':name,'manufacturer_id':None,'brand_id':None,**({'record_type':'common_food','common_food_code':record['food_code']} if record.get('food_code') else {})});event['match_status']='new_product'
            spec=event['spec'] or '규격 미기재 · 검토 필요'
            if not event['spec']:event['review_reasons'].append('규격이 원문에 명확하지 않습니다.')
            normalized_spec=('common:'+record['food_code']+':'+canonical(spec)) if record.get('food_code') else spec
            vfound=[v for v in variants if product and v['product_id']==product['id'] and (v['spec_normalized']==normalized_spec or (not record.get('food_code') and canonical(v['spec_original'])==canonical(spec)))]
            vkey=(pkey,canonical(spec));variant=vfound[0] if len(vfound)==1 else None
            if variant:vref={'id':variant['id']}
            elif vkey in local_variants:vref={'local_ref':local_variants[vkey]}
            else:
                ref='v'+str(len(local_variants));local_variants[vkey]=ref;vref={'local_ref':ref};ops.append({'kind':'create_variant','local_ref':ref,'product_ref':pref,'spec_original':spec,'spec_normalized':normalized_spec,'barcode':None})
            ops.append({'kind':'set_food_profile','variant_ref':vref,'profile':record,'clear_fields':event.get('review',{}).get('cleared_profile_fields',[])})
            if event['kind'] in ('food_profile','new_product'):
                for op in ops:pending.append({'id':uid(),'operation':op,'field_evidence':[{'field_path':'/'+k,'evidence_ids':event['evidence_ids'],'origin':'reviewer' if state.get('review_mode') else 'extracted',**({'reviewer_justification':event['review']['reason']} if state.get('review_mode') else {})} for k in op if k not in ('kind','local_ref','supersedes_fact_id','manufacturer_id','brand_id','barcode','supplier_code')]})
                pending_events.append(event);continue
            if event['kind']=='discontinued':
                target_kind='set_product_status';target={'product_ref':pref};value={'status':'discontinued'}
            else:
                found=[x for x in items if variant and x['variant_id']==variant['id'] and (not supplier or x['supplier_id']==supplier['id'])]
                item=found[0] if len(found)==1 else None
                if item:iref={'id':item['id']};event['matched_supplier_item_id']=item['id'];event['match_status']='exact_supplier_item'
                elif supplier:
                    ikey=(vkey,supplier['id'])
                    if ikey in local_items:iref={'local_ref':local_items[ikey]}
                    else:
                        ref='i'+str(len(local_items));local_items[ikey]=ref;iref={'local_ref':ref};ops.append({'kind':'create_supplier_item','local_ref':ref,'variant_ref':vref,'supplier_id':supplier['id'],'supplier_code':None,'sales_unit':event['unit'] or event['spec'] or '규격 확인 필요'})
                    if supplier.get('verification_status')=='publisher_candidate':event['review_reasons'].append(f"게시자 ‘{author}’를 공급처 후보로 연결했습니다. 실제 공급처인지 확인하세요.")
                else:event['review_reasons'].append('실제 공급처를 확인할 수 없습니다.');iref=None
                if event['kind']=='price' and event['amount'] is not None and iref:
                    unit=event['unit'] or 'ea';quantity=event['quantity'] or '1'
                    try:
                        assert re.fullmatch(r'\d{1,16}(?:\.\d{1,4})?',quantity);q=Decimal(quantity);assert q.is_finite() and q>0;quantity=format(q,'f')
                    except Exception:quantity='1';event['review_reasons'].append('가격 기준 수량을 확인하세요.')
                    if event['unit'] is None:event['review_reasons'].append('가격 기준 단위 미기재: 임시로 1개 기준을 제안했습니다.')
                    target_kind='set_price';target={'supplier_item_ref':iref};value={'value':{'amount':event['amount'],'currency':'KRW','quantity':quantity,'unit':unit,'tax':'unknown','price_kind':'unknown','condition_key':'public'}}
                    if event.get('price_basis') and any(x in event['price_basis'] for x in ['조사','비교','참고']):event['review_reasons'].append('조사·참고 가격을 실제 공급 단가로 반영할지 확인하세요.')
                elif event['kind'] in ('temporarily_unavailable','supply_ended','available') and iref:target_kind='set_availability';target={'supplier_item_ref':iref};value={'status':event['kind']}
                else:
                    if event['kind']=='substitution':event['review_reasons'].append('대체품 후보의 조합·선택 관계를 확인해야 합니다.')
                    target_kind=None
            if event['effective_from']:start=event['effective_from']
            else:
                start=(r['published_at'] or r['collected_at'])[:10];event['review_reasons'].append(f'적용일 미기재: {start}을 검토용 임시 날짜로 제안했습니다.')
            if target_kind:
                op={'kind':target_kind,**target,**value,'period':{'effective_from':start,'effective_to':event['effective_to']},'reason':{'original_text':event['reason'],'summary':event['reason'],'code':None},'supersedes_fact_id':None}
                if item and event['kind']!='discontinued':
                    previous=c.execute("SELECT id FROM facts WHERE target_id=%s AND kind=%s AND condition_key=%s AND (effective_to IS NULL OR effective_to>%s::date)",(item['id'],target_kind,'public' if target_kind=='set_price' else '',start)).fetchall()
                    if len(previous)==1:op['supersedes_fact_id']=str(previous[0]['id']);event['review_reasons'].append('기존 사실의 적용 기간을 정정하는 변경안입니다.')
                ops.append(op)
            for op in ops:
                pending.append({'id':uid(),'operation':op,'field_evidence':[{'field_path':'/'+k,'evidence_ids':event['evidence_ids'],'origin':'reviewer' if state.get('review_mode') else 'extracted',**({'reviewer_justification':event['review']['reason']} if state.get('review_mode') else {})} for k in op if k not in ('kind','local_ref','supersedes_fact_id','manufacturer_id','brand_id','barcode','supplier_code')]})
            if ops:pending_events.append(event)
        finish();report['proposal_ids']=bundles;report['status']='exporting';put(c,'agent_report',report)
        # Revalidate now that confirmation reasons and proposal bindings are persisted.
        from backend.app.domains.review.proposals import validate
        for pid in bundles:
            p=get(c,'proposal',pid);validate(c,p);put(c,'proposal',p)
        run=get(c,'analysis_run',state['run_id'],True);run['proposal_id']=bundles[0] if bundles else None;run['proposal_ids']=bundles;put(c,'analysis_run',run)
        doc['analysis_status']='completed';doc['proposal_count']+=len(bundles);put(c,'document',doc)
    return {'proposal_ids':bundles}
