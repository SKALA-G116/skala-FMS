

def nullable(t):return {'type':[t,'null']}

PLAN={'type':'object','additionalProperties':False,'properties':{'document_type':{'type':'string','enum':['notice','price_table','mixed','marketing','other']},'summary':{'type':'string'},'tasks':{'type':'array','maxItems':6,'items':{'type':'string','enum':['extract_prices','extract_food_profiles','extract_supply_changes','extract_substitutions','match_catalog','create_review_excel','no_business_change']}}},'required':['document_type','summary','tasks']}

EVENT_FIELDS={
 'kind':{'type':'string','enum':['price','temporarily_unavailable','supply_ended','discontinued','available','substitution','new_product','food_profile']},
 'company_name':nullable('string'),'food_code':nullable('string'),'attributes_text':nullable('string'),'allergen_text':nullable('string'),
 'product_name':nullable('string'),'spec':nullable('string'),'amount':nullable('string'),
 'quantity':nullable('string'),'unit':{'type':['string','null'],'enum':['g','kg','ml','l','ea','bag','box','pack',None]},
 'effective_from':nullable('string'),'effective_to':nullable('string'),'reason':nullable('string'),
 'replacements':{'type':'array','maxItems':6,'items':{'type':'string'}},
 'price_basis':nullable('string'),'uncertainties':{'type':'array','maxItems':8,'items':{'type':'string'}},
 'source_ids':{'type':'array','minItems':1,'maxItems':12,'items':{'type':'string'}}}

def event_schema(ids):
    properties={**EVENT_FIELDS,'source_ids':{'type':'array','minItems':1,'maxItems':12,'items':{'type':'string','enum':ids}}}
    event={'type':'object','additionalProperties':False,'properties':properties,'required':list(properties)}
    return {'type':'object','additionalProperties':False,'properties':{'events':{'type':'array','maxItems':24,'items':event}},'required':['events']}
