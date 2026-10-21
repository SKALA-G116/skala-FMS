"""
==============================================================================
FMS_FILE_SPEC
record.py - 표준 FoodRecord DTO와 정규화
==============================================================================
설명:
    - 표준 FoodRecord DTO와 정규화
입력·출력 명세:
    - 입력: 업체별 표 행·본문 추출값·규격·알레르기 문구
    - 출력: food-record-v2의 nullable 식품 정보와 필드 근거
실행 가정:
    - 공란과 0, 알레르기 후보와 함유 표시를 구분
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

    2026-10-21  미지정      v0.1.0   업체 표 직접 정규화·중복 통합·원문 이력 보존

    2026-10-21  미지정      v0.1.0   원본 속성 누락 복구·재정리 API·검토 동선 개선

    2026-10-21  김재현(Finn) v0.1.0   Agent 도구 선택 기반 리빌드·업무 경계 및 검증

    상세 Git 이력: git log --follow -- backend/app/domains/catalog/record.py
    공통 규칙: doc/file-header-policy.md

기존 모듈 설명:
    One nullable FoodRecord contract for extraction, review, storage and catalog views.
    Unknown is None; zero is a number; no allergen statement never means allergen-free.
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

import re
import copy
from decimal import Decimal
from backend.app.infrastructure.database import Problem

VERSION='food-record-v2'

ALLERGENS={'egg':('난류',['난류','계란','달걀','메추리알']),'milk':('우유',['우유','원유','분유','유청','카제인']), 'buckwheat':('메밀',['메밀']),'peanut':('땅콩',['땅콩']),'soy':('대두',['대두','두유','두부']), 'wheat':('밀',['밀가루','소맥','우리밀','통밀']), 'mackerel':('고등어',['고등어']),'crab':('게',['꽃게','대게','홍게']), 'shrimp':('새우',['새우']),'pork':('돼지고기',['돼지고기','돈육']), 'peach':('복숭아',['복숭아']), 'tomato':('토마토',['토마토']), 'sulfite':('아황산류',['아황산','이산화황']), 'walnut':('호두',['호두']), 'chicken':('닭고기',['닭고기','계육']), 'beef':('쇠고기',['쇠고기','소고기','우육']), 'squid':('오징어',['오징어']), 'shellfish':('조개류',['조개','굴','전복','홍합']), 'pine_nut':('잣',['잣'])}

def empty_record():
    return {'schema_version':VERSION,'record_type':'commercial_product','food_code':None,'food_name':None,'raw_food_name':None,'company_id':None,'company_name':None,
      'attributes':{'original_text':None,'flavor':None,'origin_region':None,'size_grade':None,'quality_grade':None,'intended_use':None,'labeling_requirement':None,'origin_country':None,'ingredients':None,'other':None},
      'specification':{'original_text':None,'quantity':None,'unit':None,'piece_quantity':None,'piece_unit':None,'pack_count':None,'normalized_quantity':None,'normalized_unit':None,'sales_unit':None},
      'allergens':{'contains':None,'may_contain':None,'free_from_claims':None,'candidates':[],'review_status':'unknown','original_text':None},
      'prices':{'source_applied':None,'survey_1':None,'survey_2':None,'survey_3':None},'supplier_group':None,'eco_classification':None,'note':None,'field_sources':{},'issues':[]}

def text(v):return None if v is None or str(v).strip()=='' else str(v).strip()

def number(v):
    v=text(v)
    if v is None:return None
    v=v.replace(',','')
    if not re.fullmatch(r'\d{1,16}(?:\.\d{1,6})?',v):return None
    return format(Decimal(v).normalize(),'f')

def allergens_from_text(raw,name=None):
    result=empty_record()['allergens'];result['original_text']=text(raw)
    def detect(s):
        found=[]
        for code,(label,aliases) in ALLERGENS.items():
            if any(a in s for a in aliases) or re.search(r'(?<![가-힣])'+re.escape(label)+r'(?![가-힣])',s):found.append(code)
        return found
    result['candidates']=detect(' '.join(filter(None,[raw,name])))
    for clause in re.split(r'[\n;]',raw or ''):
        codes=detect(clause)
        if not codes:continue
        key=None
        if re.search(r'같은.*(?:시설|공장)|혼입|교차|혼재',clause):key='may_contain'
        elif re.search(r'미함유|불포함|무첨가|(?:free\s*from)',clause,re.I):key='free_from_claims'
        elif re.search(r'함유|알레르기\s*(?:유발물질)?\s*[:：]',clause):key='contains'
        if key:result[key]=list(dict.fromkeys((result[key] or [])+codes));result['review_status']='source_declared'
    return result

def attribute_tokens(raw):
    """Tokenize separators outside parentheses/brackets without losing source tokens."""
    result=[];current=[];depth=0
    for char in raw or '':
        if char in '([（［':depth+=1
        elif char in ')]）］':depth=max(0,depth-1)
        if char in ',/\n' and depth==0:
            if ''.join(current).strip():result.append(''.join(current).strip())
            current=[]
        else:current.append(char)
    if ''.join(current).strip():result.append(''.join(current).strip())
    return result


def attributes(raw):
    out=empty_record()['attributes'];out['original_text']=text(raw)
    if not raw:return out
    other=[];ingredients=[]
    # Split only outside brackets so ingredient origins and compound descriptions survive.
    for token in attribute_tokens(raw):
        recognized=False
        m=re.search(r'([특상중하1-9]+등급)',token)
        if m:out['quality_grade']=m[1];recognized=True
        m=re.fullmatch(r'(?:규격|크기)?\s*([대중소](?:\([大小中]\))?)',token)
        if m:out['size_grade']=m[1];recognized=True
        if '용' in token and any(x in token for x in ('급식','조리','튀김','샐러드')):out['intended_use']=token;recognized=True
        if '표시기준' in token:out['labeling_requirement']=token;recognized=True
        # Percentages identify an ingredient declaration, independent of ingredient name.
        if re.search(r'\d+(?:\.\d+)?\s*%',token):
            ingredients.extend(ingredient_details(token) or []);recognized=True
        if token in ('국산','국내산'):out['origin_country']='KR';recognized=True
        # Specification tokens already have dedicated DTO fields; raw text remains intact.
        if re.fullmatch(r'\d+(?:\.\d+)?\s*(?:kg|g|ml|l)|EA\(개\)|개|통|봉|팩',token,re.I):recognized=True
        if not recognized:other.append(token)
    out['ingredients']=ingredients or None;out['other']=other or None
    return out

def specification(raw=None,quantity=None,unit=None,sales_unit=None,normalized=None):
    out=empty_record()['specification'];out.update(original_text=text(raw),quantity=number(quantity),unit=text(unit),sales_unit=text(sales_unit))
    if out['quantity'] is None and raw:
        m=re.fullmatch(r'\s*(\d+(?:\.\d+)?)\s*(kg|g|ml|l)\s*',raw,re.I) or re.match(r'^\s*(\d+(?:\.\d+)?)\s*(kg|g|ml|l)\s*\(',raw,re.I)
        if m:out['quantity']=number(m[1]);out['unit']=m[2].lower()
    if out['unit']:out['unit']={'㎖':'ml','㎏':'kg','ℓ':'l'}.get(out['unit'].lower(),out['unit'].lower())
    if out['quantity'] is not None and out['unit'] in ('g','kg','ml','l'):
        factor=Decimal('0.001') if out['unit'] in ('g','ml') else Decimal(1);out['normalized_quantity']=format((Decimal(out['quantity'])*factor).normalize(),'f');out['normalized_unit']='kg' if out['unit'] in ('g','kg') else 'l'
    if normalized:
        m=re.fullmatch(r'\s*(\d+(?:\.\d+)?)\s*(kg|l)\s*',normalized,re.I)
        if m:
            supplied=number(m[1]);u=m[2].lower()
            if out['normalized_quantity'] is not None and (supplied!=out['normalized_quantity'] or u!=out['normalized_unit']):out['normalization_conflict']=True
            elif out['normalized_quantity'] is None:out['normalized_quantity']=supplied;out['normalized_unit']=u
    return out

ALIASES={
 'food_code':['공통식품코드','통식품코드','식품코드','공통코드'], 'food_name':['공통식품명','식품명','품명','제품명','상품명','품목명'],
 'attributes':['공통식품속성','식품속성','제품설명','상품설명','상세설명'], 'quantity':['규격수','규격수량','내용량'], 'unit':['규격'], 'normalized':['규격(kg.l)','규격(kg,l)','규격(kg/l)'], 'sales_unit':['단위','판매단위','포장단위'],
 'raw_spec':['제품규격','포장규격'], 'ingredients':['원재료','원재료명','원재료및함량','원재료함량'], 'description':['맛&구별','제품특징','제품특성','보관','보관방법'], 'flavor':['맛','맛·종류','종류'], 'supply_price':['학교가','납품가','공급가','판매가','단가'],
 'source_applied':['적용가','적용단가'],'survey_1':['조사가1'],'survey_2':['조사가2'],'survey_3':['조사가3'], 'supplier_group':['업체군'],'eco_classification':['친환경구분'],'note':['비고','메모'], 'allergens':['알레르기','알레르기정보','알레르기유발물질'],'company_name':['업체','업체명','공급처','공급업체','판매사','제조사','제조업체','브랜드']}

def company_display(value):
    """Normalize legal-form prefixes for display; source text remains in provenance."""
    if not value:return None
    return re.sub(r'^(?:(?:농업|어업)회사법인\s*)?(?:주식회사|㈜|\(주\))\s*','',value).strip() or value


def ingredient_details(raw):
    """Keep each ingredient's raw token; ingredient origins are not product origins."""
    result=[]
    for token in attribute_tokens(raw):
        token=token.strip()
        if not token:continue
        percent=re.search(r'(\d+(?:\.\d+)?)\s*%',token)
        name=re.sub(r'\s*\d+(?:\.\d+)?\s*%','',token).strip()
        name=re.sub(r'^(?:국내산|국산)\s*','',name).strip()
        result.append({'name':name,'percentage':percent[1] if percent else None,'origin_country':'KR' if re.search(r'국산|국내산',token) else None,'original_text':token})
    return result[:100] or None


