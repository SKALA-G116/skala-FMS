"""
==============================================================================
FMS_FILE_SPEC
planning.py - 프로젝트 설정 planning.py
==============================================================================
설명:
    - 프로젝트 설정 planning.py
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

    2026-10-22  김재현(Finn) v0.1.0   자료·Agent·검수 승인·식품 DB 중심 흐름 및 알레르기 표기 정리

    2026-10-22  김재현(Finn) v0.1.0   25MB·표 삽입 이미지 근거 보완 및 검수 오류 개선

    2026-10-22  김재현(Finn) v0.1.0   OCR 문장 좌표·상품 소속·필드 근거 보존 및 발표 자료 단순화

    상세 Git 이력: git log --follow -- backend/app/domains/analysis/planning.py
    공통 규칙: doc/file-header-policy.md

기존 모듈 설명:
    Agent-selected source tools; the host validates capabilities and complete coverage.
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

from copy import deepcopy
from collections import OrderedDict
import json
from backend.app.infrastructure.database import Problem
from backend.app.domains.analysis.schemas import PLAN

VERSION='food-agent-routing-v1'
TOOLS={
    'normalize_table':'이미 읽은 표의 열을 공통 식품 DTO로 매핑한다. 알려진 열이 충분한 경우 우선 사용한다.',
    'extract_text':'텍스트·비정형 표를 의미 단위로 해석하여 공통 DTO를 채운다.',
    'extract_image_regions':'OCR 좌표로 상품 영역·공통 범례를 먼저 판단하고 영역별로 공통 DTO를 채운다.',
    'request_review':'자동 해석하기에 자료가 부족하다. 원문을 보관하고 수동 확인이 필요함을 알린다.',
}


def sources(segments):
    grouped=OrderedDict()
    for segment in segments:
        loc=segment['locator'];key=(segment.get('asset_id'),loc['kind'],loc.get('sheet_name'),loc.get('page_number'),loc.get('embedded_image'))
        if key not in grouped:grouped[key]={'id':f'D{len(grouped)+1}','segments':[],'location':{k:loc[k] for k in ('kind','sheet_name','page_number','embedded_image','row_start','row_end') if k in loc}}
        grouped[key]['segments'].append(segment)
    return list(grouped.values())


def capabilities(source):
    items=source['segments'];tools=['extract_text','request_review']
    if any(s.get('food_record') for s in items):tools.insert(0,'normalize_table')
    if any(s['locator'].get('bbox') for s in items):tools.insert(0,'extract_image_regions')
    return tools


def manifest(source):
    items=source['segments'];indexes=sorted(set([0,min(1,len(items)-1),len(items)//2,len(items)-1]))
    return {'id':source['id'],'location':source['location'],'segment_count':len(items),
        'structured_rows':sum(bool(s.get('food_record')) for s in items),'available_tools':capabilities(source),
        'mapped_fields':list(next((s['food_record']['field_sources'] for s in items if s.get('food_record')),{})),
        'samples':[items[i]['text'][:80] for i in indexes]}


def schema_for(items):
    schema=deepcopy(PLAN)
    schema['properties']['routes']={'type':'array','minItems':len(items),'maxItems':len(items),'items':{
        'type':'object','additionalProperties':False,'properties':{
            'source_id':{'type':'string','enum':[s['id'] for s in items]},
            'tool':{'type':'string','enum':list(TOOLS)},'reason':{'type':'string','minLength':1,'maxLength':500}},
        'required':['source_id','tool','reason']}}
    schema['required'].append('routes')
    return schema


def validate_routes(plan,items):
    expected={s['id']:s for s in items};routes=plan.get('routes',[])
    if len(routes)!=len(expected) or {r['source_id'] for r in routes}!=set(expected):
        raise Problem(422,'AGENT_PLAN_COVERAGE','Agent 계획에 중복·누락된 자료가 있습니다. 원문을 생략하지 않고 중단했습니다.')
    for route in routes:
        if route['tool'] not in capabilities(expected[route['source_id']]):
            raise Problem(422,'AGENT_TOOL_UNAVAILABLE','자료에 사용할 수 없는 도구를 Agent가 선택했습니다.')
    return routes


async def decide(segments,title,call):
    items=sources(segments);routes=[];summaries=[];tasks=[];types=[]
    # Bounded inventories, never the full 500-row workbook or image bytes in a prompt.
    for offset in range(0,len(items),4):
        group=items[offset:offset+4]
        decision=await call('자료를 관찰하고 각 자료에 실행할 도구를 선택하라. 파일 확장자만으로 선택하지 말고 추출된 내용·열 인식 상태를 판단하라. 명확한 표는 normalize_table, 비정형 서술은 extract_text, 상품별 배치가 있는 OCR은 extract_image_regions, 읽을 수 없으면 request_review. 모든 source_id를 정확히 한 번 포함하고 이유를 밝혀라.',
            {'title':title[:160],'tools':TOOLS,'sources':[manifest(s) for s in group]},schema_for(group))
        routes.extend(validate_routes(decision,group));summaries.append(decision['summary']);tasks.extend(decision['tasks']);types.append(decision['document_type'])
    return {'version':VERSION,'document_type':types[0] if len(set(types))==1 else 'mixed','summary':' / '.join(summaries),
        'tasks':list(dict.fromkeys(tasks)),'routes':routes}


def selected_sources(plan,segments):
    items=sources(segments)
    if plan.get('version')!=VERSION:raise Problem(409,'AGENT_PLAN_OUTDATED','이전 고정 파이프라인 결과입니다. 새 분석을 시작해 주세요.')
    routes=validate_routes(plan,items);by_id={s['id']:s for s in items}
    return [(route,by_id[route['source_id']]) for route in routes]


def layout_schema(ids):
    refs={'type':'array','uniqueItems':True,'maxItems':2000,'items':{'type':'string','enum':ids}}
    return {'type':'object','additionalProperties':False,'properties':{
        'regions':{'type':'array','maxItems':40,'items':{'type':'object','additionalProperties':False,'properties':{
            'label':{'type':'string','maxLength':120},'source_ids':{**refs,'minItems':1},'context_ids':refs},'required':['label','source_ids','context_ids']}},
        'unassigned_ids':refs},'required':['regions','unassigned_ids']}


async def image_regions(source,call):
    lines=source['segments'];mapping={str(i+1):s for i,s in enumerate(lines)}
    # Region planning sees the entire page with coordinates. Never split a page into
    # arbitrary character windows and pretend those windows are product boundaries.
    overview=[[key,[round(v*1000) for v in s['locator'].get('bbox',[0,0,0,0])],s['text']] for key,s in mapping.items()]
    payload={'location':source['location'],'lines':overview,'coordinates':'[id,[x1,y1,x2,y2] 0~1000,full text]'}
    if len(json.dumps(payload,ensure_ascii=False).encode())>6500:
        raise Problem(422,'IMAGE_LAYOUT_BUDGET','이미지 한 페이지의 영역 판단 예산을 초과했습니다. 자료를 나누어 주세요. 일부 조각만으로 상품을 추정하지 않았습니다.')
    result=await call('OCR 좌표와 글을 보고 상품별 영역을 구분하라. 각 상품 이름·규격·단가·설명은 같은 regions 항목의 source_ids에 묶어라. 제목·업체·기간 같은 공통 안내만 context_ids에 연결한다. 원재료·가격·알레르기 표시는 상품 전용 source_ids에 넣고 다른 상품과 공유하지 마라. 가까운 거리만으로 묶지 말고 행·열·테두리·여백과 상품명을 함께 판단하라. source_ids는 서로 중복 불가, context_ids는 공유 가능. 모든 줄은 source_ids/context_ids/unassigned_ids 중 하나 이상에 반드시 넣어라. 상품 영역을 판단할 수 없는 줄은 unassigned_ids에 남겨 수동 확인하게 하라.',payload,layout_schema(list(mapping)))
    owned=[];covered=set();groups=[]
    owners=[key for region in result['regions'] for key in region['source_ids']]
    if len(owners)!=len(set(owners)):raise Problem(422,'IMAGE_REGION_COVERAGE','상품 전용 원문이 여러 상품에 중복 연결됐습니다.')
    owner_set=set(owners)
    for region in result['regions']:
        owned.extend(region['source_ids'])
        # A line owned by any product must never leak into another product as context.
        context=[key for key in region['context_ids'] if key not in owner_set]
        if context!=region['context_ids']:
            result.setdefault('normalization_notes',[]).append('상품 전용 근거의 공통 안내 공유를 차단했습니다.')
        region['context_ids']=context
        ids=list(dict.fromkeys(region['source_ids']+context));covered.update(ids)
        if not set(ids)<=set(mapping):raise Problem(422,'IMAGE_REGION_SOURCE','원문에 없는 이미지 영역 근거입니다.')
        group=[{**mapping[key],'region_label':region['label'],'source_role':'product' if key in region['source_ids'] else 'context'} for key in ids]
        if sum(len(s['text'].encode())+1 for s in group)>4000:
            raise Problem(422,'IMAGE_REGION_BUDGET','한 상품 영역의 추출 예산을 넘었습니다. 상품을 중간에서 잘라 처리하지 않았습니다.')
        groups.append(group)
    unassigned=list(dict.fromkeys(result['unassigned_ids']))
    if not set(unassigned)<=set(mapping):raise Problem(422,'IMAGE_REGION_SOURCE','원문에 없는 이미지 미분류 근거입니다.')
    # Redundant unassigned IDs do not negate a valid explicit region assignment.
    # Keep every source; unknown IDs and duplicate product ownership still fail.
    overlap=set(unassigned)&covered
    if overlap:
        unassigned=[key for key in unassigned if key not in covered]
        result['unassigned_ids']=unassigned
        result['normalization_notes']=['이미 배정된 근거의 중복 미분류 표시를 정리했습니다.']
    covered.update(unassigned)
    if len(owned)!=len(set(owned)) or covered!=set(mapping) or set(unassigned)&set(owned):
        raise Problem(422,'IMAGE_REGION_COVERAGE','상품 영역이 중복되거나 원문 줄이 누락됐습니다. 원문 확인이 필요합니다.')
    return groups,[mapping[key]['evidence_id'] for key in unassigned],result


def group_references(groups):
    return [[{k:s[k] for k in ('evidence_id','region_label','window_start','window_end','table_context','source_role') if k in s} for s in group] for group in groups]


def restore_groups(refs,segments,executions=None):
    by_id={s['evidence_id']:s for s in segments};groups=[]
    # Older checkpoints did not store product/context roles. Recover them from
    # the persisted layout decision; unknown ownership stays context-only.
    source_map={source['id']:source for source in sources(segments)};roles={}
    for trace in executions or []:
        layout=trace.get('layout') or {};source=source_map.get(trace.get('source_id'))
        if layout.get('method')=='explicit_spreadsheet_anchor':
            for eid in [*trace.get('evidence_ids',[]),layout.get('table_evidence_id')]:roles[(eid,None)]='product'
        elif source:
            lookup={str(i+1):row['evidence_id'] for i,row in enumerate(source['segments'])}
            all_owned={key for region in layout.get('regions',[]) for key in region['source_ids']}
            for region in layout.get('regions',[]):
                for key in region['source_ids']:roles[(lookup.get(key),region['label'])]='product'
                for key in region['context_ids']:
                    if key not in all_owned:roles[(lookup.get(key),region['label'])]='context'

    for group in refs:
        restored=[]
        for ref in group:
            source=by_id[ref['evidence_id']];text=source['text'][ref.get('window_start',0):ref.get('window_end',len(source['text']))]
            restored.append({**source,**ref,'text':text})
            if ref.get('region_label') and 'source_role' not in ref:
                restored[-1]['source_role']=roles.get((ref['evidence_id'],ref['region_label']),roles.get((ref['evidence_id'],None),'context'))
        groups.append(restored)
    return groups
