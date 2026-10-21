from backend.app.infrastructure.database import Problem
from backend.app.infrastructure.database import entities
from backend.app.infrastructure.database import entity
from backend.app.infrastructure.database import get
from backend.app.infrastructure.database import today
import uuid

def active_facts(c,target,kind,as_of=None,scheduled=False):
    as_of=as_of or today()
    rows=c.execute('SELECT * FROM facts WHERE target_id=%s AND kind=%s ORDER BY recorded_at DESC,id DESC',(target,kind)).fetchall()
    active=[]
    for r in rows:
        start,end=r['effective_from'].isoformat(),r['effective_to'].isoformat() if r['effective_to'] else None
        if end and end<=as_of:continue
        if start>as_of and not scheduled:continue
        overridden=any(str(n['supersedes_fact_id'])==str(r['id']) and n['effective_from'].isoformat()<=max(as_of,start) and (n['effective_to'] is None or n['effective_to'].isoformat()>max(as_of,start)) for n in rows)
        if not overridden:active.append({**r['data'],'id':str(r['id']),'effective_state':'scheduled' if start>as_of else 'active','recorded_at':r['recorded_at'].isoformat()})
    return active

def item_detail(c,obj,as_of=None):
    facts=active_facts(c,obj['id'],'set_availability',as_of)
    return {**obj,'availability':({'status':facts[0]['status'],'period':facts[0]['period'],'reason':facts[0]['reason'],'evidence_ids':facts[0]['evidence_ids'],'fact_id':facts[0]['id']} if facts else None)}

def product_detail(c,id,as_of=None):
    p=entity(c,id);vs=[v for v in entities(c,'variant') if v['product_id']==id];vids={v['id'] for v in vs}
    its=[item_detail(c,x,as_of) for x in entities(c,'supplier_item') if x['variant_id'] in vids]
    for v in vs:
        profile=c.execute('SELECT data FROM food_profiles WHERE variant_id=%s',(v['id'],)).fetchone()
        from backend.app.domains.catalog.record import from_event
        v['food_record']=profile['data'] if profile else from_event({'product_name':p['name'],'spec':v['spec_original']})
        if not profile:
            companies={i['supplier_id'] for i in its if i['variant_id']==v['id']}
            if len(companies)==1:
                company=get(c,'supplier',next(iter(companies)));v['food_record'].update(company_id=company['id'],company_name=company['name'])
        from backend.app.domains.ingestion.archives import state
        v.update(state(c,'food',v['id']))
    facts=active_facts(c,id,'set_product_status',as_of)
    return {**p,'status':facts[0]['status'] if facts else p['status'],'variants':vs[:20],'supplier_items':its[:20],'variants_next_cursor':None,'supplier_items_next_cursor':None}

def prices(c,as_of=None,scheduled=False):
    out=[]
    archived={str(r['record_id']) for r in c.execute("SELECT record_id FROM record_archives WHERE record_kind='food' AND archived")}
    for item in entities(c,'supplier_item'):
        if item['variant_id'] in archived:continue
        v=entity(c,item['variant_id']);p=entity(c,v['product_id'])
        for f in active_facts(c,item['id'],'set_price',as_of,scheduled):
            out.append({'id':f['id'],'product_id':p['id'],'product_name':p['name'],'variant_id':v['id'],'spec_label':v['spec_original'],'supplier_item_id':item['id'],'supplier':get(c,'supplier',item['supplier_id']),'supplier_code':item['supplier_code'],'value':f['value'],'period':f['period'],'effective_state':f['effective_state'],'reason':f['reason'],'evidence_ids':f['evidence_ids'],'recorded_at':f['recorded_at'],'supersedes_fact_id':f.get('supersedes_fact_id')})
    return out

def foods(c,q):
    """Paginated canonical records; legacy records are adapted without role labels."""
    from backend.app.domains.catalog.record import from_event
    import uuid
    try:
        limit=min(max(int(q.get('limit','30')),1),100)
        cursor=str(uuid.UUID(q['cursor'])) if q.get('cursor') else None
    except (ValueError,TypeError):raise Problem(422,'INVALID_CURSOR','조회 조건을 확인해 주세요.')
    search=q.get('q','').strip()[:200]
    archived=q.get('archived')=='true'
    rows=c.execute("""SELECT coalesce(a.archived,false) archived,coalesce(a.version,0) archive_version,v.id,v.data variant,p.data product,fp.data profile,fp.version profile_version,
      coalesce(fp.data->>'company_name',s.data->>'name') company_name,s.id company_id
      FROM catalog_entities v
      JOIN catalog_entities p ON p.id::text=v.data->>'product_id' AND p.kind='product'
      LEFT JOIN food_profiles fp ON fp.variant_id=v.id
      LEFT JOIN record_archives a ON a.record_kind='food' AND a.record_id=v.id
      LEFT JOIN LATERAL (SELECT ar.id,ar.data FROM catalog_entities i JOIN app_records ar ON ar.id::text=i.data->>'supplier_id' AND ar.kind='supplier'
        WHERE i.kind='supplier_item' AND i.data->>'variant_id'=v.id::text AND (SELECT count(DISTINCT k.data->>'supplier_id') FROM catalog_entities k WHERE k.kind='supplier_item' AND k.data->>'variant_id'=v.id::text)=1 ORDER BY i.id LIMIT 1) s ON true
      WHERE v.kind='variant' AND coalesce(a.archived,false)=%s AND (%s::uuid IS NULL OR v.id>%s::uuid)
      AND (%s='' OR strpos(lower(coalesce(fp.data::text,'')||p.data::text||v.data::text||coalesce(s.data->>'name','')),lower(%s))>0)
      ORDER BY v.id LIMIT %s""",(archived,cursor,cursor,search,search,limit+1)).fetchall()
    more=len(rows)>limit;out=[]
    for row in rows[:limit]:
        p=row['product'];v=row['variant'];record=row['profile'] or from_event({'product_name':p['name'],'spec':v['spec_original']})
        if not row['profile'] and row['company_name']:record.update(company_name=row['company_name'],company_id=str(row['company_id']))
        out.append({'id':str(row['id']),'product_id':p['id'],'version':row['profile_version'] or v['version'],'food_record':record,'status':p['status'],'evidence_ids':v.get('evidence_ids',[]),'has_stored_profile':bool(row['profile']),'archived':row['archived'],'archive_version':row['archive_version']})
    return {'items':out,'next_cursor':out[-1]['id'] if more else None,'has_more':more}
