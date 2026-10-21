"""
==============================================================================
FMS_FILE_SPEC
matching.py - 프로젝트 설정 matching.py
==============================================================================
설명:
    - 프로젝트 설정 matching.py
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

    상세 Git 이력: git log --follow -- backend/app/domains/analysis/matching.py
    공통 규칙: doc/file-header-policy.md

기존 모듈 설명:
    Bounded read-only catalog tool selected by the Agent; no draft or catalog writes.
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

from backend.app.infrastructure.database import tx,get,put


def match_candidates(state):
    with tx() as c:
        report=get(c,'agent_report',state['agent_report_id'])
        cache={}
        for event in report['events']:
            if event.get('excluded_reason'):
                event['match_status']='unresolved';event['matched_product_id']=None;continue
            record=event['food_record'];name=record['food_name'];code=record.get('food_code')
            key=(code,name)
            if key not in cache:
                rows=c.execute("SELECT id,data FROM catalog_entities WHERE kind='product' AND (name=%s OR (%s::text IS NOT NULL AND data->>'common_food_code'=%s)) ORDER BY id LIMIT 6",(name,code,code)).fetchall()
                cache[key]=[{'id':str(r['id']),'name':r['data'].get('name'),'food_code':r['data'].get('food_code')} for r in rows]
            matches=cache[key];event['catalog_candidates']=matches
            event['matched_product_id']=matches[0]['id'] if len(matches)==1 else None
            event['match_status']='candidate' if len(matches)==1 else 'ambiguous' if matches else 'new_product'
        report.setdefault('tool_executions',[]).append({'tool':'match_catalog','reason':'Agent 처리 계획에서 DB 후보 조회를 선택했습니다.','queries':len(cache),'read_only':True})
        put(c,'agent_report',report)
    return {'proposal_ids':[]}
