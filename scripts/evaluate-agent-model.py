"""
==============================================================================
FMS_FILE_SPEC
evaluate-agent-model.py - 개발·운영 보조 evaluate-agent-model
==============================================================================
설명:
    - 개발·운영 보조 evaluate-agent-model
입력·출력 명세:
    - 입력: CLI 인자·실행 환경·선택 입력 파일
    - 출력: 명령 결과·검증 기록·실행 프로세스
실행 가정:
    - 실제 작업과 읽기 전용 점검의 범위를 해당 CLI에서 확인
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

    상세 Git 이력: git log --follow -- scripts/evaluate-agent-model.py
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
from pathlib import Path
import asyncio,json,time,argparse,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.app.infrastructure.database import pool,tx,get
from backend.app.domains.analysis.planning import decide
from backend.app.domains.analysis.consolidation import enrich_tables
from backend.app.domains.analysis.provider import LocalModel
from backend.app.domains.analysis.schemas import event_schema
from backend.app.domains.analysis.agent import extraction_payload
parser=argparse.ArgumentParser(description='Read-only local Agent model evaluation; does not change catalog or review decisions.')
parser.add_argument('--run-id',required=True)
parser.add_argument('--model',required=True)
parser.add_argument('--output',default='.local/agent-rebuild/model-evaluation.json')
args=parser.parse_args()
pool.open();pool.wait()
with tx() as c:
 run=get(c,'analysis_run',args.run_id);ex=get(c,'extraction',run['extraction_id']);segments=enrich_tables(ex['segments'])
pool.close()
async def main():
 model=LocalModel();model.name=args.model;results=[]
 try:
  start=time.monotonic();plan=await decide(segments,'11월 시장조사 단가표',model.agenerate)
  results.append({'case':'실제 두 시트 단가표의 처리 도구 선택','seconds':round(time.monotonic()-start,2),'passed':len(plan['routes'])==2 and all(r['tool']=='normalize_table' for r in plan['routes']),'result':plan})
  for label,text,expected in [
   ('원재료·규격·업체','업체 바다천지. 식품명 간장(어간장). 1300ml/통. 원재료 국산생멸치75%,천일염25%,2년숙성. 조사가1 22900원, 적용가 0원. 공급 단가 변경 공지가 아니다.',{'kind':'food_profile','company_name':'바다천지','spec':'1300ml/통'}),
   ('공급 일시중단 공지','업체 테스트급식. 식품명 시험우유 200ml/개. 2026년 11월 1일부터 2026년 11월 5일까지 포장재 부족으로 일시 공급중단. 제조 단종은 아니다.',{'kind':'temporarily_unavailable','company_name':'테스트급식','effective_from':'2026-11-01','effective_to':'2026-11-05'})]:
   start=time.monotonic();result=await model.agenerate('추출 자료를 해석해 실제 식품별 사실을 JSON events로 반환하라. 단순 회사명·연락처·안내 제목은 품목이 아니다.',extraction_payload({'title':label,'assets':[]},'mixed',{'S1':{'text':text,'locator':{'kind':'html'}}}),event_schema(['S1']))
   events=result['events'];passed=len(events)==1 and all(events[0].get(k)==v for k,v in expected.items())
   if label.startswith('원재료'):passed=passed and events[0].get('amount') is None and '국산생멸치75%' in (events[0].get('attributes_text') or '')
   results.append({'case':label,'seconds':round(time.monotonic()-start,2),'passed':passed,'result':result})
  out={'model':model.name,'results':results,'calls':model.calls};Path(args.output).parent.mkdir(parents=True,exist_ok=True);Path(args.output).write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps(out,ensure_ascii=False))
 finally:await model.aclose()
asyncio.run(main())
