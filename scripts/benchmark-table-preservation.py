"""
==============================================================================
FMS_FILE_SPEC
benchmark-table-preservation.py - 개발·운영 보조 benchmark-table-preservation
==============================================================================
설명:
    - 개발·운영 보조 benchmark-table-preservation
입력·출력 명세:
    - 입력: CLI 인자·실행 환경·선택 입력 파일
    - 출력: 명령 결과·검증 기록·실행 프로세스
실행 가정:
    - 실제 작업과 읽기 전용 점검의 범위를 해당 CLI에서 확인
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

    2026-10-22  김재현(Finn) v0.1.0   발표·비교 자료 및 바이너리 외부 명세 지원

    상세 Git 이력: git log --follow -- scripts/benchmark-table-preservation.py
    공통 규칙: doc/file-header-policy.md

기존 모듈 설명:
    Replay a local XLSX against previous and current table mapping/merge code.
    
    Read-only. No model calls, DB access, or workbook upload. The record DTO helper is
    shared from the current checkout, so this isolates parser/consolidation changes.
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

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.app.parsers.documents import parse
from backend.app.domains.analysis.consolidation import table_event,consolidate


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('xlsx',type=Path)
    parser.add_argument('--before-ref',default='13e484758efe54acf50bf591bf8e27aab5295a42')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    def previous(path):
        ns={'__name__':'benchmark_previous'}
        code=subprocess.check_output(['git','show',args.before_ref+':'+path],cwd=root)
        exec(compile(code,path,'exec'),ns)
        return ns
    old_parse=previous('backend/app/parsers/documents.py')['parse']
    old_merge=previous('backend/app/domains/analysis/consolidation.py')['consolidate']
    result={'input_sha256':hashlib.sha256(args.xlsx.read_bytes()).hexdigest(),
        'before_ref':args.before_ref,'after_ref':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
        'method':'동일 XLSX의 이전/현재 파서·통합 코드 재실행. record DTO helper는 현재 코드 공유. 모델·DB·네트워크 제외. 지연시간 비교 아님.', 'results':{}}
    for label,parse_fn,merge_fn in [('before',old_parse,old_merge),('after',parse,consolidate)]:
        rows=parse_fn(args.xlsx,args.xlsx.name)
        for i,row in enumerate(rows):row['evidence_id']=f'E{i}'
        events=[table_event(row) for row in rows if row.get('food_record')]
        kept,archive=merge_fn(events)
        result['results'][label]={'parsed_rows':len(events),'review_rows':len(kept),'merged_rows':len(archive),
            'flavor_rows':sum(bool(e['food_record']['attributes']['flavor']) for e in kept),
            'numeric_price_values':sum(q['amount'] is not None for e in kept for q in e['food_record']['prices'].get('source_columns') or []),
            'row_extraction_llm_calls':0,
            'rows':[{'food_name':e['food_record']['food_name'],'flavor':e['food_record']['attributes']['flavor'],'spec':e['spec'],'prices':e['food_record']['prices'].get('source_columns')} for e in kept]}
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(json.dumps({k:{x:y for x,y in v.items() if x!='rows'} for k,v in result['results'].items()},ensure_ascii=False))

if __name__=='__main__':main()
