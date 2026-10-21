<!--
==============================================================================
FMS_FILE_SPEC
frontend-spec.md - 프로젝트 문서 frontend-spec
==============================================================================
설명:
    - 프로젝트 문서 frontend-spec
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

    상세 Git 이력: git log --follow -- doc/food-agent/frontend-spec.md
    공통 규칙: doc/file-header-policy.md
==============================================================================
-->
# Vue 프런트엔드 명세

## 1. 기본 구성

Vue 3 + TypeScript + Vue Router를 사용한다. 화면 단위는 views, 재사용 표현 단위는 components, API·비동기 로직은 composables와 api에 둔다. Pinia는 로그인 사용자·역할·전역 알림 같은 작은 상태에 한정한다. 모든 검색 결과와 파일을 전역 store에 쌓지 않는다.

기존 CDN 단일 HTML은 기능·화면·타입을 분리하는 빌드 구조로 교체한다. 새 앱의 실제 파일은 이번 명세에서 생성하지 않는다.

## 2. 라우트와 화면

| URL | View | 핵심 컴포넌트 | 사용하는 API |
|---|---|---|---|
| /login | LoginView | LoginForm | auth/csrf, auth/session |
| / | DashboardView | PendingSummary, RecentJobs | dashboard, jobs |
| /collection | CollectionView | SourceSelector, CollectionRunForm, JobProgress | sources, collection-runs, jobs |
| /documents | DocumentListView | DocumentFilters, DocumentTable | documents |
| /documents/:id | DocumentDetailView | DocumentVersions, AssetList, AnalysisProfileSelect, AnalyzeButton | document 상세·versions·analysis-profiles·analysis-runs |
| /reviews | ReviewQueueView | ProposalFilters, ProposalTable | proposals |
| /reviews/:id | ReviewDetailView | ProposalEditor, TargetMatcher, ChangeDiff, EvidenceViewer, DecisionBar | proposal 상세·PATCH·validate·decisions·withdraw-approval·applications |
| /prices | PriceListView | PriceFilters, PriceTable, PriceConditionBadge | prices, suppliers |
| /products | ProductListView | ProductSearch, ProductTable | products |
| /products/:id | ProductDetailView | VariantTabs, SupplierItemTable, ScheduledFacts, SubstitutionPanel | product 상세·variants(다음 페이지)·supplier-items·prices·history(예정 변경)·substitutions |
| /products/:id/history | ProductHistoryView | HistoryFilters, HistoryTimeline, AuditDiff | products/{id}/history |
| /history/:id | AuditEventDetailView | AuditDiff, EvidenceLinks | audit-events/{id} |
| /evidence/:id | EvidenceDetailView | EvidenceViewer | evidence, document revision, asset access |
| /jobs | JobListView | JobFilters, JobTable | jobs |
| /jobs/:id | JobDetailView | JobProgress, JobErrors, RetryCancelActions | jobs 상세·retry·cancel |

URL의 검색 query는 q, supplier_id, as_of, status, cursor 등으로 표현해 뒤로 가기·새로고침을 지원한다. 원문 단가표 목록과 확정 가격 DB 조회를 다른 메뉴로 둔다. 자료를 찾는 행위와 가격 DB 조회를 모두 ‘조회’ 버튼 하나로 합치지 않는다.

## 3. 디렉터리와 책임

```text
src/
  views/             # 라우트 단위 조합, 데이터 로딩과 권한별 행동 연결
  components/
    common/          # DataTable, CursorPager, EmptyState, ErrorState, ConfirmDialog
    documents/       # SourceBadge, AssetList, DocumentVersions
    review/          # ChangeDiff, ProposalEditor, TargetMatcher, DecisionBar
    evidence/        # EvidenceViewer, ImageRegionViewer, HtmlBlockViewer, SheetRangeViewer
    products/        # VariantTabs, SupplierItemTable, SubstitutionPanel
    prices/          # PriceTable, PriceConditionBadge
    history/         # HistoryTimeline, AuditDiff
    jobs/            # JobProgress, JobErrors
  composables/       # useJobPolling, useProposal, useEvidence, useCursorQuery
  api/               # client, generated DTO, auth/documents/proposals/products/prices/jobs
  stores/            # auth, notifications
  router/            # route records and permission metadata
  types/             # UI 전용 타입; API DTO를 중복 작성하지 않음
```

components는 props와 emits로 상태를 전달하고 임의로 업무 반영 API를 호출하지 않는다. view/composable이 사용자 행동을 API 명령에 연결한다. 공통 API client는 쿠키·CSRF·request_id·표준 오류를 처리한다.

## 4. 변경안 검토 상세

PC에서는 왼쪽 원문, 오른쪽 변경안의 두 영역을 사용한다. 작은 화면에서는 원문/변경안 탭으로 전환한다.

```text
제목 / 출처 / 현재 상태 / 자료 불완전·충돌 경고
┌────────────────────┬────────────────────────┐
│ 원문 버전·첨부 선택 │ 제품·규격·공급처 연결    │
│ 문장·표·이미지 강조 │ 현재 값 → 변경 예정 값 │
│                    │ 적용일·사유·대체 구성   │
│                    │ 필드별 근거·수정 이유   │
└────────────────────┴────────────────────────┘
저장 / 재검증 / 보류 / 반려 / 승인
승인 후: 승인 revision 표시 / 반영 요청 / 승인 철회
```

