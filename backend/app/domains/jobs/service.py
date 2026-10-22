"""
==============================================================================
FMS_FILE_SPEC
service.py - 영속 작업의 등록·조회·상태 저장
==============================================================================
설명:
    - 영속 작업의 등록·조회·상태 저장
입력·출력 명세:
    - 입력: 작업 종류·payload·분석 실행/상위 작업 참조
    - 출력: 작업 ID와 작업 상태 DTO
실행 가정:
    - 실제 처리는 별도 worker가 수행
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

    2026-10-22  김재현(Finn) v0.1.0   자료·Agent·검수 승인·식품 DB 중심 흐름 및 알레르기 표기 정리

    상세 Git 이력: git log --follow -- backend/app/domains/jobs/service.py
    공통 규칙: doc/file-header-policy.md
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
from psycopg.types.json import Jsonb
from backend.app.infrastructure.database import Problem
from backend.app.infrastructure.database import now
from backend.app.infrastructure.database import uid

def enqueue(c,kind,payload,run=None,parent=None):
    job={'id':uid(),'type':kind,'status':'queued','stage':'대기 중','processed_count':0,'total_count':None,'attempt':1,'created_at':now(),'started_at':None,'finished_at':None,'parent_job_id':parent,'issues':[],'result':None,'allowed_actions':['cancel'] if kind!='apply' else [],'analysis_run_id':run}
    c.execute('INSERT INTO jobs(id,type,data,payload) VALUES(%s,%s,%s,%s)',(job['id'],kind,Jsonb(job),Jsonb(payload)));return job

def getjob(c,id,lock=False):
    r=c.execute('SELECT data FROM jobs WHERE id=%s'+(' FOR UPDATE' if lock else ''),(id,)).fetchone()
    if not r:raise Problem(404,'NOT_FOUND','작업을 찾을 수 없습니다.')
    return r['data']

def stamp_stage(j):
    stage=j.get('stage')
    history=j.setdefault('stage_history',[])
    if stage and (not history or history[-1]['stage']!=stage):history.append({'at':now(),'stage':stage})
    j['stage_history']=history[-100:]

def savejob(c,j):
    stamp_stage(j)
    c.execute('UPDATE jobs SET data=%s,status=%s WHERE id=%s',(Jsonb(j),j['status'],j['id']))
