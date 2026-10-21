from copy import deepcopy
from psycopg.types.json import Jsonb
from backend.app.infrastructure.database import Problem
from backend.app.infrastructure.database import entities
from backend.app.infrastructure.database import entity
from backend.app.infrastructure.database import get
from backend.app.infrastructure.database import now
from backend.app.infrastructure.database import put
from backend.app.infrastructure.database import save_entity
from backend.app.infrastructure.database import uid

def apply(c,app,actor):
    p=get(c,'proposal',app['proposal_id'],True)
    if app['status']=='applied': return app
    if p['summary']['status']!='applying' or p['summary']['approved_revision']!=app['approved_revision']:raise Problem(409,'APPROVAL_CHANGED','승인 상태가 변경되었습니다.')
    # All applications take one advisory transaction lock: no overlapping write can bypass version/period checks.
    c.execute("SELECT pg_advisory_xact_lock(hashtext('food-catalog-apply'))")
    for t in sorted(p['target_versions'],key=lambda t:t['entity_id']):
        if entity(c,t['entity_id'],True)['version']!=t['version']:raise Problem(409,'TARGET_CHANGED','검토 이후 상품이 변경되었습니다. 다시 검토하세요.')
    for rid in p['source_document_revision_ids']:
        r=get(c,'revision',rid)
        if get(c,'document',r['document_id'])['latest_revision_id']!=rid:raise Problem(409,'SOURCE_CHANGED','원문이 수정되어 다시 검토해야 합니다.')
    refs={};touched=set();events=[]
    def resolve(ref):return ref.get('id') or refs[ref['local_ref']]
    for change in p['changes']:
        op=change['operation'];kind=op['kind'];eid=uid();before=None
        evidence=list({e for f in change['field_evidence'] for e in f['evidence_ids']})
        if kind=='create_product':
            obj={'id':eid,'name':op['name'],'manufacturer':get(c,'supplier',op['manufacturer_id']) if op['manufacturer_id'] else None,'brand':get(c,'supplier',op['brand_id']) if op['brand_id'] else None,'status':'active','version':1,'created_at':now(),'evidence_ids':evidence,'record_type':op.get('record_type','commercial_product'),'common_food_code':op.get('common_food_code')}
            if any((x.get('common_food_code')==obj['common_food_code'] if obj['common_food_code'] and obj['record_type']=='common_food' else x['name'].casefold()==obj['name'].casefold() and x['manufacturer']==obj['manufacturer'] and x.get('record_type','commercial_product')==obj['record_type']) for x in entities(c,'product')):raise Problem(409,'DUPLICATE_PRODUCT','같은 상품이 이미 있습니다. 기존 상품에 연결하세요.')
            save_entity(c,'product',obj);refs[op['local_ref']]=eid;product_id=eid
        elif kind=='create_variant':
            parent=resolve(op['product_ref']);product_id=parent
            if any(x['product_id']==parent and x['spec_normalized']==op['spec_normalized'] for x in entities(c,'variant')):raise Problem(409,'DUPLICATE_VARIANT','같은 규격이 이미 있습니다.')
            obj={'id':eid,'product_id':parent,'spec_original':op['spec_original'],'spec_normalized':op['spec_normalized'],'barcode':op['barcode'],'version':1,'evidence_ids':evidence};save_entity(c,'variant',obj,parent);refs[op['local_ref']]=eid
        elif kind=='create_supplier_item':
            parent=resolve(op['variant_ref']);product_id=entity(c,parent)['product_id']
            if any(x['variant_id']==parent and x['supplier_id']==op['supplier_id'] and x['sales_unit']==op['sales_unit'] for x in entities(c,'supplier_item')):raise Problem(409,'DUPLICATE_ITEM','같은 공급 상품이 이미 있습니다.')
            obj={'id':eid,'variant_id':parent,'supplier_id':op['supplier_id'],'supplier_code':op['supplier_code'],'sales_unit':op['sales_unit'],'version':1,'evidence_ids':evidence};save_entity(c,'supplier_item',obj,parent,op['supplier_id']);refs[op['local_ref']]=eid
        elif kind=='set_food_profile':
            from backend.app.domains.catalog.record import validate_record; from backend.app.domains.catalog.record import merge_profile
            variant_id=resolve(op['variant_ref']);variant=entity(c,variant_id);product_id=variant['product_id']
            from backend.app.domains.ingestion.archives import state
            if state(c,'food',variant_id)['archived']:raise Problem(409,'FOOD_ARCHIVED','삭제된 식품입니다. 목록에서 복구한 뒤 수정해 주세요.')
            existing=c.execute('SELECT data,version FROM food_profiles WHERE variant_id=%s FOR UPDATE',(variant_id,)).fetchone()
            before=existing['data'] if existing else None;merged=merge_profile(before,op['profile'])
            for path in op['clear_fields']:
                keys=path.strip('/').split('/');objref=merged
                try:
                    for key in keys[:-1]:objref=objref[key]
                    if keys[-1] not in objref:raise KeyError()
                    objref[keys[-1]]=None
                except (KeyError,TypeError):raise Problem(422,'PROFILE_PATH','식품 정보의 수정 경로가 올바르지 않습니다.')
            validate_record(merged)
            version=existing['version']+1 if existing else 1
            c.execute('INSERT INTO food_profiles(variant_id,product_id,food_code,schema_version,version,data) VALUES(%s,%s,%s,%s,%s,%s) ON CONFLICT(variant_id) DO UPDATE SET food_code=excluded.food_code,schema_version=excluded.schema_version,version=excluded.version,data=excluded.data,updated_at=now()', (variant_id,product_id,merged['food_code'],merged['schema_version'],version,Jsonb(merged)))
            obj={**merged,'id':variant_id,'version':version};touched.add(variant_id)
        else:
            target=resolve(op.get('supplier_item_ref') or op.get('product_ref') or op['original_supplier_item_ref']);before=entity(c,target)
            product_id=target if kind=='set_product_status' else entity(c,before['variant_id'])['product_id']
            if kind!='set_product_status':
                from backend.app.domains.ingestion.archives import state
                if state(c,'food',before['variant_id'])['archived']:raise Problem(409,'FOOD_ARCHIVED','삭제된 식품입니다. 복구한 뒤 반영해 주세요.')
            condition=op.get('value',{}).get('condition_key','');period=op['period'];sup=op.get('supersedes_fact_id')
            overlaps=c.execute("SELECT id FROM facts WHERE target_id=%s AND kind=%s AND condition_key=%s AND daterange(effective_from,effective_to,'[)') && daterange(%s::date,%s::date,'[)')",(target,kind,condition,period['effective_from'],period['effective_to'])).fetchall()
            if overlaps:
                if not sup or not any(str(x['id'])==sup for x in overlaps):raise Problem(409,'PERIOD_CONFLICT','같은 기간의 사실이 있습니다. 정정할 기존 사실 ID를 지정하세요.')
                ancestors=set();cursor=sup
                while cursor:
                    if cursor in ancestors:raise Problem(409,'CORRECTION_CYCLE','잘못된 정정 연결입니다.')
                    ancestors.add(cursor);r=c.execute('SELECT supersedes_fact_id FROM facts WHERE id=%s AND target_id=%s AND kind=%s AND condition_key=%s',(cursor,target,kind,condition)).fetchone()
                    if not r:raise Problem(409,'INVALID_CORRECTION','정정 대상이 일치하지 않습니다.')
                    cursor=str(r['supersedes_fact_id']) if r['supersedes_fact_id'] else None
                if any(str(x['id']) not in ancestors for x in overlaps):raise Problem(409,'PERIOD_CONFLICT','다른 변경 사실과 기간이 겹칩니다.')
            elif sup:raise Problem(409,'INVALID_CORRECTION','정정 대상과 적용 기간이 겹치지 않습니다.')
            obj={**deepcopy(op),'id':eid,'evidence_ids':evidence}
            if kind=='set_substitution':
                for group in obj['groups']:
                    for member in group['members']:
                        member['supplier_item_ref']={'id':resolve(member['supplier_item_ref'])}
            c.execute('INSERT INTO facts(id,kind,target_id,condition_key,amount,effective_from,effective_to,supersedes_fact_id,data) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)',(eid,kind,target,condition,op.get('value',{}).get('amount'),period['effective_from'],period['effective_to'],sup,Jsonb(obj)))
            touched.add(target)
        events.append(put(c,'audit',{'id':uid(),'application_id':app['id'],'proposal_id':app['proposal_id'],'product_id':product_id,'kind':kind,'entity_id':obj['id'],'before':before,'after':obj,'evidence_ids':evidence,'actor':actor,'recorded_at':now(),'period':op.get('period')}))
    for target in touched:
        c.execute("UPDATE catalog_entities SET version=version+1, data=jsonb_set(data,'{version}',to_jsonb(version+1)) WHERE id=%s",(target,))
    from backend.app.domains.review.proposals import bump
    p['summary']['status']='applied';bump(p);put(c,'proposal',p)
    app.update(status='applied',finished_at=now(),audit_event_ids=[e['id'] for e in events]);c.execute('UPDATE applications SET data=%s WHERE id=%s',(Jsonb(app),app['id']))
    return app
