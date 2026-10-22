#!/usr/bin/env python3
"""
==============================================================================
FMS_FILE_SPEC
file-specs.py - 파일 명세·변경 이력 관리
==============================================================================
설명:
    - 파일 명세·변경 이력 관리
입력·출력 명세:
    - 입력: --apply·--refresh·--check 옵션과 Git 파일 목록
    - 출력: 언어별 헤더·파일별 명세 목록·무결성 검사 결과
실행 가정:
    - 원본·잠금·엄격한 데이터 형식을 보존하고 실명 정보를 추정하지 않음
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

    2026-10-21  미지정      v0.1.0   표 정규화·재정리 모듈 명세 등록

    2026-10-21  미지정      v0.1.0   검수함을 내부 변경 묶음에서 자료별 분석 결과로 전환

    2026-10-21  김재현(Finn) v0.1.0   Agent 도구 선택 기반 리빌드·업무 경계 및 검증

    2026-10-22  김재현(Finn) v0.1.0   발표·비교 자료 및 바이너리 외부 명세 지원

    상세 Git 이력: git log --follow -- scripts/file-specs.py
    공통 규칙: doc/file-header-policy.md

기존 모듈 설명:
    Apply source headers and maintain a format-safe file specification inventory.
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

import argparse
import ast
import hashlib
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = 'doc/file-manifest.json'
INDEX = 'doc/file-specs.md'
GENERATED = {MANIFEST, INDEX}
MARKER = 'FMS_FILE_SPEC'
UNKNOWN = '미지정'
AUTHOR = '김재현(Finn)'
EMAIL = 'penguin.klg@gmail.com'
VERSION = '0.1.0'

ROLES = {
 'review/inbox.py': ('자료별 최신 분석 검수함 조회', '로그인된 요청의 검색·상태·페이지 조건', '자료별 최신 완료 분석 한 행·실제 항목/대기 수·검토 경로', '내부 DB 반영 묶음을 검토 품목으로 노출하지 않고 전체 그룹에서 페이지를 적용'),
 'analysis/consolidation.py': ('원본 표 정규화·추출 후보 중복 통합', '근거 ID를 가진 원문 구간·표 행·AI 추출 후보', '표준 DTO 후보·통합 출처·분리한 충돌 및 제외 이력', 'OCR/LLM을 호출하지 않고 모호한 업체·규격·가격·기간을 합치지 않음'),
 'analysis/reconciliation.py': ('완료 분석의 이력 보존형 재정리', '기존 분석 ID·원문 추출·검토 담당자 ID', '새 검토 결과·검토 Excel·완료 작업과 이전 분석 참조', '기존 검토와 승인된 식품·단가를 덮어쓰지 않고 동일 정리 요청을 재사용'),
 'analysis/agent.py': ('LLM 계획·추출과 근거 연결', '분할 원문 구간·JSON 스키마·분석 실행 ID', '표준 식품 변경 후보·근거·모델 호출 기록', '모델 후보는 승인이나 DB 반영을 대신하지 않음'),
 'analysis/workflow.py': ('LangGraph 분석 흐름', '분석 실행 ID·원본 revision ID·저장된 checkpoint', '추출·계획·해석·연결·Excel 단계의 결과 ID', '큰 원문은 저장소에 두고 checkpoint는 ID 위주로 유지'),
 'analysis/provider.py': ('Ollama 비동기 구조화 추론', '작업명·원문 payload·응답 JSON 스키마', '검증한 JSON과 호출 시간·토큰 기록', '추론 동시성·입력 크기·timeout을 제한하고 HTTP client를 정리'),
 'analysis/service.py': ('영속 분석 작업 등록', 'DB connection·문서 revision·재분석 여부', '분석 실행과 queued 작업 또는 기존 작업 참조', 'HTTP 트랜잭션 안에서 실제 추론을 수행하지 않음'),
 'analysis/export.py': ('근거를 포함한 검토 Excel 생성', '분석 보고서·검토된 식품 후보·원문 근거', 'Excel bytes 또는 저장한 export asset 참조', '원문 문자열을 수식으로 실행하지 않고 DB 승인과 구분'),
 'analysis/schemas.py': ('LLM 계획·추출 응답 스키마', '문서 유형·지원하는 식품 변경 종류', '검증 가능한 JSON Schema 정의', '스키마 적합성이 식품 사실의 정확성을 보장하지 않음'),
 'catalog/record.py': ('표준 FoodRecord DTO와 정규화', '업체별 표 행·본문 추출값·규격·알레르기 문구', 'food-record-v2의 nullable 식품 정보와 필드 근거', '공란과 0, 알레르기 후보와 함유 표시를 구분'),
 'catalog/queries.py': ('식품·규격·단가의 시점별 조회', 'DB connection·식품/공급 품목 ID·조회 기준일', '현재 또는 예약 사실을 조합한 조회 DTO', '읽기 책임을 유지하며 승인된 변경 반영은 review.application이 담당'),
 'review/application.py': ('승인된 변경의 원자적 DB 반영', 'DB connection·승인 application·행위자', '업무 사실·식품 profile·감사 이력·반영 상태', '승인 revision·원문·대상 버전·기간을 재검사하고 오류 시 전체 롤백'),
 'review/items.py': ('추출 품목의 사용자 검토와 반영 준비', '분석/품목 ID·보고서 버전·수정 필드·검토 상태·행위자', '버전이 갱신된 검토 보고서 또는 변경안 참조', '품목 확인 저장은 최종 승인·DB 반영과 다름'),
 'review/proposals.py': ('변경안 검증과 승인 상태 전이', '원문 revision·변경 연산·근거·현재 변경안', '확인 사항·허용 동작·버전·revision 이력', '근거와 대상 관계·적용 기간을 확인한 뒤 허용된 전이만 수행'),
 'ingestion/collection.py': ('게시글·첨부 수집과 변경 감지', '허용된 source·게시판·수집 옵션·진행 콜백', '원본 revision·첨부 asset·수집 결과·분석 작업 참조', '동일 원본 중복 수집을 구분하고 접근 실패를 숨기지 않음'),
 'ingestion/connections.py': ('사이트 연결 정보의 암호화 보관', 'source ID·사용자가 입력한 회원 연결 설정', '암호화 저장 정보 또는 비밀을 제거한 공개 상태', '실제 계정과 암호화 키를 Git·응답·로그에 노출하지 않음'),
 'ingestion/documents.py': ('원본 파일·문서 revision 등록', '파일명·제목·bytes·선택 source 정보', '내용 해시·asset·문서·revision DTO', '파일 크기를 제한하고 실제 업무 사실 반영과 분리'),
 'ingestion/archives.py': ('자료·식품의 삭제 보관과 복구', '대상 종류/ID·보관 버전·행위자·사유', '갱신된 보관 상태와 버전', '활성 작업과 승인 근거의 일관성을 유지'),
 'ingestion/purge.py': ('자료 선택·일괄 작업과 조건부 영구 삭제', '검색 조건 또는 삭제 보관된 자료 ID·버전·행위자', '항목별 성공/실패와 파일 정리 결과', '승인된 사실이 참조하는 근거와 공유 파일을 보호'),
 'pricing/workbooks.py': ('원본 단가표·시트·열 조회', 'workbook/asset ID·시트·헤더 행·필터·정렬·페이지 조건', '원본 열 metadata와 페이지 행 DTO', '원본 자료 가격을 승인된 공급 단가와 구분'),
 'pricing/proposals.py': ('표 행의 가격 변경안 준비', '시트 ID·선택 행·열 연결·단가 적용 기준', '검토용 변경안 참조와 확인 사항', '표 등록만으로 상품·단가 사실을 확정하지 않음'),
 'identity/service.py': ('세션 인증·로그인과 역할 검사', '요청 쿠키·CSRF·로그인 입력·역할 목록', '인증된 사용자·세션 응답 또는 인증 오류', '비밀번호 해시를 검사하고 공개 사용자 정보에서 해시를 제거'),
 'jobs/service.py': ('영속 작업의 등록·조회·상태 저장', '작업 종류·payload·분석 실행/상위 작업 참조', '작업 ID와 작업 상태 DTO', '실제 처리는 별도 worker가 수행'),
 'jobs/worker.py': ('수집·분석·반영 작업 소비', '영속 큐·실행 권한 fence·작업별 payload', '진행률·완료/실패/재개 상태와 결과 참조', '작업 lease·취소·종료와 제한된 lane을 관리'),
}
VIEWS = {'ExtractionReview':'품목 선택·원문 대조·수정·최종 반영','FoodCatalog':'표준 식품 목록과 삭제·복구','Catalog':'식품 상세·규격·연결 정보','Documents':'자료 등록·선택·삭제·복구·영구 삭제','Prices':'승인된 단가 조회','Reference':'원본 자료·근거·표 조회','Reviews':'검토할 변경안 목록','CreateReview':'수동 검토 변경안 작성','Sources':'사이트 연결·업데이트 수집','Jobs':'비동기 작업 상태·취소·재시도','Dashboard':'업무 집계와 주요 화면 진입'}
COMPONENTS = {'FoodRecordForm':'표준 식품 정보 편집','FoodRecordTable':'표준 식품 DTO의 공통 열 표시','SourceComparison':'원본 이미지·추출 텍스트 비교','ArchiveDialog':'삭제 보관·복구 결정','DocumentBatchDialog':'선택 자료의 일괄 작업','WorkbookTable':'원본 시트·열 필터 조회','TableProposalWizard':'표 행에서 가격 변경안 준비','ImageEvidence':'이미지 근거 위치 표시','EvidenceViewer':'변경 필드와 원문 근거 조회','CursorPager':'커서 기반 페이지 이동','StatusBadge':'상태 표시'}


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True)


def paths():
    return sorted(path for path in set(git('ls-files', '--cached', '--others', '--exclude-standard').splitlines()) | GENERATED if (ROOT/path).is_file() or path in GENERATED)


def history():
    result = {}
    for block in git('log', '--reverse', '--format=%x1e%H%x1f%aI%x1f%s', '--name-only').split('\x1e')[1:]:
        lines = block.strip().splitlines()
        sha, stamp, subject = lines[0].split('\x1f', 2)
        for name in lines[1:]:
            if name.strip():
                result.setdefault(name, []).append({'commit': sha, 'date': stamp, 'subject': subject})
    return result


def spec(path):
    p = Path(path)
    if path == 'scripts/reconcile-extraction.py':
        return ('저장된 추출 결과 재정리 CLI', '--run-id·--dry-run 또는 기존 검토 담당 --actor', '두 품목 등 정리 미리보기 또는 새 검토 URL', '추가 OCR/LLM 호출 없이 새 초안을 만들며 기존 검토를 보존')
    if path == 'scripts/file-specs.py':
        return ('파일 명세·변경 이력 관리', '--apply·--refresh·--check 옵션과 Git 파일 목록', '언어별 헤더·파일별 명세 목록·무결성 검사 결과', '원본·잠금·엄격한 데이터 형식을 보존하고 실명 정보를 추정하지 않음')
    if path.startswith('legacy/'):
        return ('제공 ZIP 원본 참조', '기존 장애 진단 실습 코드·예제', '원본 참조 자료', '신규 식품 서비스 기본 실행 경로에서 분리한 원본이므로 내용 유지')
    if '/domains/' in path:
        key = path.split('/domains/', 1)[1]
        if key in ROLES:
            return ROLES[key]
        domain = key.split('/')[0]
        if p.name == 'api.py':
            return (f'{domain} 도메인 HTTP 유스케이스', '인증·권한·CSRF를 확인한 RequestContext와 경로/조회/본문', 'DomainResult 또는 HTTP Response', '공통 transport가 소유한 같은 DB 트랜잭션을 사용')
    if path == 'backend/app/api/main.py':
        return ('FastAPI 애플리케이션 조립', '실행 환경·도메인 router·HTTP 요청', 'ASGI app·정적 화면·health·오류 응답', '수명 관리·보안 미들웨어를 조합하고 업무 처리는 도메인에 위임')
    if path == 'backend/app/api/transport.py':
        return ('공통 HTTP 보안·트랜잭션 경계', 'Request·파일 또는 JSON payload', '인증/권한 검사 후 도메인 응답과 중복 요청 결과', '업로드 크기·동시성·CSRF·Idempotency-Key를 검사')
    if path == 'backend/app/api/http.py':
        return ('HTTP 공통 DTO와 응답 보조 함수', 'RequestContext·결과 data/status/headers·버전·페이지 조건', 'DomainResult·오류/ETag/페이지 DTO', '공통 표현 계층이며 도메인 업무 규칙을 추가하지 않음')
    if path == 'backend/app/api/routing.py':
        return ('명시적 FastAPI 도메인 라우터 생성', '도메인명·경로·HTTP method 목록', '고유 operation ID와 path parameter를 갖는 APIRouter', '실제 요청 처리는 공통 transport에 위임')
    if path == 'backend/app/infrastructure/database.py':
        return ('PostgreSQL 연결·저장 공통 함수', 'DATABASE_URL·connection·레코드 종류/ID·저장 객체', '트랜잭션·관계형/JSONB 레코드와 공통 오류', '연결 풀을 제한하고 명시적 트랜잭션에서 데이터 접근')
    if path == 'backend/app/mcp/server.py' or path == 'mcp_server.py':
        return ('식품 도메인 MCP stdio 제공', 'Tool 인자·Resource URI·Prompt 이름·선택 host 모드', '제한된 조회/초안 Tool 결과·정책/근거·작업 안내', '기본 서버에 승인·최종 반영·임의 SQL을 노출하지 않음')
    if path == 'backend/app/parsers/documents.py':
        return ('원본 텍스트·표·PDF·이미지 파싱', '파일 경로·파일명·선택 OCR 환경', '본문·셀·페이지·좌표와 confidence를 갖는 segment 목록', '크기·페이지·셀·픽셀·구간을 제한하고 OCR는 선택 구성')
    if path == 'backend/app/parsers/xlsx_images.py':
        return ('XLSX 삽입 이미지·셀 anchor 추출', 'XLSX 경로·삽입 이미지 번호', '시트·행 범위·미디어 목록 또는 크기를 제한한 이미지 bytes', '외부 관계를 읽지 않고 ZIP·미디어 크기·픽셀·이미지 수를 제한')
    if '/parsers/ocr' in path:
        return ('격리 OCR 실행과 프로세스 수명 관리', '이미지/PDF 경로·페이지·timeout·OCR 환경', '인식 텍스트·confidence·locator 또는 OCR 오류', '가중치 재사용·직렬 요청·유휴 종료·임시 자원 정리')
    if '/runtime/' in path:
        return ('실행 예산과 중단·메모리 제어', '환경 설정·분석 실행 상태·모델 호출 기록', '제한값·실행 경계·재개 신호·메모리/토큰 지표', 'worker RSS와 별도 Ollama/OCR 메모리를 구분')
    if '/connectors/' in path:
        return ('허용된 식품 사이트 수집 어댑터', '게시판/게시글 ID·회원 연결 설정·HTTP client', '본문·첨부·게시 정보·접근 오류', '허용된 HTTPS 호스트만 사용하고 로그인 실패를 데이터로 오인하지 않음')
    if path.startswith('backend/tests/') or path.startswith('frontend/tests/'):
        return ('기능·경계·회귀 검증', '테스트 fixture·가상 입력·명시적 mock/테스트 대역', 'assert 결과와 실패 사유', 'DB 통합 테스트는 별도 _test DB·임시 assets 사용; 대역과 실제 모델 검증을 구분')
    if path == 'backend/app/seed.py':
        return ('가상 예제·초기 계정 명시적 생성', '초기 비밀번호·빈 개발 DB', '가상 식품·단가·계정·예제 작업', 'API 시작 시 자동 실행하지 않고 기존 사용자가 있으면 덮어쓰지 않음')
    if p.name == '__init__.py':
        return ('Python 패키지 진입점', '패키지 import', '패키지 namespace와 모듈 metadata', '업무 처리와 실제 I/O는 해당 하위 모듈에서 수행')
    if path.startswith(('backend/app/ai/', 'backend/app/food/', 'backend/app/domain/', 'backend/app/services/', 'backend/app/workflows/', 'backend/app/workers/')) or path == 'backend/app/db.py':
        return ('기존 모듈 경로 호환 진입점', '이전 import 경로 또는 공개 호출', 'canonical 도메인 모듈과 공개 인터페이스', '새 업무 로직을 이 호환 계층에 추가하지 않음')
    if '/views/' in path:
        return (VIEWS.get(p.stem, p.stem+' 화면'), '라우트·사용자 입력·API 조회 DTO', '사용자 여정에 맞는 화면과 명시적 API 요청', '미확인 값과 저장 전 수정·서버 권한/검증 상태를 구분')
    if '/components/' in path:
        return (COMPONENTS.get(p.stem, p.stem+' UI 컴포넌트'), 'props·표준 DTO·상위 화면 상태', '표시 결과와 emit 이벤트', '업무 반영은 권한 있는 API를 통해 수행하고 컴포넌트가 직접 DB에 접근하지 않음')
    if path == 'frontend/src/api/client.js':
        return ('프런트 공통 API client', '버전 API 경로·method·body·ETag', 'JSON 응답·ETag 또는 표준 API 오류', '세션·CSRF·업무 변경 키를 연결하며 비밀값을 문서/로그에 적지 않음')
    if path.startswith('frontend/'):
        return ('Vue 애플리케이션 '+p.stem, '애플리케이션·라우트·상태·빌드 설정', '화면·공유 상태·빌드 산출물', '설치 의존성과 생성 lock 파일은 원본 형식을 유지')
    if path.startswith('migrations/'):
        return ('DB 스키마 '+p.stem, '순서대로 실행하는 PostgreSQL migration', '테이블·인덱스·제약 또는 저장 구조 변경', '배포 환경 DB와 변경 순서를 확인하고 운영 데이터를 임의 초기화하지 않음')
    if path.startswith('scripts/') or p.suffix == '.sh':
        return ('개발·운영 보조 '+p.stem, 'CLI 인자·실행 환경·선택 입력 파일', '명령 결과·검증 기록·실행 프로세스', '실제 작업과 읽기 전용 점검의 범위를 해당 CLI에서 확인')
    if path.startswith('demo/'):
        return ('개인정보 없는 가상 시연 입력', '가상 식품 공지 또는 표 행', '파싱·모델·검수 시연용 입력', '실제 거래·급식 발주 자료로 사용하지 않음')
    if p.name.startswith('requirements') and p.suffix == '.txt':
        return ('Python 의존성 명세', '환경별 패키지와 버전 제약', '설치할 Python 환경', '잠금 파일은 생성 내용을 유지하고 환경·플랫폼 호환성을 검증')
    if path.startswith('doc/') or p.suffix == '.md':
        return ('프로젝트 문서 '+p.stem, '설계·구현·측정·검증 근거', '설명·명세·예제·검증 또는 발표 안내', '계획·테스트 대역·실제 실행 결과를 구분하고 현재 상태는 README 및 검증 근거 확인')
    return ('프로젝트 설정 '+p.name, '도구별 설정·실행 환경', '해당 도구의 구성 또는 실행 결과', '실제 비밀값과 로컬 실행 데이터는 Git에서 제외')


def style(path):
    p = Path(path)
    if path in GENERATED or path.startswith(('legacy/', 'doc/food-agent/prompts/', 'doc/food-agent/policies/')):
        return 'external'
    if p.suffix.lower() in ('.json', '.csv', '.jpg', '.jpeg', '.png', '.webp', '.pdf', '.pptx') or '.lock.' in p.name:
        return 'external'
    if p.suffix == '.txt' and 'requirements' not in p.name:
        return 'external'
    if p.suffix == '.py': return 'python'
    if p.suffix in ('.vue', '.html', '.md'): return 'html'
    if p.suffix in ('.js', '.css'): return 'block'
    if p.suffix == '.sql': return 'sql'
    return 'hash'


def prefix_end(source):
    lines = source.splitlines(keepends=True)
    count = 1 if lines and lines[0].startswith('#!') else 0
    if count < len(lines) and re.search(r'coding[:=]', lines[count]): count += 1
    return sum(len(line) for line in lines[:count])


def header(path, meta):
    purpose, incoming, outgoing, assumption = meta['spec']
    lines = ['='*78, MARKER, f'{Path(path).name} - {purpose}', '='*78, '설명:', f'    - {purpose}', '입력·출력 명세:', f'    - 입력: {incoming}', f'    - 출력: {outgoing}', '실행 가정:', f'    - {assumption}', '작성 정보:', '    - 작성자: 김재현(Finn)', '    - 이메일: penguin.klg@gmail.com', f'    - 작성일: {meta["created"]} (최초 Git 등록일 기준)', '    - 라이선스: 미지정', f'    - 버전: {VERSION}', '    - 상태: Development', '변경 이력 (Revision History):', '    DATE        AUTHOR      VERSION  DESCRIPTION', '    '+'-'*68]
    first = meta['git_history'][0] if meta['git_history'] else None
    if first: lines.append(f'    {meta["created"]}  미지정      v{VERSION}   최초 Git 등록 {first["commit"][:8]}')
    lines.append(f'    {meta["documented"]}  미지정      v{VERSION}   파일 역할·입출력·가정·이력 명세 추가')
    lines.extend(['', '    상세 Git 이력: git log --follow -- '+path, '    공통 규칙: doc/file-header-policy.md'])
    if meta.get('original_docstring'):
        lines.extend(['', '기존 모듈 설명:', *['    '+line for line in meta['original_docstring'].splitlines()]])
    lines.append('='*78)
    return '\n'.join(lines)


def has_header(source):
    return bool(re.search(r"(?m)^(?:# |-- )?FMS_FILE_SPEC$", source[:2000]))


def apply_header(path, meta):
    p = ROOT / path
    source = p.read_text()
    if has_header(source): return
    mode = meta['style']
    offset = prefix_end(source)
    if mode == 'python':
        tree = ast.parse(source)
        if tree.body and isinstance(tree.body[0], ast.Expr) and isinstance(tree.body[0].value, ast.Constant) and isinstance(tree.body[0].value.value, str):
            node = tree.body[0]
            meta['original_docstring'] = node.value.value
            lines = source.splitlines(keepends=True)
            start = sum(len(x) for x in lines[:node.lineno-1]) + len(lines[node.lineno-1].encode()[:node.col_offset].decode())
            end = sum(len(x) for x in lines[:node.end_lineno-1]) + len(lines[node.end_lineno-1].encode()[:node.end_col_offset].decode())
            source = source[:start] + source[end:]
        body = header(path, meta).replace('\\', '\\\\').replace('"""', '\\"""')
        source = source[:offset]+'"""\n'+body+'\n"""\n'+source[offset:]
        # Future imports must precede the new module constants.
        parsed = ast.parse(source);futures = [n for n in parsed.body if isinstance(n, ast.ImportFrom) and n.module == '__future__']
        index = (futures[-1] if futures else parsed.body[0]).end_lineno
        lines = source.splitlines(keepends=True)
        metadata = '\n# FMS_MODULE_METADATA_BEGIN\n__author__ = "김재현(Finn)"\n__email__ = "penguin.klg@gmail.com"\n__version__ = "0.1.0"\n__status__ = "Development"\n# FMS_MODULE_METADATA_END\n\n# ---------------------------------------------------------------------------\n# 1. Imports / Module implementation\n# ---------------------------------------------------------------------------\n'
        metadata=metadata.replace('__author__ = \"김재현(Finn)\"','__author__ = '+repr(meta.get('author',AUTHOR))).replace('__email__ = \"penguin.klg@gmail.com\"','__email__ = '+repr(meta.get('email',EMAIL)))
        lines.insert(index, metadata);p.write_text(''.join(lines).rstrip()+'\n');return
    text = header(path, meta)
    if mode == 'html': block = '<!--\n'+text.replace('-->', '-- >')+'\n-->\n'
    elif mode == 'block': block = '/*\n'+text.replace('*/', '* /')+'\n*/\n'
    else: block = '\n'.join((('-- ' if mode == 'sql' else '# ')+line).rstrip() for line in text.splitlines())+'\n'
    p.write_text(source[:offset]+block+source[offset:])


def build(apply=False):
    all_paths = paths();logs = history();today = datetime.now(ZoneInfo('Asia/Seoul')).date().isoformat()
    old = json.loads((ROOT/MANIFEST).read_text())['files'] if (ROOT/MANIFEST).exists() else {}
    entries = {}
    for path in all_paths:
        revisions = logs.get(path, [])
        created = datetime.fromisoformat(revisions[0]['date']).astimezone(ZoneInfo('Asia/Seoul')).date().isoformat() if revisions else today
        previous = old.get(path, {})
        meta = {'spec': list(spec(path)), 'style': style(path), 'author': AUTHOR if style(path)!='external' else UNKNOWN, 'email': EMAIL if style(path)!='external' else UNKNOWN, 'license': UNKNOWN, 'version': VERSION, 'status':'Development', 'created': created, 'documented': previous.get('documented', today), 'git_history': revisions}
        source=(ROOT/path).read_text(errors='replace')[:4000] if path not in GENERATED else ''
        for label,key in [('작성자','author'),('이메일','email')]:
            match=re.search(label+r': ([^\n]+)',source)
            if match:meta[key]=match[1].strip()
        if previous.get('original_docstring'):meta['original_docstring'] = previous['original_docstring']
        if apply and meta['style'] != 'external': apply_header(path, meta)
        meta['sha256'] = hashlib.sha256((ROOT/path).read_bytes()).hexdigest() if path not in GENERATED else None
        entries[path] = meta
    document = {'schema_version':'file-spec-v1','identity_policy':'사용자 승인 정보: 김재현(Finn), penguin.klg@gmail.com. 수정 코드·문서에 적용; 원저자 미확인 파일과 라이선스는 미지정 유지','history_policy':'Git 이력은 생성 시점 snapshot; 최신 이력은 git log --follow로 조회','files':entries}
    (ROOT/MANIFEST).write_text(json.dumps(document, ensure_ascii=False, indent=2)+'\n')
    lines=['# 파일별 명세와 이력 목록', '', '사용자 승인에 따라 수정 코드·문서의 작성자·이메일은 김재현(Finn)·penguin.klg@gmail.com입니다. 원저자 미확인 파일과 라이선스는 미지정입니다. 파일 내 헤더는 초기 명세이며 실제 변경 이력의 기준은 Git입니다.', '', 'JSON·CSV·잠금 파일·가상 입력·이미지·MCP Prompt/정책·legacy 원본은 내용 보존을 위해 외부 명세로 관리합니다. 상세 입력·출력·가정과 Git 기록은 [file-manifest.json](file-manifest.json)의 해당 경로에 있습니다.', '', '| 파일 | 역할 | 명세 위치 |', '|---|---|---|']
    for path, meta in entries.items():
        where='외부 명세 (원본 보존)' if meta['style']=='external' else '파일 상단 헤더 + 외부 목록'
        lines.append(f'| [{path}](../{path}) | {meta["spec"][0]} | {where} |')
    lines.extend(['', '갱신: `python3 scripts/file-specs.py --apply` (누락 헤더 추가), `--refresh` (현재 파일/이력 snapshot 갱신), `--check` (형식·coverage·해시 검사).', '', '변경 이력 작성 규칙과 원본 보존 범위는 [file-header-policy.md](file-header-policy.md)를 참고하세요.'])
    (ROOT/INDEX).write_text('\n'.join(lines)+'\n')
    return len(entries)


def check():
    document=json.loads((ROOT/MANIFEST).read_text());entries=document['files'];errors=[]
    if set(entries)!=set(paths()):errors.append('파일 목록 불일치: --refresh 또는 --apply 필요')
    for path,meta in entries.items():
        p=ROOT/path
        if not p.is_file():errors.append(path+': 파일 없음');continue
        if (meta.get('author'),meta.get('email')) not in [(UNKNOWN,UNKNOWN),('김재현(Finn)','penguin.klg@gmail.com')] or meta.get('license')!=UNKNOWN:errors.append(path+': 승인된 작성 정보 정책 불일치')
        if path not in GENERATED and hashlib.sha256(p.read_bytes()).hexdigest()!=meta['sha256']:errors.append(path+': 명세 hash 갱신 필요')
        if meta['style']!='external':
            source=p.read_text()
            if not has_header(source) or any(label not in source[:4000] for label in ('설명:','입력·출력 명세:','실행 가정:','작성 정보:','변경 이력 (Revision History):')):errors.append(path+': 필수 헤더 누락')
            if meta['style']=='python':
                tree=ast.parse(source)
                values={n.targets[0].id:n.value.value for n in tree.body if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and isinstance(n.value,ast.Constant)}
                if values.get('__author__')!=meta['author'] or values.get('__email__')!=meta['email'] or values.get('__version__')!=VERSION or values.get('__status__')!='Development':errors.append(path+': Python metadata 누락')
    if errors:raise SystemExit('\n'.join(errors))
    print(f'{len(entries)} files: headers, external specifications and hashes valid')


def main():
    parser=argparse.ArgumentParser(description=__doc__);group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--apply',action='store_true');group.add_argument('--refresh',action='store_true');group.add_argument('--check',action='store_true');args=parser.parse_args()
    if args.check:check()
    else:print(f'{build(apply=args.apply)} file specifications updated')


if __name__=='__main__':main()