def header_key(v):return re.sub(r'\s+','',re.sub(r'_x[0-9a-fA-F]{4}_','',str(v or ''))).casefold()

def header_mapping(row):
    found={}
    for index,value in enumerate(row):
        key=header_key(value)
        for name,aliases in ALIASES.items():
            if key in [header_key(a) for a in aliases] and name not in found:found[name]=index
    if 'quantity' not in found and 'unit' in found:found['raw_spec']=found.pop('unit')
    return found if 'food_name' in found and any(k in found for k in ('food_code','attributes','quantity','raw_spec','ingredients','supply_price')) else None

def split_name(raw):
    original=text(raw);name=original or '';attrs={};spec={};details=[]
    company=re.match(r'^((?:(?:주식회사|㈜|\(주\))\s*)?[A-Za-z가-힣0-9&]+(?:씨푸드|푸드|식품|식품공업|유업|축산|수산))\s+(.+)$',name)
    if company:attrs['_company_name']=company[1];name=company[2]
    # Parentheses are stripped only when their content is recognizable metadata.
    pattern=r'[（(]([^()（）]+)[)）]'
    def take(match):
        content=match[1]
        if re.search(r'\d+\s*(?:kg|g|ml|l|입|개)|오리지[널날]|매운맛|순한맛|(?:국내|국|완도|제주)산|^[대중소大小中]$|/\s*(?:EA|BOX|PACK)',content,re.I):details.append(content);return ''
        return match[0]
    name=re.sub(pattern,take,name)
    for detail in details:
        variant=re.match(r'^([^_]*?)[_]',detail)
        if variant and variant[1].strip():attrs['flavor']=variant[1].strip()
        elif detail in ('오리지날','오리지널','매운맛','순한맛'):attrs['flavor']=detail
        origin=re.fullmatch(r'(완도|제주)산',detail)
        if origin:attrs['origin_region']=origin[1]
        if detail in ('국내산','국산'):attrs['origin_country']='KR'
        if detail in ('소','小','중','中','대','大'):attrs['size_grade']=detail
    rawspec=' '.join(d for d in details if re.search(r'\d+\s*(?:kg|g|ml|l|입|개)',d,re.I))
    if rawspec:
        piece=re.search(r'(\d+(?:\.\d+)?)\s*(kg|g|ml|l)\s*[*x×]\s*(\d+)\s*(?:입|개)',rawspec,re.I)
        if piece:spec.update(piece_quantity=number(piece[1]),piece_unit=piece[2].lower(),pack_count=number(piece[3]))
        totals=list(re.finditer(r'(\d+(?:\.\d+)?)\s*(kg|g|ml|l)(?![a-z])',rawspec,re.I))
        if totals:
            total=totals[-1]
            # A sole 100g*10 describes pieces, not a 100g total package.
            if len(totals)>1 or not piece:spec.update(quantity=number(total[1]),unit=total[2].lower())
        sales=re.search(r'/\s*(EA|개|봉|팩|통|병|포|캔|BOX|PACK|BAG)\b',rawspec,re.I)
        if sales:spec['sales_unit']=sales[1]
        spec['original_text']=rawspec
    name=re.sub(r'\s+',' ',name).strip(' _/')
    # Generic food name suffix like 우유/소(小) is a size attribute.
    size=re.search(r'/\s*([소중대])\s*$',name)
    if size:attrs['size_grade']=attrs.get('size_grade') or size[1];name=name[:size.start()].strip()
    return {'food_name':name or original,'raw_food_name':original,'attributes':attrs,'specification':spec}

