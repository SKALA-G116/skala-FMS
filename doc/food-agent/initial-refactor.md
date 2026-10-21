# 초기 도메인 리팩토링 보고서

## 문제와 변경

신규 식품 서비스에서 인증·자료 수집·단가표·분석·승인·이력 처리가 하나의 FastAPI dispatch에 모여 있었다. 서비스별 기능을 수정할 때 영향 범위가 넓고 실제 API 경로가 도메인별로 드러나지 않는 문제가 있었다.

- `api/main.py`를 애플리케이션 조립·미들웨어·수명 관리로 축소했다.
- `api/transport.py`에 인증·CSRF·권한·업로드 제한·중복 요청 방지·트랜잭션 경계를 유지했다.
- 도메인별 `api.py`에 실제 FastAPI 경로와 업무 처리를 분리하고 문서화 경로/operation ID를 제공했다.
- 식품 조회는 catalog, 승인된 DB 쓰기는 review.application으로 분리했다.
- 분석 작업 등록은 ingestion.collection에서 analysis.service로 옮겼다.
- 버전별 계약 검증은 review에서 공통 infrastructure.contracts로 분리했다.
- 새 도메인 코드의 wildcard import와 이전 경로 역의존을 없앴다.
- 기존 모듈 경로를 호환 진입점으로 유지하고 실제 개발 위치는 domains 아래로 통일했다.
- 장애 진단 예제·채팅 UI·SQLite 대화 기록 코드는 legacy 아래로 격리했다.
- 루트 server.py, mcp_server.py, run.sh를 신규 서비스 진입점으로 정리했다.
- Docker의 worker 진입점과 host Ollama 연결 설정을 수정했다.

## 보존한 계약

세션/CSRF, 역할별 권한, 업무 변경의 Idempotency-Key, 변경안 ETag, 원문·대상 버전 검사, 기간 충돌 검사, 묶음 반영의 원자성, 원문 근거와 감사 이력을 보존한다. reader 로그아웃에는 업무 변경 권한이나 중복 요청 키를 새로 요구하지 않는다.

## 검증 결과

| 검증 | 결과 |
|---|---|
| 별도 PostgreSQL 테스트 DB 전체 테스트 | 69 passed in 7.61s (최종 실행 진입점·설정 정리 후) |
| 실제 MCP stdio 전송 | 기존 테스트에 포함, 기본 읽기 도구·Resource·Prompt 확인 |
| Vue 사용자 흐름 단위 테스트 | 5 passed |
| 프런트 배포 빌드 | Vite production build 성공, 1605 modules |
| 리팩토링 앱 정적 UI/API smoke | /, /health, /docs, /openapi.json 모두 200; 미인증 products 401; 루트 server 진입점 동일 app 확인 |
| Docker 컨테이너 기동 | 로컬 Docker 미설치로 실행하지 않음 |
| 실제 사이트·실제 LLM/OCR 전체 수집 | 이번 구조 변경의 회귀 테스트에서는 실행하지 않음 |

실행 중인 기존 프로젝트와 DB는 수정하지 않았으며, 별도 `skala-FMS` 작업 폴더와 `food_fms_refactor_test` DB를 사용했다. 모델 테스트는 명시적인 테스트 대역으로 실제 모델 호출과 구분한다.

## 다음 단계

도메인 중심 구조를 마련한 초기 리팩토링이다. 모든 도메인 객체의 완전한 DDD/ORM 전환, 대규모 DB 검색, 자율 MCP 계획 루프, 운영 배포 자동화까지 완성한 것으로 보지 않는다. 실행 명세와 실제 한계는 루트 [readmd.md](../../readmd.md)를 우선한다.
