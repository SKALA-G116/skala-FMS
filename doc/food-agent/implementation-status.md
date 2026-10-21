<!--
==============================================================================
FMS_FILE_SPEC
implementation-status.md - 프로젝트 문서 implementation-status
==============================================================================
설명:
    - 프로젝트 문서 implementation-status
입력·출력 명세:
    - 입력: 설계·구현·측정·검증 근거
    - 출력: 설명·명세·예제·검증 또는 발표 안내
실행 가정:
    - 계획·테스트 대역·실제 실행 결과를 구분하고 현재 상태는 README 및 검증 근거 확인
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

    2026-10-21  김재현(Finn) v0.1.0   Agent 도구 선택 기반 리빌드·업무 경계 및 검증

    상세 Git 이력: git log --follow -- doc/food-agent/implementation-status.md
    공통 규칙: doc/file-header-policy.md
==============================================================================
-->
# 실제 구현 상태 — 2026-10-20

AI 자동 처리의 최신 구현은 [AI 처리 보완](agent-update.md)을 참고하세요. 아래 초기 규칙 분석·모델 미검증 설명은 해당 문서로 대체합니다.

최신 실행 흐름은 [운영 흐름 보완](operational-update.md)을 우선 참고하세요. 이 파일의 초기 제한 설명 중 계정·증분 수집·OCR·표 검토 UI는 후속 구현으로 갱신되었습니다.

이 파일은 v0.2 설계 문서와 **지금 실행되는 개발 버전**의 차이를 설명합니다. 설계 문서의 계획이 자동으로 구현 완료를 뜻하지 않습니다.

## 동작하는 기능

- Vue 3 + Vite: 로그인, 대시보드, 문서 등록·목록·원본 다운로드, 분석 실행, 변경안 목록·근거 비교·수정·승인/보류/반려/철회, 수동 초안 작성, 상품/단가/식품별 이력, 작업 상태와 재시도·취소.
- FastAPI: 설계의 38 경로·42 operation을 처리하는 디스패처. 추가로 문서 revision별 근거 목록과 인증·서명된 원본 파일 다운로드 경로 제공. 요청 operation은 JSON Schema로 검사.
- PostgreSQL: 상품/규격/공급 품목과 사실의 관계형 테이블·외래키·numeric 금액·기간; 문서/근거/변경안/검토/audit는 종류별 JSONB 레코드. JSONB는 조회 인덱스를 가지지만 대규모 운영용 상세 정규화는 후속 작업.
- 승인과 반영 분리. 변경 묶음의 모든 업무 사실, audit, application, proposal, job 완료는 같은 트랜잭션으로 기록.
- 멱등 키의 요청 hash 비교, actor+method+path 범위, ETag, 승인 내용 revision 고정, application 고유 제약.
- 기존 대상 version/원문 최신 revision/기간 충돌 재검사. 정정 체인을 사용한 부분 기간 교체와 원본 보존.
- 별도 durable job worker: PostgreSQL SKIP LOCKED claim, lease/fence, 실패 상태, 재시도 job, 취소 경계. apply 작업은 취소 불가.
- LangGraph + 실제 PostgreSQL checkpointer. 상태는 ID 참조로 유지. 파싱 결과와 제안 ID는 업무 DB에 보관해 재실행 중복을 피함.
- TXT/CSV/HTML, Excel(XLS/XLSX), 텍스트 PDF 파싱. Excel 셀 위치, 이미지 OCR 좌표, 텍스트 블록 근거. 파일 20MiB, PDF 20페이지, 이미지 16MP, 셀 20만개 등 제한.
- school062 공개 본문 수동 수집 커넥터. 허용 호스트·리다이렉트 검사, 내용 해시와 원문 revision. 이미지/첨부가 있으면 불완전 입력으로 표시하고 승인 차단. 사이트 로그인을 우회하지 않음.
- MCP stdio: 모델용 read Tool 3개, 별도 신뢰 호스트 실행은 Tool 6개. Resource 5종, Prompt 3종. 모델에 DB 직접 수정·승인·삭제 Tool 미제공.
- Argon2 비밀번호, 해시 저장 세션, 8시간 만료, CSRF, 동일 출처 검사, 역할 검사, 사용자별 로그인 시도 제한, 다운로드 인증+5분 서명.