def apply_name(record,raw):
    parts=split_name(raw);record.update(food_name=parts['food_name'],raw_food_name=parts['raw_food_name']);record['attributes'].update({k:v for k,v in parts['attributes'].items() if not k.startswith('_')})
    if not record['company_name']:record['company_name']=parts['attributes'].get('_company_name')
    if parts['specification']:
        extra=parts['specification'];normalized=specification(extra.get('original_text'),extra.get('quantity'),extra.get('unit'),extra.get('sales_unit'))
        record['specification'].update({k:v for k,v in normalized.items() if v is not None});record['specification'].update(extra)
    return record

def from_table_row(row,mapping,locator,company_name=None):
    get=lambda key:row[mapping[key]] if key in mapping and mapping[key]<len(row) else None
    if text(get('food_name')) is None:return None
    record=empty_record();record.update(record_type='common_food' if text(get('food_code')) else 'commercial_product',food_code=text(get('food_code')),food_name=text(get('food_name')),company_name=company_display(text(get('company_name')) or company_name),supplier_group=text(get('supplier_group')),eco_classification=text(get('eco_classification')),note=text(get('note')))
    if isinstance(get('food_code'),(int,float)) and float(get('food_code')).is_integer():record['food_code']=str(int(get('food_code')))
    record['attributes']=attributes(text(get('attributes')));record['specification']=specification(raw=text(get('raw_spec')),quantity=get('quantity'),unit=get('unit'),sales_unit=get('sales_unit'),normalized=text(get('normalized')))
    if not record['specification']['original_text'] and record['specification']['quantity'] and record['specification']['unit']:record['specification']['original_text']=record['specification']['quantity']+record['specification']['unit']
    apply_name(record,text(get('food_name')))
    package=split_name('식품('+str(get('raw_spec'))+')')['specification'] if text(get('raw_spec')) else {}
    for key in ('piece_quantity','piece_unit','pack_count'):
        if package.get(key):record['specification'][key]=package[key]
    if text(get('ingredients')):record['attributes']['ingredients']=ingredient_details(text(get('ingredients')))
    if text(get('description')):record['attributes']['other']=list(dict.fromkeys((record['attributes']['other'] or [])+[text(get('description'))]))
    if text(get('flavor')):record['attributes']['flavor']=text(get('flavor'))
    if text(get('supply_price')):record['prices']['source_applied']=number(get('supply_price'))
    if record['specification']['sales_unit'] in ('개','EA','ea','EA(개)') and record['specification']['quantity']:
        record['specification'].update(piece_quantity=record['specification']['quantity'],piece_unit=record['specification']['unit'])
    record['allergens']=allergens_from_text(text(get('allergens')) or text(get('ingredients')) or text(get('attributes')),record['food_name'])
    for key in record['prices']:
        if text(get(key)) is not None:record['prices'][key]=number(get(key))
    if company_name and not text(get('company_name')):record['field_sources']['company_name']={'locator':locator,'raw_value':company_name,'origin':'parser_context'}
    for key,index in mapping.items():
        if text(get(key)) is not None:record['field_sources'][key]={'locator':locator,'column_index':index,'raw_value':str(get(key)),'origin':'parser'}
    if record['specification'].pop('normalization_conflict',False):record['issues'].append('원본 규격과 환산 규격이 일치하지 않습니다.')
    return record

