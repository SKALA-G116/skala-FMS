"""
==============================================================================
FMS_FILE_SPEC
inbox.py - 자료별 최신 분석 검수함 조회
==============================================================================
설명:
    - 자료별 최신 분석 검수함 조회
입력·출력 명세:
    - 입력: 로그인된 요청의 검색·상태·페이지 조건
    - 출력: 가져온 자료별 최신 분석 상태·nullable 품목 수·검수/진행 경로
실행 가정:
    - 내부 DB 반영 묶음을 검토 품목으로 노출하지 않고 전체 그룹에서 페이지를 적용
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

    2026-10-22  김재현(Finn) v0.1.0   자료·Agent·검수 승인·식품 DB 중심 흐름 및 알레르기 표기 정리

    2026-10-22  김재현(Finn) v0.1.0   자료 상태별 검수 대기 및 표 행의 동일 검토 DTO 연결

    상세 Git 이력: git log --follow -- backend/app/domains/review/inbox.py
    공통 규칙: doc/file-header-policy.md

기존 모듈 설명:
    A material inbox includes unprocessed documents and their current review result.
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

from backend.app.infrastructure.database import Problem
from backend.app.api.http import page


def aggregate_status(states,item_count):
    if states and all(s=='rejected' for s in states):return 'rejected'
    if 'rejected' in states and any(s not in ('rejected','superseded') for s in states):return 'conflict'
    active=[s for s in states if s not in ('superseded','rejected')]
    for state in ('apply_failed','applying','on_hold','conflict'):
        if state in active:return state
    if active and all(s=='applied' for s in active):return 'applied'
    if active and all(s in ('approved','applied') for s in active):return 'approved'
    return 'ready' if item_count else 'draft'


def document_reviews(c,document_id=None,revision_id=None):
    """One current material per row, including materials not ready for review yet."""
    rows=c.execute("""
        SELECT doc.id AS document_id,doc.data->>'title' AS title,
            coalesce(run.data->>'created_at',doc.data->>'collected_at',doc.created_at::text) AS created_at,
            run.id,coalesce(job.status,run.data->>'status') AS analysis_status,run.data->>'job_id' AS job_id,
            report.id AS report_id,report.data->>'status' AS report_status,
            jsonb_array_length(coalesce(report.data->'events','[]'::jsonb)) AS item_count,
            (SELECT count(*) FROM jsonb_array_elements(report.data->'events') e WHERE e#>>'{review,status}'='confirmed') AS confirmed_count,
            (SELECT count(*) FROM jsonb_array_elements(report.data->'events') e WHERE e#>>'{review,status}'='skipped') AS skipped_count,
            ARRAY(SELECT p.data#>>'{summary,status}' FROM app_records p WHERE p.kind='proposal' AND p.id IN
                (SELECT value::uuid FROM jsonb_array_elements_text(coalesce(report.data->'proposal_ids','[]'::jsonb)))) AS proposal_states
        FROM app_records doc
        JOIN app_records rev ON rev.kind='revision' AND rev.id=coalesce(%s::uuid,(doc.data->>'latest_revision_id')::uuid)
            AND rev.data->>'document_id'=doc.id::text
        LEFT JOIN LATERAL (SELECT r.id,r.data FROM app_records r WHERE r.kind='analysis_run'
            AND r.data->>'document_revision_id'=rev.id::text ORDER BY r.created_at DESC,r.id DESC LIMIT 1) run ON true
        LEFT JOIN jobs job ON job.id=(run.data->>'job_id')::uuid
        LEFT JOIN app_records report ON report.kind='agent_report' AND report.id=(run.data->>'agent_report_id')::uuid
        WHERE doc.kind='document' AND (%s::uuid IS NULL OR doc.id=%s::uuid)
            AND NOT EXISTS (SELECT 1 FROM record_archives a WHERE a.record_kind='document' AND a.record_id=doc.id AND a.archived)
        ORDER BY doc.created_at DESC,doc.id DESC LIMIT 2001
    """,(revision_id,document_id,document_id)).fetchall()
    if len(rows)>2000:raise Problem(422,'DATASET_LIMIT','검수함 조회 상한을 넘었습니다. 검색 범위를 나누어 주세요.')
    items=[]
    for row in rows:
        count=row['item_count'];confirmed=row['confirmed_count'];skipped=row['skipped_count']
        ready=row['report_status']=='completed' and row['analysis_status'] in ('succeeded','partial')
        status=aggregate_status(row['proposal_states'],count) if ready else (row['analysis_status'] or 'not_analyzed')
        if not ready and status=='succeeded':status='not_analyzed'
        href='/analysis-runs/'+str(row['id'])+'/review' if ready else '/jobs/'+row['job_id'] if row['job_id'] else '/documents/'+str(row['document_id'])
        items.append({'id':str(row['id'] or row['document_id']),'kind':'analysis','document_id':str(row['document_id']),
            'analysis_run_id':str(row['id']) if row['id'] else None,'report_id':str(row['report_id']) if row['report_id'] else None,
            'review_ready':ready,'analysis_status':row['analysis_status'] or 'not_analyzed',
            'title':row['title'],'status':status,'item_count':count if ready else None,
            'pending_count':count-confirmed-skipped if ready else None,'confirmed_count':confirmed,'skipped_count':skipped,
            'created_at':row['created_at'],'href':href})
    return items


def list_inbox(c,query):
    items=document_reviews(c)
    # Explicit manual commands remain separate and retain their original approval controls.
    manual=c.execute("SELECT id,data->'summary' AS summary FROM app_records WHERE kind='proposal' AND nullif(data->>'analysis_run_id','') IS NULL ORDER BY created_at DESC LIMIT 2001").fetchall()
    if len(items)+len(manual)>2000:raise Problem(422,'DATASET_LIMIT','검수함 조회 상한을 넘었습니다.')
    for row in manual:
        s=row['summary'];items.append({'id':str(row['id']),'kind':'manual','title':s['title'],'status':s['status'],
            'item_count':s['change_count'],'pending_count':None,'created_at':s['created_at'],'href':'/reviews/'+str(row['id'])})
    if query.get('kind'):items=[item for item in items if item['kind']==query['kind']]
    status=query.get('status');text=query.get('q','').casefold()
    items=[item for item in items if (not status or item['status']==status or status=='ready' and item['status'] in ('draft','conflict','not_analyzed','queued','running','failed','cancelled','partial')) and (not text or text in item['title'].casefold())]
    return page(items,query,c)
