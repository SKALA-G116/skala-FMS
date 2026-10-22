"""
==============================================================================
FMS_FILE_SPEC
approval.py - 프로젝트 설정 approval.py
==============================================================================
설명:
    - 프로젝트 설정 approval.py
입력·출력 명세:
    - 입력: 도구별 설정·실행 환경
    - 출력: 해당 도구의 구성 또는 실행 결과
실행 가정:
    - 실제 비밀값과 로컬 실행 데이터는 Git에서 제외
작성 정보:
    - 작성자: 김재현(Finn)
    - 이메일: penguin.klg@gmail.com
    - 작성일: 2026-10-22 (최초 Git 등록일 기준)
    - 라이선스: 미지정
    - 버전: 0.1.0
    - 상태: Development
변경 이력 (Revision History):
    DATE        AUTHOR      VERSION  DESCRIPTION
    --------------------------------------------------------------------
    2026-10-22  미지정      v0.1.0   파일 역할·입출력·가정·이력 명세 추가

    2026-10-22  김재현(Finn) v0.1.0   자료·Agent·검수 승인·식품 DB 중심 흐름 및 알레르기 표기 정리

    상세 Git 이력: git log --follow -- backend/app/domains/review/approval.py
    공통 규칙: doc/file-header-policy.md

기존 모듈 설명:
    One human approval command; existing validation, decisions and durable apply jobs remain authoritative.
==============================================================================
"""

# FMS_MODULE_METADATA_BEGIN
__author__ = '김재현(Finn)'
__email__ = 'penguin.klg@gmail.com'
__version__ = "0.1.0"
__status__ = "Development"
# FMS_MODULE_METADATA_END

# ---------------------------------------------------------------------------
# 1. Imports / Module implementation
# ---------------------------------------------------------------------------

from types import SimpleNamespace
from backend.app.infrastructure.database import Problem,get
from backend.app.api.http import RequestContext,etag
from backend.app.domains.review.items import prepare


def approve_review(c,runid,payload,actor):
    if not isinstance(payload,dict) or set(payload)!={'version'} or type(payload['version']) is not int:
        raise Problem(422,'REVIEW_INPUT','최신 검토 버전이 필요합니다.')
    run=get(c,'analysis_run',runid,True)
    if not run.get('agent_report_id'):raise Problem(409,'NOT_READY','분석이 끝난 뒤 승인하세요.')
    report=get(c,'agent_report',run['agent_report_id'],True)
    if payload['version']!=report.get('version',1):raise Problem(409,'REVIEW_CHANGED','다른 검토 내용이 저장됐습니다. 다시 조회하세요.')
    current=[get(c,'proposal',pid,True) for pid in report['proposal_ids']]
    protected=any(p['summary']['status'] in ('approved','applying','applied','apply_failed') for p in current)
    if not protected:
        prepared=prepare(c,runid,payload,actor['id'])
        current=[get(c,'proposal',pid,True) for pid in prepared['proposal_ids']]
    if not current:raise Problem(422,'NOTHING_CONFIRMED','확인한 품목이 없습니다.')
    from backend.app.domains.review.api import handle
    jobs=[]
    # All decisions and enqueues share the outer transaction: any blocker rolls
    # back the entire approval request. Workers only see committed jobs.
    for proposal in current:
        summary=proposal['summary'];pid=summary['id']
        if summary['blocking_count']:raise Problem(422,'REVIEW_BLOCKED','반영 전에 품목 정보를 확인해 주세요.',proposal['issues'])
        def command(action,body):
            return handle(RequestContext(c,SimpleNamespace(headers={'if-match':etag(get(c,'proposal',pid))}),'POST',{},body,None,actor,'proposals/'+pid+'/'+action)).data
        if summary['status']=='ready':
            proposal=command('decisions',{'action':'approve','revision':summary['revision'],'reason':'품목별 원문 대조 후 승인·DB 반영'})
        if proposal['summary']['status']=='approved':
            applied=command('applications',{'approved_revision':proposal['summary']['approved_revision']});jobs.append(applied['job'])
        elif proposal['summary']['status'] not in ('applying','applied'):
            raise Problem(409,'REVIEW_BLOCKED','반영 상태를 확인하세요. 실패한 반영은 처리 현황에서 재시도할 수 있습니다.')
    return {'report':get(c,'agent_report',report['id']),'jobs':jobs,'proposal_ids':[p['summary']['id'] for p in current]}
