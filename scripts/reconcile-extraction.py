#!/usr/bin/env python3
"""
==============================================================================
FMS_FILE_SPEC
reconcile-extraction.py - 저장된 추출 결과 재정리 CLI
==============================================================================
설명:
    - 저장된 추출 결과 재정리 CLI
입력·출력 명세:
    - 입력: --run-id·--dry-run 또는 기존 검토 담당 --actor
    - 출력: 두 품목 등 정리 미리보기 또는 새 검토 URL
실행 가정:
    - 추가 OCR/LLM 호출 없이 새 초안을 만들며 기존 검토를 보존
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

    상세 Git 이력: git log --follow -- scripts/reconcile-extraction.py
    공통 규칙: doc/file-header-policy.md

기존 모듈 설명:
    Preview or rebuild a saved analysis without repeating OCR/LLM or overwriting review history.
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

import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.app.infrastructure.database import pool,tx,Problem
from backend.app.domains.analysis.reconciliation import preview,rebuild


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id',required=True)
    parser.add_argument('--actor',help='Existing admin/reviewer username; required when creating a result')
    parser.add_argument('--dry-run',action='store_true')
    args=parser.parse_args()
    pool.open();pool.wait()
    try:
        with tx() as c:
            if args.dry_run:
                source,original,events,archive=preview(c,args.run_id)
                print(json.dumps({'source_run_id':source['id'],'before':len(original['events']),'after':len(events),'items':[{'name':e['product_name'],'company':e['food_record']['company_name'],'spec':e['spec'],'source_price':e['food_record']['prices']['source_applied']} for e in events]},ensure_ascii=False))
            else:
                actor=c.execute("SELECT data FROM app_records WHERE kind='user' AND data->>'username'=%s",(args.actor,)).fetchone()
                if not actor or not set(actor['data']['roles'])&{'admin','reviewer'}:raise Problem(403,'REVIEW_ROLE','기존 검토 담당 계정을 --actor로 지정하세요.')
                result=rebuild(c,args.run_id,actor['data']['id'])
                print(json.dumps({'analysis_run_id':result['id'],'review_url':'http://127.0.0.1:8100/analysis-runs/'+result['id']+'/review'},ensure_ascii=False))
    finally:pool.close()


if __name__=='__main__':main()
