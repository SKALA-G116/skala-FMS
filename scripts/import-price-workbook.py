"""
==============================================================================
FMS_FILE_SPEC
import-price-workbook.py - 개발·운영 보조 import-price-workbook
==============================================================================
설명:
    - 개발·운영 보조 import-price-workbook
입력·출력 명세:
    - 입력: CLI 인자·실행 환경·선택 입력 파일
    - 출력: 명령 결과·검증 기록·실행 프로세스
실행 가정:
    - 실제 작업과 읽기 전용 점검의 범위를 해당 CLI에서 확인
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

    상세 Git 이력: git log --follow -- scripts/import-price-workbook.py
    공통 규칙: doc/file-header-policy.md

기존 모듈 설명:
    Register an authorized local source for viewing; never applies business prices.
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

import argparse,sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.app.infrastructure.database import init,tx,pool
from backend.app.domains.pricing.workbooks import import_workbook,metadata
import hashlib

def main():
    parser=argparse.ArgumentParser();parser.add_argument('path');a=parser.parse_args();p=Path(a.path)
    if p.stat().st_size>20*1024*1024:raise SystemExit('파일은 20MB까지 지원합니다.')
    content=p.read_bytes();digest=hashlib.sha256(content).hexdigest();init()
    try:
        with tx() as c:
            old=c.execute('SELECT id FROM price_workbooks WHERE content_sha256=%s ORDER BY created_at LIMIT 1',(digest,)).fetchone()
            result=metadata(c,str(old['id'])) if old else import_workbook(c,p.stem,content,p.name)
            print(json.dumps({'id':result['id'],'sheets':[{'name':s['name'],'row_count':s['row_count'],'columns':len(s['columns'])} for s in result['sheets']]},ensure_ascii=False))
    finally:pool.close()
if __name__=='__main__':main()