- 승인 버튼은 서버의 can_approve와 blockers를 기준으로 표시한다. 프런트 검증만으로 우회하지 않는다.
- 편집 후 저장 전에는 승인·반영을 비활성화한다. 변경 내용이 있으면 페이지 이탈 확인을 한다.
- 저장 요청에는 현재 ETag를 If-Match로 전송한다. 412면 입력을 버리지 않고 최신 데이터와 차이를 보여준다.
- 승인은 내용 revision에 고정된다. approved 상태에서는 편집 대신 승인 철회를 먼저 요청한다.
- 반영 요청은 승인된 내용과 효과를 확인한 뒤 전송한다. 버튼을 잠그고 동일 요청에는 같은 Idempotency-Key를 사용한다.
- applying은 새로고침 후에도 서버 상태로 복원한다. 적용 실패와 충돌은 다른 상태로 표시한다.
- 조합 대체품은 AND 구성과 OR 선택지를 구분하고, 연결 미확정은 링크 없는 설명으로 표시한다.

## 5. 단가·제품·이력 화면

PriceTable의 필수 열: 제품명, 규격, 공급처, 품목코드, 금액·통화, 기준 수량/단위, 세금, 가격 유형·조건, 적용 기간, 근거. 금액은 서버 문자열을 포맷만 하며 가격 정규화는 서버가 담당한다.

ProductDetail은 전체 제품 상태와 공급처 상품 상태를 분리한다. ‘단종’ 배지를 무조건 모든 규격에 전파하지 않는다. 미래 가격·상태는 ‘예정’으로 표시하고 기본 현재 값에 섞지 않는다. 가격은 /prices?product_id=...&as_of=...&include_scheduled=true, 예정 변경은 /products/{id}/history?effective_start_after={상세 응답의 as_of}를 사용한다. 공급처 상품 후보 응답은 제품명·규격·바코드도 포함해 추가 조회 없이 비교할 수 있게 한다. as_of를 과거로 바꾸면 그 기준 상태임을 상단에 명시한다.

HistoryTimeline에는 생성/변경/정정, recorded_at, effective_from/to, 대상 규격·공급처, before/after, 검토자·반영 주체, 사유와 근거 링크를 표시한다. ‘오늘 입력했지만 다음 달 적용’이 한눈에 구분되어야 한다. 정정은 이전 사건 링크를 함께 표시한다.

EvidenceViewer는 원문 snapshot과 좌표·셀·블록을 사용한다. 이미지 확대·축소 시 bbox도 같은 변환을 적용한다. OCR 회전 보정 좌표를 원본 좌표로 오해하지 않는다. API URL 만료는 재발급하고 파일 자체 접근 불가는 별도 안내한다.

## 6. 비동기 작업과 상태

MVP는 GET job polling을 사용한다. 초기 2초, 이후 5초, 오래 걸리면 10초 정도로 backoff하며 실제 기준은 조정 가능하다. 페이지가 숨겨지면 빈도를 낮추고 view 해제 시 타이머·요청을 정리한다. succeeded/partial/failed/cancelled에서 중단한다. 새로고침은 job_id로 재조회한다.

SSE는 후속 개선이며 현재 OpenAPI 계약에는 포함하지 않는다. SSE가 끊겼다는 이유로 작업을 실패로 판단하지 않는다.

목록 요청은 검색 debounce와 이전 요청 취소 또는 최신 요청 ID 비교로 늦게 온 응답의 덮어쓰기를 막는다. 검색 조건 변경 시 cursor를 초기화한다. 초기 로딩·빈 결과·부분 데이터·실패를 구분한다.

## 7. 접근과 오류

같은 origin의 세션 쿠키를 사용한다. access token을 localStorage에 저장하지 않는다. CSRF 토큰은 메모리에 두고 새로고침 시 /auth/csrf로 다시 받는다. 로그인 후 토큰을 재발급한다.

401은 로그인 이동, 403은 권한 안내, 409는 업무 충돌·중복 키 안내, 412는 최신 변경안 비교, 422는 필드 오류, 429는 Retry-After 대기를 표시한다. 네트워크 실패 시 mutation을 새 키로 무조건 재전송하지 않는다. 동일 키의 결과를 확인하거나 서버 리소스를 재조회한다.

## 8. 프런트와 백엔드의 계약

API DTO는 openapi.json에서 생성하는 것을 목표로 한다. 생성 도구와 빌드 의존성은 실제 앱 구현 시 고정한다. UI는 `permissions`/`allowed_actions`를 참고하지만 최종 권한과 상태 전이는 서버가 검증한다. 예시 JSON으로 읽기 화면을 먼저 구현할 수 있으나 mock 승인을 실제 반영 성공처럼 표시해서는 안 된다.

Vue Router의 동적 경로를 통해 상품·이력·근거 상세를 직접 링크한다. [공식 라우팅 문서](https://router.vuejs.org/guide/essentials/route-matching-syntax.html)

## 9. v0.2 프로필·자원 처리

분석 프로필은 GET /analysis-profiles에서 가져온다. POST /analysis-runs의 workflow_profile에 auto/notice/price_table을 보낸다. 202의 analysis_run_id를 사용해 입력·처리 버전과 결과 연결을 조회할 수 있다. 일반 사용자에게 thread ID·메모리 내부 구조를 노출하지 않고 누락 자료·미완료 범위·재시도 가능 여부를 설명한다.

원문 이미지는 필요한 페이지만 lazy load한다. view 해제 시 canvas 참조와 Blob URL을 해제하고 polling·event listener·진행 중 요청을 정리한다. 목록과 제품 규격·공급처 상세는 페이지 단위로 보관한다. 전역 store에 전체 파일·OCR 배열·과거 원문을 누적하지 않는다.

제품 상세의 variants/supplier_items는 처음 20개 미리보기다. variants_next_cursor와 supplier_items_next_cursor를 각각 관련 목록 API에 연결한다. 문서 body_truncated가 true면 미리보기만으로 검토 완료를 표시하지 않고 원문 asset/segment를 열게 한다.