def from_event(event):
    if event.get('food_record'):return copy.deepcopy(event['food_record'])
    result=empty_record();result['company_name']=text(event.get('company_name'));result['food_name']=text(event.get('product_name'));result['food_code']=text(event.get('food_code'));result['record_type']='common_food' if result['food_code'] else 'commercial_product';result['attributes']=attributes(text(event.get('attributes_text')));result['specification']=specification(event.get('spec'));result['allergens']=allergens_from_text(text(event.get('allergen_text')) or text(event.get('attributes_text')),event.get('product_name'));apply_name(result,event.get('product_name'))
    rawspec=text(event.get('spec'))
    if rawspec:
        parts=split_name('식품('+rawspec+')')['specification']
        if parts:
            result['specification'].update(parts)
            normalized=specification(rawspec,result['specification']['quantity'],result['specification']['unit'],result['specification']['sales_unit'])
            for key in ('normalized_quantity','normalized_unit'):result['specification'][key]=normalized[key]
    for field in ('food_name','specification'):

        result['field_sources'][field]={'evidence_ids':event.get('evidence_ids',[]),'origin':'llm'}
    return result

def merge_profile(before,incoming):
    """Unknown incoming fields never erase known approved values."""
    if before is None:return copy.deepcopy(incoming)
    if not isinstance(incoming,dict):return copy.deepcopy(incoming) if incoming is not None else copy.deepcopy(before)
    merged=copy.deepcopy(before) if isinstance(before,dict) else {}
    for key,value in incoming.items():
        if value is None:continue
        if isinstance(value,dict):merged[key]=merge_profile(merged.get(key),value)
        else:merged[key]=copy.deepcopy(value)
    if 'review_status' in incoming and before.get('review_status')=='reviewed' and incoming.get('review_status')!='reviewed':
        unchanged=all(incoming.get(k) is None or incoming.get(k)==before.get(k) for k in ('contains','may_contain','free_from_claims','original_text'))
        if unchanged:merged['review_status']='reviewed'
    return merged

