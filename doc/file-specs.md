# 파일별 명세와 이력 목록

사용자 승인에 따라 수정 코드·문서의 작성자·이메일은 김재현(Finn)·penguin.klg@gmail.com입니다. 원저자 미확인 파일과 라이선스는 미지정입니다. 파일 내 헤더는 초기 명세이며 실제 변경 이력의 기준은 Git입니다.

JSON·CSV·잠금 파일·가상 입력·이미지·MCP Prompt/정책·legacy 원본은 내용 보존을 위해 외부 명세로 관리합니다. 상세 입력·출력·가정과 Git 기록은 [file-manifest.json](file-manifest.json)의 해당 경로에 있습니다.

| 파일 | 역할 | 명세 위치 |
|---|---|---|
| [.dockerignore](../.dockerignore) | 프로젝트 설정 .dockerignore | 파일 상단 헤더 + 외부 목록 |
| [.env.example](../.env.example) | 프로젝트 설정 .env.example | 파일 상단 헤더 + 외부 목록 |
| [.env.food.example](../.env.food.example) | 프로젝트 설정 .env.food.example | 파일 상단 헤더 + 외부 목록 |
| [.github/workflows/ci.yml](../.github/workflows/ci.yml) | 프로젝트 설정 ci.yml | 파일 상단 헤더 + 외부 목록 |
| [.gitignore](../.gitignore) | 프로젝트 설정 .gitignore | 파일 상단 헤더 + 외부 목록 |
| [Dockerfile.food](../Dockerfile.food) | 프로젝트 설정 Dockerfile.food | 파일 상단 헤더 + 외부 목록 |
| [README.food.md](../README.food.md) | 프로젝트 문서 README.food | 파일 상단 헤더 + 외부 목록 |
| [README.md](../README.md) | 프로젝트 문서 README | 파일 상단 헤더 + 외부 목록 |
| [backend/__init__.py](../backend/__init__.py) | Python 패키지 진입점 | 파일 상단 헤더 + 외부 목록 |
| [backend/app/__init__.py](../backend/app/__init__.py) | Python 패키지 진입점 | 파일 상단 헤더 + 외부 목록 |
| [backend/app/api/__init__.py](../backend/app/api/__init__.py) | Python 패키지 진입점 | 파일 상단 헤더 + 외부 목록 |
| [backend/app/api/assets.py](../backend/app/api/assets.py) | 프로젝트 설정 assets.py | 파일 상단 헤더 + 외부 목록 |
| [backend/app/api/http.py](../backend/app/api/http.py) | HTTP 공통 DTO와 응답 보조 함수 | 파일 상단 헤더 + 외부 목록 |
| [backend/app/api/main.py](../backend/app/api/main.py) | FastAPI 애플리케이션 조립 | 파일 상단 헤더 + 외부 목록 |
| [backend/app/api/registry.py](../backend/app/api/registry.py) | 프로젝트 설정 registry.py | 파일 상단 헤더 + 외부 목록 |
| [backend/app/api/routing.py](../backend/app/api/routing.py) | 명시적 FastAPI 도메인 라우터 생성 | 파일 상단 헤더 + 외부 목록 |
| [backend/app/api/transport.py](../backend/app/api/transport.py) | 공통 HTTP 보안·트랜잭션 경계 | 파일 상단 헤더 + 외부 목록 |
| [backend/app/connectors/school062.py](../backend/app/connectors/school062.py) | 허용된 식품 사이트 수집 어댑터 | 파일 상단 헤더 + 외부 목록 |
| [backend/app/domains/__init__.py](../backend/app/domains/__init__.py) | Python 패키지 진입점 | 파일 상단 헤더 + 외부 목록 |
| [backend/app/domains/analysis/__init__.py](../backend/app/domains/analysis/__init__.py) | Python 패키지 진입점 | 파일 상단 헤더 + 외부 목록 |
| [backend/app/domains/analysis/agent.py](../backend/app/domains/analysis/agent.py) | LLM 계획·추출과 근거 연결 | 파일 상단 헤더 + 외부 목록 |
| [backend/app/domains/analysis/api.py](../backend/app/domains/analysis/api.py) | analysis 도메인 HTTP 유스케이스 | 파일 상단 헤더 + 외부 목록 |
| [backend/app/domains/analysis/consolidation.py](../backend/app/domains/analysis/consolidation.py) | 원본 표 정규화·추출 후보 중복 통합 | 파일 상단 헤더 + 외부 목록 |
| [backend/app/domains/analysis/export.py](../backend/app/domains/analysis/export.py) | 근거를 포함한 검토 Excel 생성 | 파일 상단 헤더 + 외부 목록 |
| [backend/app/domains/analysis/matching.py](../backend/app/domains/analysis/matching.py) | 프로젝트 설정 matching.py | 파일 상단 헤더 + 외부 목록 |
| [backend/app/domains/analysis/planning.py](../backend/app/domains/analysis/planning.py) | 프로젝트 설정 planning.py | 파일 상단 헤더 + 외부 목록 |
| [backend/app/domains/analysis/provider.py](../backend/app/domains/analysis/provider.py) | Ollama 비동기 구조화 추론 | 파일 상단 헤더 + 외부 목록 |
| [backend/app/domains/analysis/reconciliation.py](../backend/app/domains/analysis/reconciliation.py) | 완료 분석의 이력 보존형 재정리 | 파일 상단 헤더 + 외부 목록 |
| [backend/app/domains/analysis/schemas.py](../backend/app/domains/analysis/schemas.py) | LLM 계획·추출 응답 스키마 | 파일 상단 헤더 + 외부 목록 |
| [backend/app/domains/analysis/service.py](../backend/app/domains/analysis/service.py) | 영속 분석 작업 등록 | 파일 상단 헤더 + 외부 목록 |
| [backend/app/domains/analysis/workflow.py](../backend/app/domains/analysis/workflow.py) | LangGraph 분석 흐름 | 파일 상단 헤더 + 외부 목록 |
| [backend/app/domains/catalog/__init__.py](../backend/app/domains/catalog/__init__.py) | Python 패키지 진입점 | 파일 상단 헤더 + 외부 목록 |
| [backend/app/domains/catalog/api.py](../backend/app/domains/catalog/api.py) | catalog 도메인 HTTP 유스케이스 | 파일 상단 헤더 + 외부 목록 |
| [backend/app/domains/catalog/editing.py](../backend/app/domains/catalog/editing.py) | 프로젝트 설정 editing.py | 파일 상단 헤더 + 외부 목록 |
| [backend/app/domains/catalog/queries.py](../backend/app/domains/catalog/queries.py) | 식품·규격·단가의 시점별 조회 | 파일 상단 헤더 + 외부 목록 |
| [backend/app/domains/catalog/record.py](../backend/app/domains/catalog/record.py) | 표준 FoodRecord DTO와 정규화 | 파일 상단 헤더 + 외부 목록 |
| [backend/app/domains/identity/__init__.py](../backend/app/domains/identity/__init__.py) | Python 패키지 진입점 | 파일 상단 헤더 + 외부 목록 |
| [backend/app/domains/identity/api.py](../backend/app/domains/identity/api.py) | identity 도메인 HTTP 유스케이스 | 파일 상단 헤더 + 외부 목록 |
| [backend/app/domains/identity/service.py](../backend/app/domains/identity/service.py) | 세션 인증·로그인과 역할 검사 | 파일 상단 헤더 + 외부 목록 |
| [backend/app/domains/ingestion/__init__.py](../backend/app/domains/ingestion/__init__.py) | Python 패키지 진입점 | 파일 상단 헤더 + 외부 목록 |
| [backend/app/domains/ingestion/api.py](../backend/app/domains/ingestion/api.py) | ingestion 도메인 HTTP 유스케이스 | 파일 상단 헤더 + 외부 목록 |
| [backend/app/domains/ingestion/archives.py](../backend/app/domains/ingestion/archives.py) | 자료·식품의 삭제 보관과 복구 | 파일 상단 헤더 + 외부 목록 |
| [backend/app/domains/ingestion/collection.py](../backend/app/domains/ingestion/collection.py) | 게시글·첨부 수집과 변경 감지 | 파일 상단 헤더 + 외부 목록 |
| [backend/app/domains/ingestion/connections.py](../backend/app/domains/ingestion/connections.py) | 사이트 연결 정보의 암호화 보관 | 파일 상단 헤더 + 외부 목록 |
| [backend/app/domains/ingestion/documents.py](../backend/app/domains/ingestion/documents.py) | 원본 파일·문서 revision 등록 | 파일 상단 헤더 + 외부 목록 |
| [backend/app/domains/ingestion/purge.py](../backend/app/domains/ingestion/purge.py) | 자료 선택·일괄 작업과 조건부 영구 삭제 | 파일 상단 헤더 + 외부 목록 |
| [backend/app/domains/jobs/__init__.py](../backend/app/domains/jobs/__init__.py) | Python 패키지 진입점 | 파일 상단 헤더 + 외부 목록 |
| [backend/app/domains/jobs/api.py](../backend/app/domains/jobs/api.py) | jobs 도메인 HTTP 유스케이스 | 파일 상단 헤더 + 외부 목록 |
| [backend/app/domains/jobs/service.py](../backend/app/domains/jobs/service.py) | 영속 작업의 등록·조회·상태 저장 | 파일 상단 헤더 + 외부 목록 |
| [backend/app/domains/jobs/worker.py](../backend/app/domains/jobs/worker.py) | 수집·분석·반영 작업 소비 | 파일 상단 헤더 + 외부 목록 |
| [backend/app/domains/pricing/__init__.py](../backend/app/domains/pricing/__init__.py) | Python 패키지 진입점 | 파일 상단 헤더 + 외부 목록 |
| [backend/app/domains/pricing/api.py](../backend/app/domains/pricing/api.py) | pricing 도메인 HTTP 유스케이스 | 파일 상단 헤더 + 외부 목록 |
| [backend/app/domains/pricing/proposals.py](../backend/app/domains/pricing/proposals.py) | 표 행의 가격 변경안 준비 | 파일 상단 헤더 + 외부 목록 |
| [backend/app/domains/pricing/workbooks.py](../backend/app/domains/pricing/workbooks.py) | 원본 단가표·시트·열 조회 | 파일 상단 헤더 + 외부 목록 |
| [backend/app/domains/reporting/__init__.py](../backend/app/domains/reporting/__init__.py) | Python 패키지 진입점 | 파일 상단 헤더 + 외부 목록 |
| [backend/app/domains/reporting/api.py](../backend/app/domains/reporting/api.py) | reporting 도메인 HTTP 유스케이스 | 파일 상단 헤더 + 외부 목록 |
| [backend/app/domains/review/__init__.py](../backend/app/domains/review/__init__.py) | Python 패키지 진입점 | 파일 상단 헤더 + 외부 목록 |
| [backend/app/domains/review/api.py](../backend/app/domains/review/api.py) | review 도메인 HTTP 유스케이스 | 파일 상단 헤더 + 외부 목록 |
| [backend/app/domains/review/application.py](../backend/app/domains/review/application.py) | 승인된 변경의 원자적 DB 반영 | 파일 상단 헤더 + 외부 목록 |
| [backend/app/domains/review/approval.py](../backend/app/domains/review/approval.py) | 프로젝트 설정 approval.py | 파일 상단 헤더 + 외부 목록 |
| [backend/app/domains/review/inbox.py](../backend/app/domains/review/inbox.py) | 자료별 최신 분석 검수함 조회 | 파일 상단 헤더 + 외부 목록 |
| [backend/app/domains/review/items.py](../backend/app/domains/review/items.py) | 추출 품목의 사용자 검토와 반영 준비 | 파일 상단 헤더 + 외부 목록 |
| [backend/app/domains/review/proposals.py](../backend/app/domains/review/proposals.py) | 변경안 검증과 승인 상태 전이 | 파일 상단 헤더 + 외부 목록 |
| [backend/app/domains/review/staging.py](../backend/app/domains/review/staging.py) | 프로젝트 설정 staging.py | 파일 상단 헤더 + 외부 목록 |
| [backend/app/infrastructure/__init__.py](../backend/app/infrastructure/__init__.py) | Python 패키지 진입점 | 파일 상단 헤더 + 외부 목록 |
| [backend/app/infrastructure/contracts.py](../backend/app/infrastructure/contracts.py) | 프로젝트 설정 contracts.py | 파일 상단 헤더 + 외부 목록 |
| [backend/app/infrastructure/database.py](../backend/app/infrastructure/database.py) | PostgreSQL 연결·저장 공통 함수 | 파일 상단 헤더 + 외부 목록 |
| [backend/app/mcp/server.py](../backend/app/mcp/server.py) | 식품 도메인 MCP stdio 제공 | 파일 상단 헤더 + 외부 목록 |
| [backend/app/parsers/documents.py](../backend/app/parsers/documents.py) | 원본 텍스트·표·PDF·이미지 파싱 | 파일 상단 헤더 + 외부 목록 |
| [backend/app/parsers/ocr.py](../backend/app/parsers/ocr.py) | 격리 OCR 실행과 프로세스 수명 관리 | 파일 상단 헤더 + 외부 목록 |
| [backend/app/parsers/ocr_pool.py](../backend/app/parsers/ocr_pool.py) | 격리 OCR 실행과 프로세스 수명 관리 | 파일 상단 헤더 + 외부 목록 |
| [backend/app/parsers/xlsx_images.py](../backend/app/parsers/xlsx_images.py) | XLSX 삽입 이미지·셀 anchor 추출 | 파일 상단 헤더 + 외부 목록 |
| [backend/app/parsers/xlsx_merges.py](../backend/app/parsers/xlsx_merges.py) | 프로젝트 설정 xlsx_merges.py | 파일 상단 헤더 + 외부 목록 |
| [backend/app/runtime/__init__.py](../backend/app/runtime/__init__.py) | 실행 예산과 중단·메모리 제어 | 파일 상단 헤더 + 외부 목록 |
| [backend/app/runtime/execution.py](../backend/app/runtime/execution.py) | 실행 예산과 중단·메모리 제어 | 파일 상단 헤더 + 외부 목록 |
| [backend/app/runtime/limits.py](../backend/app/runtime/limits.py) | 실행 예산과 중단·메모리 제어 | 파일 상단 헤더 + 외부 목록 |
| [backend/app/seed.py](../backend/app/seed.py) | 가상 예제·초기 계정 명시적 생성 | 파일 상단 헤더 + 외부 목록 |
| [backend/requirements-ocr.lock.txt](../backend/requirements-ocr.lock.txt) | Python 의존성 명세 | 외부 명세 (원본 보존) |
| [backend/requirements.lock.txt](../backend/requirements.lock.txt) | Python 의존성 명세 | 외부 명세 (원본 보존) |
| [backend/requirements.txt](../backend/requirements.txt) | Python 의존성 명세 | 파일 상단 헤더 + 외부 목록 |
| [backend/tests/conftest.py](../backend/tests/conftest.py) | 기능·경계·회귀 검증 | 파일 상단 헤더 + 외부 목록 |
| [backend/tests/test_agent.py](../backend/tests/test_agent.py) | 기능·경계·회귀 검증 | 파일 상단 헤더 + 외부 목록 |
| [backend/tests/test_agent_routing.py](../backend/tests/test_agent_routing.py) | 기능·경계·회귀 검증 | 파일 상단 헤더 + 외부 목록 |
| [backend/tests/test_async_runtime.py](../backend/tests/test_async_runtime.py) | 기능·경계·회귀 검증 | 파일 상단 헤더 + 외부 목록 |
| [backend/tests/test_consolidation.py](../backend/tests/test_consolidation.py) | 기능·경계·회귀 검증 | 파일 상단 헤더 + 외부 목록 |
| [backend/tests/test_domain_architecture.py](../backend/tests/test_domain_architecture.py) | 기능·경계·회귀 검증 | 파일 상단 헤더 + 외부 목록 |
| [backend/tests/test_file_specs.py](../backend/tests/test_file_specs.py) | 기능·경계·회귀 검증 | 파일 상단 헤더 + 외부 목록 |
| [backend/tests/test_food_record.py](../backend/tests/test_food_record.py) | 기능·경계·회귀 검증 | 파일 상단 헤더 + 외부 목록 |
| [backend/tests/test_parsers_mcp.py](../backend/tests/test_parsers_mcp.py) | 기능·경계·회귀 검증 | 파일 상단 헤더 + 외부 목록 |
| [backend/tests/test_workflow.py](../backend/tests/test_workflow.py) | 기능·경계·회귀 검증 | 파일 상단 헤더 + 외부 목록 |
| [compose.food.yml](../compose.food.yml) | 프로젝트 설정 compose.food.yml | 파일 상단 헤더 + 외부 목록 |
| [demo/notice.txt](../demo/notice.txt) | 개인정보 없는 가상 시연 입력 | 외부 명세 (원본 보존) |
| [demo/prices.csv](../demo/prices.csv) | 개인정보 없는 가상 시연 입력 | 외부 명세 (원본 보존) |
| [doc/README.md](../doc/README.md) | 프로젝트 문서 README | 파일 상단 헤더 + 외부 목록 |
| [doc/file-header-policy.md](../doc/file-header-policy.md) | 프로젝트 문서 file-header-policy | 파일 상단 헤더 + 외부 목록 |
| [doc/file-manifest.json](../doc/file-manifest.json) | 프로젝트 문서 file-manifest | 외부 명세 (원본 보존) |
| [doc/file-specs.md](../doc/file-specs.md) | 프로젝트 문서 file-specs | 외부 명세 (원본 보존) |
| [doc/food-agent/README.md](../doc/food-agent/README.md) | 프로젝트 문서 README | 파일 상단 헤더 + 외부 목록 |
| [doc/food-agent/acceptance.md](../doc/food-agent/acceptance.md) | 프로젝트 문서 acceptance | 파일 상단 헤더 + 외부 목록 |
| [doc/food-agent/agent-rebuild.md](../doc/food-agent/agent-rebuild.md) | 프로젝트 문서 agent-rebuild | 파일 상단 헤더 + 외부 목록 |
| [doc/food-agent/agent-update.md](../doc/food-agent/agent-update.md) | 프로젝트 문서 agent-update | 파일 상단 헤더 + 외부 목록 |
| [doc/food-agent/api-guide.md](../doc/food-agent/api-guide.md) | 프로젝트 문서 api-guide | 파일 상단 헤더 + 외부 목록 |
| [doc/food-agent/architecture-audit-v3.md](../doc/food-agent/architecture-audit-v3.md) | 프로젝트 문서 architecture-audit-v3 | 파일 상단 헤더 + 외부 목록 |
| [doc/food-agent/architecture.md](../doc/food-agent/architecture.md) | 프로젝트 문서 architecture | 파일 상단 헤더 + 외부 목록 |
| [doc/food-agent/auth-session.md](../doc/food-agent/auth-session.md) | 프로젝트 문서 auth-session | 파일 상단 헤더 + 외부 목록 |
| [doc/food-agent/capability-design.md](../doc/food-agent/capability-design.md) | 프로젝트 문서 capability-design | 파일 상단 헤더 + 외부 목록 |
| [doc/food-agent/design-review-report.json](../doc/food-agent/design-review-report.json) | 프로젝트 문서 design-review-report | 외부 명세 (원본 보존) |
| [doc/food-agent/embedded-table-images.md](../doc/food-agent/embedded-table-images.md) | 프로젝트 문서 embedded-table-images | 파일 상단 헤더 + 외부 목록 |
| [doc/food-agent/examples/analysis-profiles.json](../doc/food-agent/examples/analysis-profiles.json) | 프로젝트 문서 analysis-profiles | 외부 명세 (원본 보존) |
| [doc/food-agent/examples/analysis-run.json](../doc/food-agent/examples/analysis-run.json) | 프로젝트 문서 analysis-run | 외부 명세 (원본 보존) |
| [doc/food-agent/examples/application-accepted.json](../doc/food-agent/examples/application-accepted.json) | 프로젝트 문서 application-accepted | 외부 명세 (원본 보존) |
| [doc/food-agent/examples/error-stale.json](../doc/food-agent/examples/error-stale.json) | 프로젝트 문서 error-stale | 외부 명세 (원본 보존) |
| [doc/food-agent/examples/evidence.json](../doc/food-agent/examples/evidence.json) | 프로젝트 문서 evidence | 외부 명세 (원본 보존) |
| [doc/food-agent/examples/job-analyzed.json](../doc/food-agent/examples/job-analyzed.json) | 프로젝트 문서 job-analyzed | 외부 명세 (원본 보존) |
| [doc/food-agent/examples/manifest.json](../doc/food-agent/examples/manifest.json) | 프로젝트 문서 manifest | 외부 명세 (원본 보존) |
| [doc/food-agent/examples/price-list.json](../doc/food-agent/examples/price-list.json) | 프로젝트 문서 price-list | 외부 명세 (원본 보존) |
| [doc/food-agent/examples/product-history.json](../doc/food-agent/examples/product-history.json) | 프로젝트 문서 product-history | 외부 명세 (원본 보존) |
| [doc/food-agent/examples/proposal-approved.json](../doc/food-agent/examples/proposal-approved.json) | 프로젝트 문서 proposal-approved | 외부 명세 (원본 보존) |
| [doc/food-agent/examples/proposal-new-product-bundle.json](../doc/food-agent/examples/proposal-new-product-bundle.json) | 프로젝트 문서 proposal-new-product-bundle | 외부 명세 (원본 보존) |
| [doc/food-agent/examples/proposal-ready.json](../doc/food-agent/examples/proposal-ready.json) | 프로젝트 문서 proposal-ready | 외부 명세 (원본 보존) |
| [doc/food-agent/examples/source.json](../doc/food-agent/examples/source.json) | 프로젝트 문서 source | 외부 명세 (원본 보존) |
| [doc/food-agent/extraction-consolidation.md](../doc/food-agent/extraction-consolidation.md) | 프로젝트 문서 extraction-consolidation | 파일 상단 헤더 + 외부 목록 |
| [doc/food-agent/extraction-normalization.md](../doc/food-agent/extraction-normalization.md) | 프로젝트 문서 extraction-normalization | 파일 상단 헤더 + 외부 목록 |
| [doc/food-agent/frontend-spec.md](../doc/food-agent/frontend-spec.md) | 프로젝트 문서 frontend-spec | 파일 상단 헤더 + 외부 목록 |
| [doc/food-agent/implementation-status.md](../doc/food-agent/implementation-status.md) | 프로젝트 문서 implementation-status | 파일 상단 헤더 + 외부 목록 |
| [doc/food-agent/implementation-verification.json](../doc/food-agent/implementation-verification.json) | 프로젝트 문서 implementation-verification | 외부 명세 (원본 보존) |
| [doc/food-agent/initial-refactor.md](../doc/food-agent/initial-refactor.md) | 프로젝트 문서 initial-refactor | 파일 상단 헤더 + 외부 목록 |
| [doc/food-agent/mcp-capabilities.json](../doc/food-agent/mcp-capabilities.json) | 프로젝트 문서 mcp-capabilities | 외부 명세 (원본 보존) |
| [doc/food-agent/memory-checklist.md](../doc/food-agent/memory-checklist.md) | 프로젝트 문서 memory-checklist | 파일 상단 헤더 + 외부 목록 |
| [doc/food-agent/model-errors.md](../doc/food-agent/model-errors.md) | 프로젝트 문서 model-errors | 파일 상단 헤더 + 외부 목록 |
| [doc/food-agent/ocr-reuse-benchmark.json](../doc/food-agent/ocr-reuse-benchmark.json) | 프로젝트 문서 ocr-reuse-benchmark | 외부 명세 (원본 보존) |
| [doc/food-agent/ocr-stability.md](../doc/food-agent/ocr-stability.md) | 프로젝트 문서 ocr-stability | 파일 상단 헤더 + 외부 목록 |
| [doc/food-agent/openapi.json](../doc/food-agent/openapi.json) | 프로젝트 문서 openapi | 외부 명세 (원본 보존) |
| [doc/food-agent/operational-update.md](../doc/food-agent/operational-update.md) | 프로젝트 문서 operational-update | 파일 상단 헤더 + 외부 목록 |
| [doc/food-agent/pdf-review-provenance.json](../doc/food-agent/pdf-review-provenance.json) | 프로젝트 문서 pdf-review-provenance | 외부 명세 (원본 보존) |
| [doc/food-agent/performance-after-resume.json](../doc/food-agent/performance-after-resume.json) | 프로젝트 문서 performance-after-resume | 외부 명세 (원본 보존) |
| [doc/food-agent/performance-baseline.json](../doc/food-agent/performance-baseline.json) | 프로젝트 문서 performance-baseline | 외부 명세 (원본 보존) |
| [doc/food-agent/performance-refactor.md](../doc/food-agent/performance-refactor.md) | 프로젝트 문서 performance-refactor | 파일 상단 헤더 + 외부 목록 |
| [doc/food-agent/policies/food-policy-v1.md](../doc/food-agent/policies/food-policy-v1.md) | 프로젝트 문서 food-policy-v1 | 외부 명세 (원본 보존) |
| [doc/food-agent/price-workbook-api.md](../doc/food-agent/price-workbook-api.md) | 프로젝트 문서 price-workbook-api | 파일 상단 헤더 + 외부 목록 |
| [doc/food-agent/product-spec.md](../doc/food-agent/product-spec.md) | 프로젝트 문서 product-spec | 파일 상단 헤더 + 외부 목록 |
| [doc/food-agent/prompts/notice-v1.md](../doc/food-agent/prompts/notice-v1.md) | 프로젝트 문서 notice-v1 | 외부 명세 (원본 보존) |
| [doc/food-agent/prompts/price-table-v1.md](../doc/food-agent/prompts/price-table-v1.md) | 프로젝트 문서 price-table-v1 | 외부 명세 (원본 보존) |
| [doc/food-agent/prompts/review-evidence-v1.md](../doc/food-agent/prompts/review-evidence-v1.md) | 프로젝트 문서 review-evidence-v1 | 외부 명세 (원본 보존) |
| [doc/food-agent/review-checklist.json](../doc/food-agent/review-checklist.json) | 프로젝트 문서 review-checklist | 외부 명세 (원본 보존) |
| [doc/food-agent/review-evidence-contract.md](../doc/food-agent/review-evidence-contract.md) | 프로젝트 문서 review-evidence-contract | 파일 상단 헤더 + 외부 목록 |
| [doc/food-agent/review-inbox.md](../doc/food-agent/review-inbox.md) | 프로젝트 문서 review-inbox | 파일 상단 헤더 + 외부 목록 |
| [doc/food-agent/review-journey.md](../doc/food-agent/review-journey.md) | 프로젝트 문서 review-journey | 파일 상단 헤더 + 외부 목록 |
| [doc/food-agent/runtime-policy.json](../doc/food-agent/runtime-policy.json) | 프로젝트 문서 runtime-policy | 외부 명세 (원본 보존) |
| [doc/food-agent/schemas/food-change-dto-v1.json](../doc/food-agent/schemas/food-change-dto-v1.json) | 프로젝트 문서 food-change-dto-v1 | 외부 명세 (원본 보존) |
| [doc/food-agent/schemas/food-change-v1.json](../doc/food-agent/schemas/food-change-v1.json) | 프로젝트 문서 food-change-v1 | 외부 명세 (원본 보존) |
| [doc/food-agent/schemas/food-record-v2.json](../doc/food-agent/schemas/food-record-v2.json) | 프로젝트 문서 food-record-v2 | 외부 명세 (원본 보존) |
| [doc/food-agent/screenshots/review-journey.jpg](../doc/food-agent/screenshots/review-journey.jpg) | 프로젝트 문서 review-journey | 외부 명세 (원본 보존) |
| [doc/food-agent/service-workflow.md](../doc/food-agent/service-workflow.md) | 프로젝트 문서 service-workflow | 파일 상단 헤더 + 외부 목록 |
| [doc/food-agent/technology-review.md](../doc/food-agent/technology-review.md) | 프로젝트 문서 technology-review | 파일 상단 헤더 + 외부 목록 |
| [doc/food-agent/validate_contract.py](../doc/food-agent/validate_contract.py) | 프로젝트 문서 validate_contract | 파일 상단 헤더 + 외부 목록 |
| [doc/food-agent/validate_design.py](../doc/food-agent/validate_design.py) | 프로젝트 문서 validate_design | 파일 상단 헤더 + 외부 목록 |
| [doc/food-agent/validation-report.json](../doc/food-agent/validation-report.json) | 프로젝트 문서 validation-report | 외부 명세 (원본 보존) |
| [doc/submission/background-sources.md](../doc/submission/background-sources.md) | 프로젝트 문서 background-sources | 파일 상단 헤더 + 외부 목록 |
| [doc/submission/before-after.md](../doc/submission/before-after.md) | 프로젝트 문서 before-after | 파일 상단 헤더 + 외부 목록 |
| [doc/submission/before-after/01-table-preservation.md](../doc/submission/before-after/01-table-preservation.md) | 프로젝트 문서 01-table-preservation | 파일 상단 헤더 + 외부 목록 |
| [doc/submission/before-after/02-ocr-lifecycle.md](../doc/submission/before-after/02-ocr-lifecycle.md) | 프로젝트 문서 02-ocr-lifecycle | 파일 상단 헤더 + 외부 목록 |
| [doc/submission/before-after/03-review-contract.md](../doc/submission/before-after/03-review-contract.md) | 프로젝트 문서 03-review-contract | 파일 상단 헤더 + 외부 목록 |
| [doc/submission/before-after/04-embedded-labels.md](../doc/submission/before-after/04-embedded-labels.md) | 프로젝트 문서 04-embedded-labels | 파일 상단 헤더 + 외부 목록 |
| [doc/submission/benchmark-view.html](../doc/submission/benchmark-view.html) | 프로젝트 문서 benchmark-view | 파일 상단 헤더 + 외부 목록 |
| [doc/submission/demo-guide.md](../doc/submission/demo-guide.md) | 프로젝트 문서 demo-guide | 파일 상단 헤더 + 외부 목록 |
| [doc/submission/presentation-5min.md](../doc/submission/presentation-5min.md) | 프로젝트 문서 presentation-5min | 파일 상단 헤더 + 외부 목록 |
| [doc/submission/requirements-audit.md](../doc/submission/requirements-audit.md) | 프로젝트 문서 requirements-audit | 파일 상단 헤더 + 외부 목록 |
| [doc/submission/screenshots/01-documents.jpg](../doc/submission/screenshots/01-documents.jpg) | 프로젝트 문서 01-documents | 외부 명세 (원본 보존) |
| [doc/submission/screenshots/03-agent-log.jpg](../doc/submission/screenshots/03-agent-log.jpg) | 프로젝트 문서 03-agent-log | 외부 명세 (원본 보존) |
| [doc/submission/screenshots/04-price-table.jpg](../doc/submission/screenshots/04-price-table.jpg) | 프로젝트 문서 04-price-table | 외부 명세 (원본 보존) |
| [doc/submission/screenshots/05-table-filter.jpg](../doc/submission/screenshots/05-table-filter.jpg) | 프로젝트 문서 05-table-filter | 외부 명세 (원본 보존) |
| [doc/submission/screenshots/06-review.jpg](../doc/submission/screenshots/06-review.jpg) | 프로젝트 문서 06-review | 외부 명세 (원본 보존) |
| [doc/submission/screenshots/07-food-db.jpg](../doc/submission/screenshots/07-food-db.jpg) | 프로젝트 문서 07-food-db | 외부 명세 (원본 보존) |
| [doc/submission/screenshots/08-food-edit.jpg](../doc/submission/screenshots/08-food-edit.jpg) | 프로젝트 문서 08-food-edit | 외부 명세 (원본 보존) |
| [doc/submission/screenshots/09-before-after.jpg](../doc/submission/screenshots/09-before-after.jpg) | 프로젝트 문서 09-before-after | 외부 명세 (원본 보존) |
| [doc/submission/screenshots/10-history-evidence.jpg](../doc/submission/screenshots/10-history-evidence.jpg) | 프로젝트 문서 10-history-evidence | 외부 명세 (원본 보존) |
| [doc/submission/screenshots/11-table-agent-log.jpg](../doc/submission/screenshots/11-table-agent-log.jpg) | 프로젝트 문서 11-table-agent-log | 외부 명세 (원본 보존) |
| [doc/submission/screenshots/12-model-calls.jpg](../doc/submission/screenshots/12-model-calls.jpg) | 프로젝트 문서 12-model-calls | 외부 명세 (원본 보존) |
| [doc/submission/table-demo-result.json](../doc/submission/table-demo-result.json) | 프로젝트 문서 table-demo-result | 외부 명세 (원본 보존) |
| [doc/submission/table-preservation-benchmark.json](../doc/submission/table-preservation-benchmark.json) | 프로젝트 문서 table-preservation-benchmark | 외부 명세 (원본 보존) |
| [frontend/index.html](../frontend/index.html) | Vue 애플리케이션 index | 파일 상단 헤더 + 외부 목록 |
| [frontend/package-lock.json](../frontend/package-lock.json) | Vue 애플리케이션 package-lock | 외부 명세 (원본 보존) |
| [frontend/package.json](../frontend/package.json) | Vue 애플리케이션 package | 외부 명세 (원본 보존) |
| [frontend/src/App.vue](../frontend/src/App.vue) | Vue 애플리케이션 App | 파일 상단 헤더 + 외부 목록 |
| [frontend/src/api/auth.js](../frontend/src/api/auth.js) | Vue 애플리케이션 auth | 파일 상단 헤더 + 외부 목록 |
| [frontend/src/api/client.js](../frontend/src/api/client.js) | 프런트 공통 API client | 파일 상단 헤더 + 외부 목록 |
| [frontend/src/components/ArchiveDialog.vue](../frontend/src/components/ArchiveDialog.vue) | 삭제 보관·복구 결정 | 파일 상단 헤더 + 외부 목록 |
| [frontend/src/components/CursorPager.vue](../frontend/src/components/CursorPager.vue) | 커서 기반 페이지 이동 | 파일 상단 헤더 + 외부 목록 |
| [frontend/src/components/DocumentBatchDialog.vue](../frontend/src/components/DocumentBatchDialog.vue) | 선택 자료의 일괄 작업 | 파일 상단 헤더 + 외부 목록 |
| [frontend/src/components/EvidenceViewer.vue](../frontend/src/components/EvidenceViewer.vue) | 변경 필드와 원문 근거 조회 | 파일 상단 헤더 + 외부 목록 |
| [frontend/src/components/FoodRecordForm.vue](../frontend/src/components/FoodRecordForm.vue) | 표준 식품 정보 편집 | 파일 상단 헤더 + 외부 목록 |
| [frontend/src/components/FoodRecordTable.vue](../frontend/src/components/FoodRecordTable.vue) | 표준 식품 DTO의 공통 열 표시 | 파일 상단 헤더 + 외부 목록 |
| [frontend/src/components/ImageEvidence.vue](../frontend/src/components/ImageEvidence.vue) | 이미지 근거 위치 표시 | 파일 상단 헤더 + 외부 목록 |
| [frontend/src/components/SourceComparison.vue](../frontend/src/components/SourceComparison.vue) | 원본 이미지·추출 텍스트 비교 | 파일 상단 헤더 + 외부 목록 |
| [frontend/src/components/StatusBadge.vue](../frontend/src/components/StatusBadge.vue) | 상태 표시 | 파일 상단 헤더 + 외부 목록 |
| [frontend/src/components/TableProposalWizard.vue](../frontend/src/components/TableProposalWizard.vue) | 표 행에서 가격 변경안 준비 | 파일 상단 헤더 + 외부 목록 |
| [frontend/src/components/WorkbookTable.vue](../frontend/src/components/WorkbookTable.vue) | 원본 시트·열 필터 조회 | 파일 상단 헤더 + 외부 목록 |
| [frontend/src/composables/useJob.js](../frontend/src/composables/useJob.js) | Vue 애플리케이션 useJob | 파일 상단 헤더 + 외부 목록 |
| [frontend/src/main.js](../frontend/src/main.js) | Vue 애플리케이션 main | 파일 상단 헤더 + 외부 목록 |
| [frontend/src/style.css](../frontend/src/style.css) | Vue 애플리케이션 style | 파일 상단 헤더 + 외부 목록 |
| [frontend/src/utils/agentLogs.js](../frontend/src/utils/agentLogs.js) | Vue 애플리케이션 agentLogs | 파일 상단 헤더 + 외부 목록 |
| [frontend/src/utils/reviewJourney.js](../frontend/src/utils/reviewJourney.js) | Vue 애플리케이션 reviewJourney | 파일 상단 헤더 + 외부 목록 |
| [frontend/src/views/Catalog.vue](../frontend/src/views/Catalog.vue) | 식품 상세·규격·연결 정보 | 파일 상단 헤더 + 외부 목록 |
| [frontend/src/views/Documents.vue](../frontend/src/views/Documents.vue) | 자료 등록·선택·삭제·복구·영구 삭제 | 파일 상단 헤더 + 외부 목록 |
| [frontend/src/views/ExtractionReview.vue](../frontend/src/views/ExtractionReview.vue) | 품목 선택·원문 대조·수정·최종 반영 | 파일 상단 헤더 + 외부 목록 |
| [frontend/src/views/FoodCatalog.vue](../frontend/src/views/FoodCatalog.vue) | 표준 식품 목록과 삭제·복구 | 파일 상단 헤더 + 외부 목록 |
| [frontend/src/views/Jobs.vue](../frontend/src/views/Jobs.vue) | 비동기 작업 상태·취소·재시도 | 파일 상단 헤더 + 외부 목록 |
| [frontend/src/views/Prices.vue](../frontend/src/views/Prices.vue) | 승인된 단가 조회 | 파일 상단 헤더 + 외부 목록 |
| [frontend/src/views/Reference.vue](../frontend/src/views/Reference.vue) | 원본 자료·근거·표 조회 | 파일 상단 헤더 + 외부 목록 |
| [frontend/src/views/Reviews.vue](../frontend/src/views/Reviews.vue) | 검토할 변경안 목록 | 파일 상단 헤더 + 외부 목록 |
| [frontend/src/views/Sources.vue](../frontend/src/views/Sources.vue) | 사이트 연결·업데이트 수집 | 파일 상단 헤더 + 외부 목록 |
| [frontend/tests/agentLogs.test.js](../frontend/tests/agentLogs.test.js) | 기능·경계·회귀 검증 | 파일 상단 헤더 + 외부 목록 |
| [frontend/tests/auth.test.js](../frontend/tests/auth.test.js) | 기능·경계·회귀 검증 | 파일 상단 헤더 + 외부 목록 |
| [frontend/tests/reviewJourney.test.js](../frontend/tests/reviewJourney.test.js) | 기능·경계·회귀 검증 | 파일 상단 헤더 + 외부 목록 |
| [frontend/vite.config.js](../frontend/vite.config.js) | Vue 애플리케이션 vite.config | 파일 상단 헤더 + 외부 목록 |
| [mcp_server.py](../mcp_server.py) | 식품 도메인 MCP stdio 제공 | 파일 상단 헤더 + 외부 목록 |
| [migrations/001_initial.sql](../migrations/001_initial.sql) | DB 스키마 001_initial | 파일 상단 헤더 + 외부 목록 |
| [migrations/002_price_workbooks.sql](../migrations/002_price_workbooks.sql) | DB 스키마 002_price_workbooks | 파일 상단 헤더 + 외부 목록 |
| [migrations/003_source_connections.sql](../migrations/003_source_connections.sql) | DB 스키마 003_source_connections | 파일 상단 헤더 + 외부 목록 |
| [migrations/004_workbook_assets.sql](../migrations/004_workbook_assets.sql) | DB 스키마 004_workbook_assets | 파일 상단 헤더 + 외부 목록 |
| [migrations/005_sheet_headers.sql](../migrations/005_sheet_headers.sql) | DB 스키마 005_sheet_headers | 파일 상단 헤더 + 외부 목록 |
| [migrations/006_food_profiles.sql](../migrations/006_food_profiles.sql) | DB 스키마 006_food_profiles | 파일 상단 헤더 + 외부 목록 |
| [migrations/007_record_archives.sql](../migrations/007_record_archives.sql) | DB 스키마 007_record_archives | 파일 상단 헤더 + 외부 목록 |
| [migrations/008_asset_cleanup.sql](../migrations/008_asset_cleanup.sql) | DB 스키마 008_asset_cleanup | 파일 상단 헤더 + 외부 목록 |
| [migrations/009_job_fairness.sql](../migrations/009_job_fairness.sql) | DB 스키마 009_job_fairness | 파일 상단 헤더 + 외부 목록 |
| [output/presentation/food-ledger-5min.pdf](../output/presentation/food-ledger-5min.pdf) | 프로젝트 설정 food-ledger-5min.pdf | 외부 명세 (원본 보존) |
| [output/presentation/food-ledger-5min.pptx](../output/presentation/food-ledger-5min.pptx) | 프로젝트 설정 food-ledger-5min.pptx | 외부 명세 (원본 보존) |
| [readmd.md](../readmd.md) | 프로젝트 문서 readmd | 파일 상단 헤더 + 외부 목록 |
| [requirements.txt](../requirements.txt) | Python 의존성 명세 | 파일 상단 헤더 + 외부 목록 |
| [run.sh](../run.sh) | 개발·운영 보조 run | 파일 상단 헤더 + 외부 목록 |
| [scripts/benchmark-table-preservation.py](../scripts/benchmark-table-preservation.py) | 개발·운영 보조 benchmark-table-preservation | 파일 상단 헤더 + 외부 목록 |
| [scripts/demo-preflight.py](../scripts/demo-preflight.py) | 개발·운영 보조 demo-preflight | 파일 상단 헤더 + 외부 목록 |
| [scripts/dev.sh](../scripts/dev.sh) | 개발·운영 보조 dev | 파일 상단 헤더 + 외부 목록 |
| [scripts/evaluate-agent-model.py](../scripts/evaluate-agent-model.py) | 개발·운영 보조 evaluate-agent-model | 파일 상단 헤더 + 외부 목록 |
| [scripts/example-notice.txt](../scripts/example-notice.txt) | 개발·운영 보조 example-notice | 외부 명세 (원본 보존) |
| [scripts/example-price.csv](../scripts/example-price.csv) | 개발·운영 보조 example-price | 외부 명세 (원본 보존) |
| [scripts/file-specs.py](../scripts/file-specs.py) | 파일 명세·변경 이력 관리 | 파일 상단 헤더 + 외부 목록 |
| [scripts/import-price-workbook.py](../scripts/import-price-workbook.py) | 개발·운영 보조 import-price-workbook | 파일 상단 헤더 + 외부 목록 |
| [scripts/reconcile-extraction.py](../scripts/reconcile-extraction.py) | 저장된 추출 결과 재정리 CLI | 파일 상단 헤더 + 외부 목록 |
| [scripts/start-postgres.sh](../scripts/start-postgres.sh) | 개발·운영 보조 start-postgres | 파일 상단 헤더 + 외부 목록 |
| [server.py](../server.py) | 프로젝트 설정 server.py | 파일 상단 헤더 + 외부 목록 |

갱신: `python3 scripts/file-specs.py --apply` (누락 헤더 추가), `--refresh` (현재 파일/이력 snapshot 갱신), `--check` (형식·coverage·해시 검사).

변경 이력 작성 규칙과 원본 보존 범위는 [file-header-policy.md](file-header-policy.md)를 참고하세요.
