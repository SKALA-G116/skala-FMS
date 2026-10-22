"""
==============================================================================
FMS_FILE_SPEC
worker.py - 수집·분석·반영 작업 소비
==============================================================================
설명:
    - 수집·분석·반영 작업 소비
입력·출력 명세:
    - 입력: 영속 큐·실행 권한 fence·작업별 payload
    - 출력: 진행률·완료/실패/재개 상태와 결과 참조
실행 가정:
    - 작업 lease·취소·종료와 제한된 lane을 관리
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

    2026-10-21  미지정      v0.1.0   수집 진행 표시·갱신·완료 건수 수정

    2026-10-22  김재현(Finn) v0.1.0   자료·Agent·검수 승인·식품 DB 중심 흐름 및 알레르기 표기 정리

    상세 Git 이력: git log --follow -- backend/app/domains/jobs/worker.py
    공통 규칙: doc/file-header-policy.md

기존 모듈 설명:
    Durable queue consumer. Single worker by default; database claim/fencing prevents duplicates.
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

import time
import logging
import sys
import signal
import threading
import gc
import os
import socket
from concurrent.futures import ThreadPoolExecutor
from backend.app.runtime.execution import AnalysisYield
from psycopg.types.json import Jsonb
from backend.app.infrastructure.database import DSN
from backend.app.infrastructure.database import Problem
from backend.app.infrastructure.database import get
from backend.app.infrastructure.database import init
from backend.app.infrastructure.database import now
from backend.app.infrastructure.database import pool
from backend.app.infrastructure.database import put
from backend.app.infrastructure.database import tx
from backend.app.domains.jobs.service import savejob
from backend.app.domains.jobs.service import getjob
from backend.app.domains.review.application import apply
from backend.app.domains.analysis.workflow import run_analysis
from backend.app.domains.ingestion.collection import collect_source
from backend.app.domains.ingestion.collection import schedule_tick
from langgraph.checkpoint.postgres import PostgresSaver

def once(job_types=None):
    with tx() as c:
        row=c.execute("SELECT * FROM jobs WHERE (status='queued' OR (status='running' AND lease_until<now())) AND (%s::text[] IS NULL OR type=ANY(%s::text[])) ORDER BY coalesce(last_slice_at,created_at),created_at,id FOR UPDATE SKIP LOCKED LIMIT 1",(job_types,job_types)).fetchone()
        if not row:return False
        job=row['data'];job.update(status='running',stage='처리 중',started_at=job.get('started_at') or now(),last_started_at=now(),worker_pid=os.getpid(),worker_host=socket.gethostname());fence=row['fence']+1
        c.execute("UPDATE jobs SET status='running',data=%s,lease_until=now()+interval '15 minutes',fence=%s WHERE id=%s",(Jsonb(job),fence,job['id']))
    try:
        if job['type']=='analyze':
            with tx() as c:
                run=get(c,'analysis_run',job['analysis_run_id'],True);run['job_id']=job['id'];run['active_fence']=fence;put(c,'analysis_run',run)
            result=run_analysis(job['analysis_run_id'],row['payload']['document_revision_id']);output={k:result[k] for k in ('agent_report_id','export_asset_id') if k in result};output['proposal_ids']=result.get('proposal_ids') or ([result['proposal_id']] if result.get('proposal_id') else [])
        elif job['type']=='collect':
            with tx() as c:source=get(c,'source',row['payload']['source_id'])
            def progress(stage,processed):
                from backend.app.runtime.execution import STOP_REQUESTED
                if STOP_REQUESTED.is_set():raise AnalysisYield()
                with tx() as c:
                    current=c.execute('SELECT data,status,fence FROM jobs WHERE id=%s FOR UPDATE',(job['id'],)).fetchone()
                    if current['status']=='cancelled':raise Problem(409,'CANCELLED','취소된 작업입니다.')
                    if current['fence']!=fence:raise Problem(409,'LEASE_LOST','작업 실행 권한이 만료되었습니다.')
                    job.update(stage=stage,processed_count=processed);savejob(c,job)
                    c.execute("UPDATE jobs SET lease_until=now()+interval '15 minutes' WHERE id=%s",(job['id'],))
            output=collect_source(source['id'],row['payload'],progress)
            job['issues']=output.pop('issues')
        else:
            with tx() as c:
                lock=c.execute('SELECT status,fence FROM jobs WHERE id=%s FOR UPDATE',(job['id'],)).fetchone()
                if lock['fence']!=fence or lock['status']!='running':return True
                app=c.execute('SELECT data FROM applications WHERE id=%s FOR UPDATE',(row['payload']['application_id'],)).fetchone()['data']
                a=apply(c,app,row['payload']['actor_id']);output={'application_id':a['id']}
                job.update(status='succeeded',stage='반영 완료',finished_at=now(),processed_count=1,total_count=1,result=output,allowed_actions=[]);savejob(c,job)
            return True
        with tx() as c:
            lock=c.execute('SELECT status,fence FROM jobs WHERE id=%s FOR UPDATE',(job['id'],)).fetchone()
            if lock['fence']!=fence or lock['status']=='cancelled':return True
            issues=job['issues'];job=getjob(c,job['id'],True);job['issues']=issues
            count=len(output.get('document_ids',[])) if job['type']=='collect' and not output.get('connected') else job.get('total_count') or 1
            actionable=[issue for issue in job['issues'] if issue['code']!='SCAN_CONTINUES']
            job.update(status='partial' if actionable else 'succeeded',stage='일부 확인 필요' if actionable else '완료',finished_at=now(),processed_count=count,total_count=count,result=output,allowed_actions=[]);savejob(c,job)
            if job['analysis_run_id']:
                run=get(c,'analysis_run',job['analysis_run_id']);run.update(status='succeeded',finished_at=now());put(c,'analysis_run',run)
    except AnalysisYield:
        with tx() as c:
            row=c.execute('SELECT status,fence FROM jobs WHERE id=%s FOR UPDATE',(job['id'],)).fetchone()
            if row['status']=='running' and row['fence']==fence:
                latest=getjob(c,job['id']);latest.update(status='queued',stage='저장한 다음 구간부터 이어서 처리',continuations=latest.get('continuations',0)+1);savejob(c,latest);c.execute('UPDATE jobs SET lease_until=NULL,last_slice_at=now() WHERE id=%s',(job['id'],))
    except KeyboardInterrupt:
        with tx() as c:
            current=c.execute('SELECT status,fence FROM jobs WHERE id=%s FOR UPDATE',(job['id'],)).fetchone()
            if current and current['status']=='running' and current['fence']==fence:
                job.update(status='queued',stage='재시작 후 이어서 처리');savejob(c,job);c.execute('UPDATE jobs SET lease_until=NULL WHERE id=%s',(job['id'],))
        raise
    except Exception as ex:
        logging.exception('Job %s failed',job['id'])
        code=ex.code if isinstance(ex,Problem) else 'PROCESSING_FAILED';message=ex.message if isinstance(ex,Problem) else '처리 실패. 작업자 로그를 확인하세요.'
        with tx() as c:
            lock=c.execute('SELECT status,fence FROM jobs WHERE id=%s FOR UPDATE',(job['id'],)).fetchone()
            if lock['fence']!=fence or lock['status']=='cancelled':return True
            job=getjob(c,job['id'],True)
            manual=code=='MANUAL_REVIEW_REQUIRED'
            job.update(status='partial' if manual else 'failed',stage='원문 추출 완료 · 검토 필요' if manual else '확인 필요',finished_at=now(),issues=[{'code':code,'message':message,'retryable':not isinstance(ex,Problem)}],allowed_actions=['retry']);savejob(c,job)
            if job['analysis_run_id']:
                run=get(c,'analysis_run',job['analysis_run_id']);run.update(status='partial' if manual else 'failed',finished_at=now());put(c,'analysis_run',run)
                rev=get(c,'revision',run['document_revision_id']);doc=get(c,'document',rev['document_id']);doc['analysis_status']='partial' if manual else 'failed';put(c,'document',doc)
            if job['type']=='apply':
                app=c.execute('SELECT data FROM applications WHERE id=%s FOR UPDATE',(row['payload']['application_id'],)).fetchone()['data'];app['status']='conflict' if isinstance(ex,Problem) else 'failed';app['error']={'code':code,'message':message};c.execute('UPDATE applications SET data=%s WHERE id=%s',(Jsonb(app),app['id']))
                from backend.app.domains.review.proposals import bump
                p=get(c,'proposal',app['proposal_id'],True);p['summary']['status']='conflict' if isinstance(ex,Problem) else 'apply_failed';bump(p);put(c,'proposal',p)
    return True

def recover_abandoned_jobs():
    # Only reclaim same-host owners proven dead; a live or unknown owner keeps its lease.
    recovered=0
    with tx() as c:
        rows=c.execute("SELECT id,data,fence FROM jobs WHERE status='running' FOR UPDATE SKIP LOCKED").fetchall()
        for row in rows:
            job=row['data'];pid=job.get('worker_pid')
            if job.get('worker_host')!=socket.gethostname() or type(pid) is not int or pid<=0:continue
            try:os.kill(pid,0)
            except ProcessLookupError:
                job.update(status='queued',stage='저장한 진행 상태에서 재개 대기');savejob(c,job);c.execute('UPDATE jobs SET lease_until=NULL WHERE id=%s',(row['id'],));recovered+=1
            except PermissionError:pass
    return recovered

def main():
    init();recover_abandoned_jobs()
    with PostgresSaver.from_conn_string(DSN) as cp:cp.setup()
    stop=threading.Event()
    def shutdown(*_):
        from backend.app.runtime.execution import STOP_REQUESTED
        STOP_REQUESTED.set();stop.set()
    signal.signal(signal.SIGTERM,shutdown);signal.signal(signal.SIGINT,shutdown)
    def lane(kind):
        while not stop.is_set():
            try:
                if not once([kind]):stop.wait(.5)
                else:gc.collect()
            except Exception:logging.exception('Worker lane %s failed',kind);stop.wait(1)
    try:
        if '--once' in sys.argv:once();return
        # Separate bounded lanes prevent slow OCR/LLM from blocking collection or approval writes.
        with ThreadPoolExecutor(max_workers=3,thread_name_prefix='food-worker') as executor:
            futures=[executor.submit(lane,kind) for kind in ('collect','analyze','apply')]
            last_schedule=0
            while not stop.wait(1):
                if time.monotonic()-last_schedule>30:
                    try:schedule_tick()
                    except Exception:logging.exception('Scheduler tick failed')
                    last_schedule=time.monotonic()
                from backend.app.domains.ingestion.purge import cleanup_files
                from backend.app.parsers.ocr_pool import OCR
                try:cleanup_files();OCR.expire_idle()
                except Exception:logging.exception('Maintenance failed')
                for future in futures:
                    if future.done():future.result();raise RuntimeError('Worker lane stopped unexpectedly')
    finally:
        from backend.app.parsers.ocr_pool import OCR
        OCR.close();pool.close()

if __name__=='__main__':main()
