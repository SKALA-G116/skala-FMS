"""
==============================================================================
FMS_FILE_SPEC
reconciliation.py - 완료 분석의 이력 보존형 재정리
==============================================================================
설명:
    - 완료 분석의 이력 보존형 재정리
입력·출력 명세:
    - 입력: 기존 분석 ID·원문 추출·검토 담당자 ID
    - 출력: 새 검토 결과·검토 Excel·완료 작업과 이전 분석 참조
실행 가정:
    - 기존 검토와 승인된 식품·단가를 덮어쓰지 않고 동일 정리 요청을 재사용
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
    2026-10-21  미지정      v0.1.0   파일 역할·입출력·가정·이력 명세 추가

    상세 Git 이력: git log --follow -- backend/app/domains/analysis/reconciliation.py
    공통 규칙: doc/file-header-policy.md

기존 모듈 설명:
    Create a new review revision from saved extraction; preserve all previous decisions.
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

from copy import deepcopy
import time
from backend.app.infrastructure.database import get,put,uid,now,Problem
from backend.app.domains.analysis.consolidation import enrich_tables,table_event,consolidate,VERSION
from backend.app.domains.catalog.record import validate_record


def preview(c,run_id):
    run=get(c,'analysis_run',run_id)
    if run['status']!='succeeded' or not run.get('agent_report_id'):
        raise Problem(409,'ANALYSIS_NOT_FINISHED','완료한 분석만 원문 기준으로 다시 정리할 수 있습니다.')
    original=get(c,'agent_report',run['agent_report_id'])
    extraction=get(c,'extraction',run['extraction_id'])
    if extraction['revision_id']!=run['document_revision_id']:
        raise Problem(409,'SOURCE_CHANGED','추출 원문이 분석 자료와 일치하지 않습니다.')
    segments=enrich_tables(extraction['segments'])
    rows=[table_event(s) for s in segments if s.get('food_record')]
    candidates=deepcopy(original['events'])
    for item in candidates:
        # Decisions are retained on the original report; the new revision requires review.
        for key in ('review','proposal_id','matched_product_id','matched_supplier_item_id','match_status'):
            item.pop(key,None)
    events,archive=consolidate(rows+candidates)
    for event in events:
        validate_record(event['food_record'])
        event['proposal_id']=None;event['match_status']='unresolved'
        event['review_reasons']=list(dict.fromkeys(event.get('uncertainties',[])+event.get('validation_warnings',[])))
        if event['kind']=='price' and not event.get('effective_from'):
            event['review_reasons'].append('원문에 적용 시작일이 없어 확인이 필요합니다. 날짜를 추정하지 않았습니다.')
    return run,original,events,archive


def rebuild(c,run_id,actor_id):
    """Only create a new draft result and Excel; never change approved catalog facts."""
    started=time.monotonic();get(c,'user',actor_id)
    get(c,'analysis_run',run_id,True)
    source,original,events,archive=preview(c,run_id)
    from backend.app.domains.ingestion.archives import state
    revision=get(c,'revision',source['document_revision_id'])
    if state(c,'document',revision['document_id'])['archived']:
        raise Problem(409,'DOCUMENT_ARCHIVED','삭제된 자료는 복구 후 정리해 주세요.')
    # Same source/report version produces one revision; new reviewer edits allow a fresh revision.
    token=f"{original['id']}:{original.get('version',1)}:{VERSION}"
    c.execute('SELECT pg_advisory_xact_lock(hashtext(%s))',('reconciliation:'+token,))
    previous=c.execute("SELECT data FROM app_records WHERE kind='analysis_run' AND data->>'reconciliation_key'=%s",(token,)).fetchone()
    if previous:return previous['data']
    stamp=now();run_id=uid();report_id=uid()
    run={'id':run_id,'document_revision_id':source['document_revision_id'],'extraction_id':source['extraction_id'],
        'workflow_profile':'auto','mode':source['mode'],'status':'succeeded','created_at':stamp,'finished_at':stamp,
        'agent_report_id':report_id,'source_analysis_run_id':source['id'],'reconciliation_key':token,'proposal_ids':[],'proposal_id':None}
    report={'id':report_id,'analysis_run_id':run_id,'document_revision_id':source['document_revision_id'],
        'model':'표 정규화 · 기존 AI 추출 재사용','model_calls':[],'events':events,'merged_events':archive,
        'status':'completed','version':1,'proposal_ids':[],'review_prepared':False,'export_asset_id':None,
        'created_at':stamp,'finished_at':stamp,'dto_schema':'food-change-dto-v1','processing_version':'food-record-v2',
        'plan':{'document_type':original['plan']['document_type'],'summary':'원본 표의 업체·품명·규격·단가·원재료를 직접 연결하고 중복 근거를 통합했습니다. 새 AI 호출 없이 정리했으며 이전 검토 기록은 원래 분석에 보존됩니다.','tasks':['normalize_tables','consolidate_candidates','create_review_excel']},
        'coverage':deepcopy(original['coverage']),'warnings':[],
        'consolidation':{'version':VERSION,'source_analysis_run_id':source['id'],'source_report_version':original.get('version',1),'input_events':len(original['events']),'review_items':len(events),'merged_or_excluded':len(archive),'new_model_calls':0,'actor_id':actor_id}}
    put(c,'analysis_run',run);put(c,'agent_report',report)
    from backend.app.domains.analysis.export import export_review
    output=export_review({'run_id':run_id,'revision_id':run['document_revision_id'],'agent_report_id':report_id,'review_mode':True},connection=c)
    from backend.app.domains.jobs.service import enqueue,savejob
    job=enqueue(c,'analyze',{'document_revision_id':run['document_revision_id'],'source_analysis_run_id':source['id'],'processing':'host-normalization'},run_id)
    job.update(status='succeeded',stage='원본 표 정규화·중복 통합 완료 (추가 AI 호출 없음)',processed_count=len(events),total_count=len(events),started_at=stamp,finished_at=now(),allowed_actions=[],result={'agent_report_id':report_id,**output,'proposal_ids':[]})
    savejob(c,job);run.update(job_id=job['id'],**output);put(c,'analysis_run',run)
    report=get(c,'agent_report',report_id);report['consolidation']['elapsed_seconds']=round(time.monotonic()-started,3);put(c,'agent_report',report)
    return run
