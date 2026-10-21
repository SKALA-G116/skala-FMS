"""
==============================================================================
FMS_FILE_SPEC
service.py - 영속 분석 작업 등록
==============================================================================
설명:
    - 영속 분석 작업 등록
입력·출력 명세:
    - 입력: DB connection·문서 revision·재분석 여부
    - 출력: 분석 실행과 queued 작업 또는 기존 작업 참조
실행 가정:
    - HTTP 트랜잭션 안에서 실제 추론을 수행하지 않음
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

    상세 Git 이력: git log --follow -- backend/app/domains/analysis/service.py
    공통 규칙: doc/file-header-policy.md

기존 모듈 설명:
    Register durable analysis without calling an LLM inside the HTTP transaction.
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

from backend.app.infrastructure.database import get
from backend.app.infrastructure.database import put
from backend.app.infrastructure.database import uid
from backend.app.infrastructure.database import now
from backend.app.domains.jobs.service import enqueue
from backend.app.domains.jobs.service import getjob

def queue_analysis(c,revision_id,force=False):
    from backend.app.domains.ingestion.archives import state
    revision=get(c,'revision',revision_id);get(c,'document',revision['document_id'],True)
    if state(c,'document',revision['document_id'])['archived']:return None,None
    c.execute('SELECT pg_advisory_xact_lock(hashtext(%s))',('analysis:'+revision_id,))
    rev=get(c,'revision',revision_id)
    existing=c.execute("SELECT data FROM app_records WHERE kind='analysis_run' AND data->>'document_revision_id'=%s ORDER BY created_at DESC LIMIT 1",(revision_id,)).fetchone()
    if existing and existing['data'].get('job_id') and (not force or getjob(c,existing['data']['job_id'])['status'] in ('queued','running')) and existing['data'].get('mode')==__import__('os').getenv('FOOD_ANALYSIS_MODE','agent'):return existing['data'],None
    run={'id':uid(),'document_revision_id':revision_id,'workflow_profile':'auto','status':'queued','created_at':now(),'mode':__import__('os').getenv('FOOD_ANALYSIS_MODE','agent')}
    if rev.get('extraction_ids') and not rev.get('parse_issues'):run['extraction_id']=rev['extraction_ids'][-1]
    job=enqueue(c,'analyze',{'document_revision_id':revision_id,'workflow_profile':'auto'},run['id']);run['job_id']=job['id'];put(c,'analysis_run',run)
    doc=get(c,'document',rev['document_id']);doc['analysis_status']='queued';put(c,'document',doc);return run,job
