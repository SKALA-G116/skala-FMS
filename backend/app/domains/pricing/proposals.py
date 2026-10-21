"""Deterministic, user-mapped table ingestion. Explicit period/party/price basis;
no unreviewed facts. Each product group is one atomic proposal (max 50 ops)."""
from decimal import Decimal
from decimal import InvalidOperation
from collections import defaultdict
from backend.app.infrastructure.database import Problem
from datetime import date
from backend.app.infrastructure.database import entities
from backend.app.infrastructure.database import get
from backend.app.infrastructure.database import now
from backend.app.infrastructure.database import put
from backend.app.infrastructure.database import uid
from backend.app.domains.review.proposals import create
from backend.app.infrastructure.contracts import schema_check

UNITS={'kg':'kg','g':'g','l':'l','ml':'ml','ea':'ea','ea(개)':'ea','개':'ea','봉':'bag','봉지':'bag','bag':'bag','box':'box','상자':'box','박스':'box','pack':'pack','팩':'pack','병':'ea','통':'ea','판':'ea','캔':'ea','포':'pack'}

def stage(c,sheet_id,payload):
    sheet=c.execute('SELECT * FROM price_sheets WHERE id=%s',(sheet_id,)).fetchone()
    if not sheet:raise Problem(404,'NOT_FOUND','시트를 찾을 수 없습니다.')
    workbook=c.execute('SELECT * FROM price_workbooks WHERE id=%s',(sheet['workbook_id'],)).fetchone();rev=get(c,'revision',str(workbook['revision_id']))
    supplier=get(c,'supplier',payload.get('supplier_id'));columns={x['key'] for x in sheet['columns']}
    for key in ('name_column','price_column','unit_column'):
        if payload.get(key) not in columns:raise Problem(422,'COLUMN_REQUIRED','식품명·가격·단위 열을 선택하세요.')
    specs=payload.get('spec_columns',[])
    if not isinstance(specs,list) or not specs or any(x not in columns for x in specs):raise Problem(422,'SPEC_REQUIRED','규격 열을 한 개 이상 선택하세요.')
    try:date.fromisoformat(payload.get('effective_from',''))
    except ValueError:raise Problem(422,'DATE_REQUIRED','적용 시작일을 지정하세요.')
    if payload.get('tax') not in ('included','excluded','unknown'):raise Problem(422,'TAX_REQUIRED','세금 기준을 선택하세요.')
    chosen=payload.get('row_numbers')
    if chosen is not None and (not isinstance(chosen,list) or not chosen or len(chosen)>500 or any(not isinstance(x,int) or x<2 for x in chosen)):raise Problem(422,'ROW_SELECTION','최대 500행까지 선택할 수 있습니다.')
    rows=c.execute('SELECT row_number,cells FROM price_sheet_rows WHERE sheet_id=%s AND row_number>'+str(sheet['header_row'])+(' AND row_number=ANY(%s)' if chosen else '')+' ORDER BY row_number LIMIT 501',([sheet_id,chosen] if chosen else [sheet_id])).fetchall()
    if len(rows)>500:raise Problem(422,'BATCH_LIMIT','500행 이하로 나누어 검토하세요.')
    groups=defaultdict(list);skipped=[];seen=set()
    for row in rows:
        cells=row['cells'];rn=row['row_number'];name=cells.get(payload['name_column'],'').strip();price=cells.get(payload['price_column'],'').replace(',','').strip();spec=' / '.join(cells.get(k,'').strip() for k in specs if cells.get(k,'').strip());sales=cells.get(payload['unit_column'],'').strip();unit=UNITS.get(sales.lower())
        try:
            amount=Decimal(price)
            if not amount.is_finite() or amount<0 or amount.as_tuple().exponent<-4:raise ValueError()
        except (InvalidOperation,ValueError):skipped.append({'row_number':rn,'message':'가격이 비어 있거나 유효한 금액이 아닙니다.'});continue
        if amount==0 and not payload.get('include_zero',False):skipped.append({'row_number':rn,'message':'0원 행은 제외했습니다.'});continue
        if not name or not spec or not unit:skipped.append({'row_number':rn,'message':'식품명·규격 또는 지원하는 판매 단위가 필요합니다.'});continue
        identity=(name,spec,sales)
        if identity in seen:skipped.append({'row_number':rn,'message':'같은 식품·규격·판매 단위가 중복되어 별도 검토가 필요합니다.'});continue
        seen.add(identity);groups[name].append({'row':rn,'cells':cells,'spec':spec,'sales':sales,'unit':unit,'amount':format(amount,'f')})
    ps=[];bundles=[];products=entities(c,'product');variants=entities(c,'variant');items=entities(c,'supplier_item')
    for name,group in groups.items():
        if len(group)*3+1>50:
            skipped.extend({'row_number':r['row'],'message':'한 식품의 규격 묶음이 50개 작업을 초과했습니다.'} for r in group);continue
        candidates=[p for p in products if p['name']==name]
        if len(candidates)>1:
            skipped.extend({'row_number':r['row'],'message':'같은 이름의 제품이 여럿 있습니다. 제조사와 규격을 수동으로 확인하세요.'} for r in group);continue
        changes=[];p=candidates[0] if candidates else None;product_ref={'id':p['id']} if p else {'local_ref':'p'}
        for i,row in enumerate(group):
            quote=' | '.join(f'{k}: {v}' for k,v in row['cells'].items())[:4096]
            ev=put(c,'evidence',{'id':uid(),'document_revision_id':rev['id'],'source_url':get(c,'document',rev['document_id'])['source_url'],'quote':quote,'locator':{'kind':'spreadsheet','asset_id':str(workbook['asset_id']),'sheet_name':sheet['name'],'cell_range':f"A{row['row']}:{sheet['columns'][-1]['key']}{row['row']}"},'extraction_id':None,'ocr_confidence':None,'created_at':now()})
            ops=[]
            if not p and i==0:ops.append({'kind':'create_product','local_ref':'p','name':name,'manufacturer_id':None,'brand_id':None})
            matched=[v for v in variants if p and v['product_id']==p['id'] and v['spec_normalized']==row['spec']]
            v=matched[0] if len(matched)==1 else None;vref={'id':v['id']} if v else {'local_ref':f'v{i}'}
            if not v:ops.append({'kind':'create_variant','local_ref':f'v{i}','product_ref':product_ref,'spec_original':row['spec'],'spec_normalized':row['spec'],'barcode':None})
            matched_items=[x for x in items if v and x['variant_id']==v['id'] and x['supplier_id']==supplier['id'] and x['sales_unit']==row['sales']]
            item=matched_items[0] if len(matched_items)==1 else None;iref={'id':item['id']} if item else {'local_ref':f'i{i}'}
            if not item:ops.append({'kind':'create_supplier_item','local_ref':f'i{i}','variant_ref':vref,'supplier_id':supplier['id'],'supplier_code':None,'sales_unit':row['sales']})
            # Existing overlapping facts are never silently superseded.
            previous=None
            if item:
                overlapping=c.execute("SELECT id FROM facts WHERE target_id=%s AND kind='set_price' AND condition_key='public' AND (effective_to IS NULL OR effective_to>%s::date)",(item['id'],payload['effective_from'])).fetchall()
                if len(overlapping)==1 and payload.get('replace_existing',False):previous=str(overlapping[0]['id'])
                elif overlapping:
                    skipped.append({'row_number':row['row'],'message':'기존 가격과 기간이 겹칩니다. 정정 여부를 지정하거나 별도 검토하세요.'});continue
            ops.append({'kind':'set_price','supplier_item_ref':iref,'value':{'amount':row['amount'],'currency':'KRW','quantity':'1','unit':row['unit'],'tax':payload['tax'],'price_kind':'regular','condition_key':'public'},'period':{'effective_from':payload['effective_from'],'effective_to':None},'reason':{'original_text':None,'summary':'검토자가 표의 가격 열과 적용일을 지정함','code':None},'supersedes_fact_id':previous})
            changes.extend({'id':uid(),'operation':op,'field_evidence':[{'field_path':'/'+k,'evidence_ids':[ev['id']],'origin':'reviewer','reviewer_justification':'표의 식품명·규격·가격·공급처·적용일 매핑을 담당자가 지정함'} for k in op if k not in ('kind','local_ref','supersedes_fact_id','manufacturer_id','brand_id','barcode','supplier_code')]} for op in ops)
        if not changes:continue
        prefix=f'g{len(bundles)}_'
        def rename(value):
            if isinstance(value,dict):return {k:(prefix+v if k=='local_ref' else rename(v)) for k,v in value.items()}
            if isinstance(value,list):return [rename(v) for v in value]
            return value
        bundles.append((name,rename(changes)))
    pending=[];names=[]
    def flush():
        if not pending:return
        title=f"{workbook['filename']} · {len(names)}개 식품 단가"
        schema_check('ProposalCreate',{'title':title,'source_document_revision_ids':[rev['id']],'changes':pending})
        proposal=create(c,title,[rev['id']],pending.copy());ps.append(proposal['summary'])
    for name,changes in bundles:
        if pending and len(pending)+len(changes)>50:flush();pending=[];names=[]
        pending.extend(changes);names.append(name)
    flush()
    return {'proposals':ps,'skipped_rows':skipped,'prepared_count':len(rows)-len(skipped),'skipped_count':len(skipped),'source_row_count':len(rows)}
