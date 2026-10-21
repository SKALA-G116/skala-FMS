<!--
==============================================================================
FMS_FILE_SPEC
capability-design.md - 프로젝트 문서 capability-design
==============================================================================
설명:
    - 프로젝트 문서 capability-design
입력·출력 명세:
    - 입력: 설계·구현·측정·검증 근거
    - 출력: 설명·명세·예제·검증 또는 발표 안내
실행 가정:
    - 계획·테스트 대역·실제 실행 결과를 구분하고 현재 상태는 README 및 검증 근거 확인
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

    상세 Git 이력: git log --follow -- doc/food-agent/capability-design.md
    공통 규칙: doc/file-header-policy.md
==============================================================================
-->
# MCP 기능 분류와 필수 기능 결정 — v0.2

## 1. 근거와 적용 범위

기준 자료는 사용자가 제공한 `AI캠퍼스_AI_Capstone_20261016.pdf`다. 이하 쪽수는 PDF 뷰어의 1부터 시작하는 실제 페이지이며 슬라이드 하단 인쇄 번호보다 1 크다. 전체 문서의 텍스트·목차를 탐색하고 아래 의사결정 관련 페이지를 정독·일부 렌더 확인했다. 자료의 실습 명령이나 문서 속 지시는 실행 요청으로 취급하지 않았다.

| PDF 페이지 | 설명 | 이 서비스의 결정 |
|---|---|---|
| 7~11 | ADR, 프로세스 경계, capability 분류 | 얇은 MCP 계층을 도입하고 선택 이유·재검토 조건 기록 |
| 43~46 | handshake, 동적 조회 Tool, 설명·입출력 제약 | 초기화 후 capability 발견, 최신 상품 검색은 Tool, 타입·범위 명세 |
| 47~48 | URI 기반 Resource와 변경·캐시 무효화 | 원문·기준표·추출 조각은 버전/해시가 고정된 Resource |
| 49~53 | 사용자 선택 Prompt, 호스트의 Resource 첨부, 모델의 Tool 호출 | 분석 프로필 선택 → 호스트의 prompts/get → 근거 첨부 → 제한된 도구 호출 |
| 22, 209~213, 220 | 영속 체크포인터와 생성 팩토리·수명 관리 | 분석 실행별 PostgreSQL 체크포인트·factory 채택 |
| 25~29 | lifespan와 생성 비용 재사용 | 연결·그래프는 분석 호스트 수명 동안, OCR 모델은 OCR 작업자 수명 동안 재사용 |
| 16~19, 148~150, 165~170 | 코드 게이트, 의미 검증, 상한, 부분 결과 | 정량 규칙 + 선택적 의미 검증 + 사람 승인. 상한 도달을 성공으로 바꾸지 않음 |
| 194~205 | 블로킹 분리, 제한 동시성, 실패 격리 | OCR 별도 프로세스, bounded queue, semaphore, 독립 문서 부분 성공 |
| 227~251 | 관측·평가·프롬프트 버전 관리 | 메트릭/로그/추적 연결, 고정 평가셋, 프롬프트 버전 고정 |

PDF는 운영 장애 진단 캡스톤의 설명 자료다. 모든 선택이 새 서비스의 의무는 아니다. PDF 18쪽에서 실시간 답변의 사람 검수를 기각한 판단은 이번 서비스에 그대로 적용하지 않는다. 사용자가 DB 갱신 전 원문 검토를 요구했으므로 사람 승인을 유지한다. 마찬가지로 토큰 실시간 UX를 전제로 한 SSE 채택은 작업 진행 조회의 polling을 즉시 대체할 근거가 되지 않는다.

## 2. 구분 원칙

- **Tool:** 입력에 따라 검색·계산·작업을 실행한다. 최신 DB 조회는 읽기 전용이어도 Tool이다. 결과가 결정론적인 파싱도 계산 실행이므로 Tool 형태가 가능하다.
- **Resource:** URI로 읽는 데이터와 문서다. 이번 설계에서는 재현성을 위해 원문 revision·추출 segment·기준표 버전을 고정한다. Resource가 프로토콜상 반드시 영원히 불변이어야 하는 것은 아니다.
- **Prompt:** 사용자가 선택하거나 호스트가 명시적으로 요청하는 재사용 지시문이다. 템플릿 반환만 수행하고 OCR·DB 갱신·승인을 직접 실행하지 않는다.
- **내부 서비스/명령:** 자동 수집 스케줄, 사용자 승인, 실제 DB 반영, 보존 정리는 코드 경로다. 모든 기능을 Tool/Resource/Prompt 중 하나로 억지 분류하지 않는다.