def record_schema():
    string={'type':['string','null'],'maxLength':2000}
    def obj(props):return {'type':'object','additionalProperties':False,'properties':props,'required':list(props)}
    allergy_list={'type':['array','null'],'items':{'enum':list(ALLERGENS)},'uniqueItems':True}
    attrs={k:copy.deepcopy(string) for k in empty_record()['attributes']}
    attrs['ingredients']={'type':['array','null'],'maxItems':100,'items':obj({'name':string,'percentage':string,'origin_country':string,'original_text':string})}
    attrs['other']={'type':['array','null'],'maxItems':100,'items':{'type':'string','maxLength':2000}}
    top={k:copy.deepcopy(string) for k in ('food_code','food_name','raw_food_name','company_id','company_name','supplier_group','eco_classification','note')}
    top['company_id']={'type':['string','null'],'format':'uuid'}
    top.update(schema_version={'const':VERSION},record_type={'enum':['common_food','commercial_product']},attributes=obj(attrs),specification=obj({k:copy.deepcopy(string) for k in empty_record()['specification']}),allergens=obj({'contains':allergy_list,'may_contain':allergy_list,'free_from_claims':allergy_list,'candidates':{'type':'array','items':{'enum':list(ALLERGENS)},'uniqueItems':True},'review_status':{'enum':['unknown','source_declared','reviewed']},'original_text':string}),prices=obj({k:copy.deepcopy(string) for k in empty_record()['prices']}),field_sources={'type':'object'},issues={'type':'array','items':{'type':'string'},'maxItems':100})
    return obj(top)

def validate_record(record):
    from jsonschema import Draft202012Validator,FormatChecker
    errors=list(Draft202012Validator(record_schema(),format_checker=FormatChecker()).iter_errors(record))
    if errors:raise Problem(422,'FOOD_RECORD_INVALID','표준 식품 정보의 값과 형식을 확인해 주세요.',[{'field':'/'.join(map(str,e.absolute_path)),'message':e.message} for e in errors[:5]])
    if record['allergens']['review_status']=='reviewed' and not record['allergens']['original_text']:
        raise Problem(422,'ALLERGEN_EVIDENCE','알레르기 확인에는 표시사항 원문 또는 확인 근거를 남겨 주세요.')
    if set(record['allergens']['contains'] or [])&set(record['allergens']['free_from_claims'] or []):raise Problem(422,'ALLERGEN_CONFLICT','같은 알레르기 성분이 함유와 불포함에 함께 표시되어 있습니다.')
    for key in ('quantity','piece_quantity','normalized_quantity','pack_count'):
        value=record['specification'][key]
        if value is not None and (number(value) is None or Decimal(number(value))<=0 or (key=='pack_count' and Decimal(number(value))!=Decimal(number(value)).to_integral_value())):raise Problem(422,'FOOD_QUANTITY','규격 수량은 양수, 포장 수량은 양의 정수로 입력하세요.')
    for ingredient in record['attributes']['ingredients'] or []:
        value=ingredient.get('percentage')
        if value is not None and (number(value) is None or Decimal(number(value))>100):raise Problem(422,'FOOD_INGREDIENT','원재료 함량은 0~100 사이의 숫자로 입력하세요.')
    for key in record['prices']:

        v=record['prices'][key]
        if v is not None and number(v) is None:raise Problem(422,'FOOD_PRICE_FORMAT','자료의 가격은 숫자 또는 공란이어야 합니다.')
    for key in ('quantity','piece_quantity','normalized_quantity','pack_count'):
        record['specification'][key]=number(record['specification'][key])
    for key,value in record['prices'].items():record['prices'][key]=number(value)
    return record

def upgrade_event(event):
    result=copy.deepcopy(event);record=from_event(event);result['food_record']=record
    if record['food_name']:result['product_name']=record['food_name']
    if record['specification']['original_text']:result['spec']=record['specification']['original_text']
    return result