## 현재의 제한과 운영 전 작업

| 항목 | 현재 동작 / 필요한 작업 |
|---|---|
| 분석 품질 | 기본은 명시된 형식만 읽는 규칙 분석. 자유 형식은 수동 초안 또는 설정한 모델 adapter. 실제 모델·한국어 식품 OCR 평가 미실시 |
| OCR | PaddleOCR 3 adapter는 구현. 런타임·가중치 미설치, 실제 추론 미검증. subprocess마다 로딩. 지원 Python 환경, 모델 재사용 worker, cgroup/RSS 상한, 벤치마크 필요 |
| PDF | 텍스트 PDF만 지원. 스캔 PDF는 명시적 실패. 고정 렌더와 좌표 변환은 후속 구현 |
| 수집 범위 | 본문만 수집. 원격 이미지/첨부 내려받기·로그인 세션·자동 스케줄러 미구현. 수동 수집은 게시판당 최대 10개로 제한, 과거 전체 재방문 없음 |
| MCP host | stdio adapter는 실제 통신 테스트. 기본 그래프는 공통 서비스 직접 호출. 장기 MCP 자식 프로세스 수명 관리와 도구 스키마 hash 검증 미연결 |
| 모델 예산 | 단일 호출, 보수적 UTF-8 byte 입력 상한, 출력 4,000 tokens, 120초 timeout. 실제 tokenizer/window 등록·세그먼트별 도구 순환·모델 fallback 없음 |
| 성능 | 개발 데이터셋 2,000건 상한을 초과하면 명시적 실패. 현재 정렬/필터 일부는 상한 내 메모리에서 수행. SQL 검색·페이지 쿼리, 제품별 세부 pagination 확장 필요 |
| 작업 경쟁 | apply는 DB에서 fencing 확인 후 잠금. 분석 단계는 취소 경계 검사. lease heartbeat와 오래 멈춘 분석자의 각 쓰기별 fencing, 더 정교한 재개 테스트 필요 |
| 저장/보존 | 파일은 내용 hash로 DB 밖 저장. 백업/보존/체크포인트 14일 정리/참조 보호 GC는 아직 없음. 임의 자동 삭제를 하지 않음 |
| API 계약 | 주요 입력과 Proposal 응답을 검사. 일부 응답 DTO(AnalysisRun/Audit/Decision/Application 등)는 개발 버전 형태. v0.2 OpenAPI 81종 응답 전체 호환성 검증은 미완료 |
| UI | 일상 검토는 폼 제공. 고급 대체품 구성·제품 생애 상태 operation은 JSON 편집/API 사용. 이미지 영역 강조 뷰어는 좌표 표시+원본 다운로드 수준 |
| 배포 | 로컬 Python 3.14/PostgreSQL 17과 Vue build 검증. Docker 설정은 제공했지만 build 미검증. TLS, 강한 계정 정책, 비밀 관리, 사용자 관리 화면, 운영 관측/백업 필요 |

현재 `memory-checklist.md`의 운영 측정 항목을 통과했다고 주장하지 않습니다. 실제 OCR 정확도·최대 RSS·지연·처리량은 대상 자료와 서버에서 측정해야 합니다.

## 코드의 위치

- `backend/app/api/main.py`: 인증·권한·HTTP 명령·멱등 처리
- `backend/app/domains/review/proposals.py`: 검증·상태 전이·내용 revision
- `backend/app/domains/review/application.py`: 기간 조회·원자적 반영·정정·audit
- `backend/app/domains/ingestion/documents.py`: 원문/파일/내용 hash/revision
- `backend/app/domains/analysis/workflow.py`: durable 분석 그래프
- `backend/app/domains/jobs/worker.py`: 큐 실행·실패 기록
- `backend/app/parsers/`: 제한을 둔 파일 파싱과 OCR 어댑터
- `backend/app/mcp/server.py`: MCP 경계
- `frontend/src/views/`: 페이지별 업무 흐름
- `frontend/src/components/`: 상태, 근거, 페이지 이동 공통 UI

검증 명령과 계정은 저장소 루트의 `README.food.md`를 참조하세요.