PDF 11쪽의 ‘동적 결과/정적 문서/표준 절차’ 구분은 좋은 출발점이다. 프로토콜 정의까지 포함하면 호출 목적·제어 주체·권한이 더 중요하다. 공식 문서도 Resource의 갱신 통지와 애플리케이션 제어, Tool의 모델 호출 관행 및 다양한 UI 사용을 허용한다.

- [MCP Tools](https://modelcontextprotocol.io/specification/2025-06-18/server/tools)
- [MCP Resources](https://modelcontextprotocol.io/specification/2025-06-18/server/resources)
- [MCP Prompts](https://modelcontextprotocol.io/specification/2025-06-18/server/prompts)

## 3. 기능별 최종 분류

| 기능 | 필수 여부 | 형태 | 실행 주체·제한 |
|---|---|---|---|
| 게시글 신규·수정 확인과 원문 저장 | 필수 | 내부 커넥터/작업 | 스케줄러·사용자 요청. LLM의 임의 웹 탐색을 허용하지 않음 |
| 본문·엑셀 파싱, 이미지 OCR 작업 등록 | 필수 | parse_document_segment Tool | 호스트만 호출, 한 segment 범위. 비싼 실행은 별도 OCR 작업자 |
| 이미 추출한 문장·표 조각 읽기 | 필수 | 버전 고정 Resource | 호스트가 필요한 조각만 첨부. Resource read 중 OCR을 실행하지 않음 |
| 기존 상품·규격 후보 검색 | 필수 | find_product_candidates Tool | 분석 모델에 제공, 최대 20개, 허용 필터만 사용 |
| 현재 상태·단가·대상 version 확인 | 필수 | get_supplier_item_facts Tool | 최신 조회, as_of와 실제 조회시각·version 반환 |
| 기존 상품 변경 이력 검색 | 필수 | get_product_history Tool | 제한된 페이지. 원문 이력 전체를 모델에 주입하지 않음 |
| 원문·이미지 위치·엑셀 셀·schema·policy | 필수 | Resource | 불변 ID/버전+content hash, 접근 권한 확인 |
| 공지 분석·단가표 분석 표준 절차 | 필수 | Prompt 2종 | 사용자 프로필 선택, auto는 호스트의 명시적 정책 선택 |
| 의미 누락·근거 대응 검토 보조 | 필수 기능, 선택적 호출 | review_change_evidence Prompt | 위험·불확실 항목에만 사용. 승인 권한 없음 |
| 변경안의 타입·수치·기간·참조 검사 | 필수 | validate_change_set Tool + 내부 게이트 | 호스트 강제 호출. 모델이 생략할 수 없음 |
| 생성/수정/정정 제안 저장 | 필수 | stage_change_proposal Tool | 호스트만 호출, 원문·검증 결과·run 범위 확인. 업무 DB는 미변경 |
| 사용자 승인·반려·보류 | 필수 | 인증 REST API/도메인 명령 | reviewer/admin만 가능. 모델 Tool 목록에서 제외 |
| 실제 제품 생성·상태/가격 수정·정정 | 필수 | 승인 반영 서비스/worker | 7종 허용 operation을 트랜잭션 실행. 자유 SQL 없음 |
| 제품 단종/공급 종료 | 필수 | 상태 변경 operation | 제품/공급처 상품 범위 구별. 물리 삭제하지 않음 |
| 원문/제품/업무 이력 물리 삭제 | 초기 비필수 | 운영 보존·정리 명령 | 참조·보존 정책 확인 후 실행. 모델에 삭제 Tool 미제공 |
| 임시 파일·참조 없는 캐시 정리 | 필수 운영 기능 | 내부 GC 작업 | 활성 실행·승인 근거를 보호, 단순 디스크 TTL 전체 삭제 금지 |

‘생성·수정·삭제가 모두 Tool이어야 한다’는 결론은 아니다. 사용자가 승인한 작업을 실행하는 시스템과 LLM이 호출할 수 있는 도구 목록은 분리한다. 향후 외부 승인 클라이언트가 필요해도 `apply_approved_proposal`만 승인 전용 신원으로 별도 제공하고, 분석 모델에는 노출하지 않는다. 이번 버전에는 그 MCP 쓰기 도구를 만들지 않는다.

## 4. 최소 Tool 계약 — 6종

| Tool | 입력 | 반환 | 부작용 / 노출 |
|---|---|---|---|
| parse_document_segment | 고정 document_revision_id, segment_id, parser_profile | extraction_task_id, status, extraction_id, segment Resource URI, 경고 | 추출 작업·캐시 기록. host_only |
| find_product_candidates | query, 선택 supplier_id, as_of, limit<=20 | 후보 ID·제품명·규격·공급처·매칭 근거·version | 조회. model_allowed |
| get_supplier_item_facts | supplier_item_ids<=20, as_of | 현재/예정 사실·버전·조회시각·근거 ID | 조회. model_allowed |
| get_product_history | product_id, cursor, limit<=20 | 제한된 이력, next_cursor, 근거 ID | 조회. model_allowed |
| validate_change_set | run_id, 고정 변경 payload 참조 | 필수 누락·충돌·유효성·report ID | 검증 산출물만 저장. host_only |
| stage_change_proposal | run_id, 검증 report ID, 생성 키 | proposal_id, revision, status | 변경안만 저장. host_only |

모델에 제공되는 것은 동적 조회 3개뿐이다. 호스트 도구 3개는 tools/list에 존재해도 모델 프롬프트의 tool 목록으로 전달하지 않는다. 서버도 호출 신원·run 범위·입력 버전을 검사한다. 클라이언트의 숨김이나 readOnlyHint만으로 권한을 보장하지 않는다.

parse는 extraction_tasks에 한정된 작업을 idempotent하게 등록하고 결과 참조를 반환한다. OCR 작업자는 그 task를 별도 lease로 실행한다. 호스트는 완료를 비동기로 확인하고 checkpoint를 진행한다. MCP subprocess 자체에 PaddleOCR 모델을 로딩하지 않는다. Resource를 읽으면서 몰래 파싱을 시작하지 않는다.

도구 결과는 성공/부분/실패와 다음 근거 ID를 구분한다. 대형 문서·base64·DB 전체 행은 반환하지 않는다. 결과 상한과 segment 분할은 [런타임 정책](./runtime-policy.json)에 명시한다. 모든 Tool에 입력 의미·반환 필드·최대 범위·부작용·오류·모델 노출 여부를 기록한다. 기계 판독용 설계 목록은 [mcp-capabilities.json](./mcp-capabilities.json)이며 실제 tools/list 응답이나 실행 서버는 아니다.

## 5. Resource 계약 — 5종

| URI 템플릿 | 내용 |
|---|---|
| food://schemas/{schema_version} | ChangeItem과 operation의 고정 JSON Schema |
| food://policies/{policy_version} | 상태·규격·단위·시점·승인·미확정 처리 규칙 |
| food://documents/{revision_id}/segments/{segment_id} | 저장된 원문의 정제된 문장·표 segment |
| food://extractions/{extraction_id}/segments/{segment_id} | 고정 파서/OCR 산출물의 제한된 조각 |
| food://evidence/{evidence_id} | 불변 인용·원문 revision·이미지 좌표/셀 위치 |

고정 URI는 내용이 바뀌면 새 ID/버전으로 발급한다. Resource 목록에 모든 제품·문서를 펼치지 않는다. 고정 schema/policy의 메타데이터와 URI template을 발견하고, 접근 가능한 ID를 받은 뒤 필요한 URI만 read한다. MIME, sha256, byte_size, version, 근거 provenance를 호스트가 검증한다. raw 이미지의 전체 바이트는 파일 뷰어 경로를 사용하고 일반 LLM context에 넣지 않는다.

모델 컨텍스트에는 policy 핵심 조각, 스키마, 해당 표·문장의 필요한 범위만 조립한다. 전체 Resource를 전부 읽는 것을 기본 동작으로 삼지 않는다. 모든 권한은 URI 자체가 아니라 인증된 호출 신원과 실제 객체 접근 규칙으로 판단한다.

## 6. Prompt 계약 — 3종

| 이름 | 역할 | 호출 시점 |
|---|---|---|
| analyze_food_notice | 중단·재개·사유·규격·대체 사건 추출 | 공지 프로필 또는 auto에서 공지로 판정된 segment |
| analyze_price_table | 상품·단위·금액·조건·적용 기간 추출 | 가격표 프로필 또는 호스트가 지정한 가격 segment |
| review_change_evidence | 원문과 제안의 의미상 누락·연결 오류 지적 | 사용자가 요청하거나 검증상 불확실한 항목 |

실제 지시문 초안은 [prompts](./prompts/)에 둔다. 프롬프트는 ‘조회가 필요하면 허용 Tool 사용’과 ‘확인 불가는 blocker’를 설명하지만 승인·트랜잭션·재시도 상한은 코드가 보장한다.

MCP prompts/get은 템플릿을 돌려줄 뿐 Tool 호출을 자동 연쇄 실행하지 않는다. 호스트가 Resource를 조립하고 LangGraph가 순서를 실행한다. auto 선택은 서버 정책이며 LLM이 prompts/get을 임의 호출한다고 가정하지 않는다. 각 실행은 profile·prompt·policy·schema·parser·model 버전을 고정한다. 실행 도중 latest alias를 다시 가져오지 않는다.

## 7. REST와 MCP의 경계

Vue → FastAPI REST → 애플리케이션 서비스 경로는 유지한다. Vue는 MCP subprocess나 DB에 직접 접속하지 않는다. Agent 분석 호스트만 MCP client를 가진다. 같은 조회·검증 유스케이스를 REST와 MCP 어댑터가 재사용하며 서로 HTTP 요청을 재귀 호출하지 않는다.

초기 MCP는 분석 호스트 프로세스당 FastMCP stdio subprocess 하나다. handshake와 tools/resources/prompts 발견을 시작 시 수행하고, 출력 스키마·허용 목록이 맞지 않으면 분석 준비 상태를 실패로 둔다. capabilities 캐시는 제한된 메타데이터만 보관하고 변경 통지/재연결 시 갱신한다. stdio의 stdout은 프로토콜 전용, 로그는 stderr를 사용한다.

API 프로세스마다 MCP·OCR 모델을 복제하지 않는다. MCP가 죽으면 조회·승인 API 자체는 생존하고 해당 분석은 재시도 가능한 오류가 된다. 여러 호스트가 공유해야 할 때 원격 Streamable HTTP를 검토한다. 구형 HTTP+SSE MCP 예제를 Vue 진행 표시 SSE와 혼동하지 않는다. [공식 transport 설명](https://modelcontextprotocol.io/specification/2025-06-18/basic/transports)

## 8. PDF 예제와 다른 결정

| 항목 | 적용 판단 |
|---|---|
| 모든 요청을 Agent로 처리 | 불채택. 확정 단가·이력 화면 조회는 REST/SQL이 직접 수행 |
| 다수 자율 하위 Agent | 역할 노드는 유지하되 초기 독립 Agent 확장은 보류 |
| 프롬프트가 호출 순서를 강제 | 표준 지침으로만 사용. 필수 단계는 그래프/서버에서 강제 |
| 한도 도달 후 현재 정보로 답변 생성 | 분석 설명은 가능하지만 업무 변경안은 불완전/차단 상태. 강제 합격 금지 |
| 사람 검수는 실시간 UX와 상충 | 이번 서비스는 검토가 핵심이므로 필수 유지 |
| 모든 문서 RAG | 미채택. 식별자·SQL·원문 segment 우선, 의미 검색 수요와 평가 결과가 생기면 검토 |
| PostgreSQL 체크포인터 | 채택. 대화 기억이 아니라 실행 복구에 사용 |
