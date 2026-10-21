<!--
==============================================================================
FMS_FILE_SPEC
api-guide.md - 프로젝트 문서 api-guide
==============================================================================
설명:
    - 프로젝트 문서 api-guide
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

    상세 Git 이력: git log --follow -- doc/food-agent/api-guide.md
    공통 규칙: doc/file-header-policy.md
==============================================================================
-->
# API 사용 안내

## 1. 계약의 성격

기본 경로는 같은 origin의 `/api/v1`이다. [openapi.json](./openapi.json)은 OpenAPI 3.1.0으로 작성한 구현 전 계약이다. FastAPI에서 이미 실행되는 API가 아니다. 실제 앱 구현에서는 이 계약과 응답 DTO를 맞추고 필요하면 클라이언트 타입을 생성한다. [OpenAPI 표준](https://spec.openapis.org/oas/v3.1.0.html)

모든 ID는 UUID, 시각은 timezone이 있는 ISO 8601, 업무 적용일은 `YYYY-MM-DD`다. 금액과 수량은 10진 문자열로 주고받는다. `effective_to=null`은 종료 미정이며 시작일 포함·종료일 미포함이다.

## 2. 인증과 권한

1. `GET /auth/csrf`로 로그인 전 토큰을 받는다. 서버는 사전 세션과 토큰을 연결한다.
2. `POST /auth/session`에 username/password와 `X-CSRF-Token`을 보낸다. 성공 시 opaque 세션 Cookie를 발급하고 세션 ID를 교체한다.
3. 로그인 성공 후 `/auth/csrf`를 다시 호출해 현재 세션의 토큰을 받는다.
4. GET은 세션 Cookie, mutation은 Cookie와 `X-CSRF-Token`을 사용한다.
5. 로그아웃은 세션을 서버에서 무효화하고 Cookie를 만료시킨다.

세션은 HttpOnly/Secure/SameSite=Lax, 서버는 Origin과 CSRF를 확인한다. 응답·로그에 비밀번호나 사이트 수집 세션을 포함하지 않는다. 역할의 reader 권한은 reviewer/operator/admin에 포함된다. `x-required-roles`는 허용 역할이며 공개 인증 엔드포인트는 빈 배열이다. API별 제한 외에 리소스 접근 권한도 확인한다.

초기 사용자는 배포 초기화로 등록한다. 회원가입·비밀번호 재설정 UI/API는 후속 범위이며, 구현 시 별도 인증 설계가 필요하다. source/업체/거래조건 기준 데이터도 초기화 단계에서 입력한다.

## 3. 조회와 실행을 구분

| 사용자 행동 | 요청 | 업무 데이터 변경 |
|---|---|---|
| 확정 단가 검색 | GET /prices | 없음 |
| 원문 게시글 목록 확인 | GET /documents | 없음 |
| 사이트 새 글 가져오기 | POST /collection-runs | 원문·작업 기록만 생성 |
| 게시글 분석 | POST /analysis-runs | 추출·변경안·작업 기록만 생성 |
| 변경안 수정 | PATCH /proposals/{id} | 변경안 revision만 생성 |
| 승인 | POST /proposals/{id}/decisions | 승인 기록만 생성 |
| 승인안 반영 요청 | POST /proposals/{id}/applications | 반영 작업 등록. 실제 업무 변경은 worker의 트랜잭션 |

## 4. 검토 → 승인 → 반영 예시

아래 ID와 값은 모두 가상 데이터다. 실제 게시글 OCR 결과나 운영 DB를 뜻하지 않는다. 예시 파일은 [examples](./examples/)에 있다.

### 4.1 검토할 변경안 조회

```http
GET /api/v1/proposals/00000000-0000-4000-8000-000000000009
```

응답은 `ETag: "7"`이고, 본문 summary는 다음과 같다.

```json
{
  "status": "ready",
  "version": 7,
  "revision": 2,
  "approved_revision": null
}
```

`version`은 상태와 내용을 포함한 현재 표현 버전이다. `revision`은 변경안 업무 내용 버전이다. 전체 응답은 [proposal-ready.json](./examples/proposal-ready.json)을 참고한다.

### 4.2 승인

```http
POST /api/v1/proposals/00000000-0000-4000-8000-000000000009/decisions
Content-Type: application/json
X-CSRF-Token: <현재 세션 토큰>
If-Match: "7"
Idempotency-Key: review-approve-demo-001

{"action":"approve","revision":2,"reason":"원문과 규격을 확인함"}
```

서버가 ready·필수 근거·미확정 항목·권한·대상 revision을 검증한다. 성공 시 ETag는 `"8"`, status는 approved, approved_revision은 2가 된다. 승인 기록은 [proposal-approved.json](./examples/proposal-approved.json)처럼 제안에 연결된다. 이 시점에 식품 DB는 바뀌지 않는다.

hold/reject에는 사유가 필요하다. 승인 이후 내용 수정은 `/withdraw-approval`로 철회한 뒤 수행한다. 편집 중인 화면이 가진 ETag와 다르면 412다.

### 4.3 반영 요청

```http
POST /api/v1/proposals/00000000-0000-4000-8000-000000000009/applications
Content-Type: application/json
X-CSRF-Token: <현재 세션 토큰>
If-Match: "8"
Idempotency-Key: apply-demo-001

{"approved_revision":2}
```

`202 Accepted`와 application/job을 반환한다. [application-accepted.json](./examples/application-accepted.json)을 참고한다. 이 응답은 반영 완료가 아니다. Location은 application 조회 경로다.

`GET /jobs/{job_id}`를 polling하고 완료 후 `/applications/{id}`와 상품·이력을 재조회한다. applied는 DB 기록 완료이며 미래 적용 사실일 수 있다. 작업이 끝났더라도 오늘 가격이 바뀌었다고 가정하지 않는다.

동일 요청의 재전송은 같은 Idempotency-Key를 사용한다. 서버는 이미 처리한 키를 ETag 재검사보다 먼저 찾아 원래 결과를 반환한다. 같은 키에 다른 내용이면 409다. 새로운 키를 사용한 경우에도 동일 proposal+approved_revision에 application을 두 번 만들지 않는다. 기존 application 재사용은 현재 리소스 ETag를 확인하며, 과거 ETag면 412로 최신 조회를 유도할 수 있다.

### 4.4 단가와 이력 조회

```http
GET /api/v1/prices?as_of=2026-10-20&include_scheduled=true&limit=20
GET /api/v1/products/00000000-0000-4000-8000-000000000017/history?limit=20
GET /api/v1/audit-events/00000000-0000-4000-8000-000000000019
```

[price-list.json](./examples/price-list.json)은 미래 적용 가격이 scheduled로 표시되는 예시다. include_scheduled를 생략하면 미래 가격은 기본 현재 목록에 섞지 않는다. [product-history.json](./examples/product-history.json)은 변경 전후·기록시각·적용일·승인자·근거 ID를 포함한다.

## 5. 새 상품과 복합 변경

변경안의 `changes`는 정해진 operation 중 하나다.

| kind | 대상·내용 |
|---|---|
| create_product | 제품명·제조사·브랜드 |
| create_variant | 제품 참조·규격·바코드 |
| create_supplier_item | 규격 참조·공급처·공급처 코드·판매 단위 |
| set_price | 공급처 상품·가격 조건·적용 기간·사유 |
| set_availability | 공급처 상품의 available/temporarily_unavailable/supply_ended/unknown |
| set_product_status | 제품 전체의 active/discontinued/unknown |
| set_substitution | 기존 공급처 상품·대체 구성·선택지·관계 확정 상태·기간 |

새 대상은 제안 안에서 `local_ref`로 참조하고 기존 대상은 id로 참조한다. 서버가 참조 존재·순서·순환을 검사하고 실제 ID를 반영 트랜잭션에서 매핑한다. [신규 상품 묶음 예시](./examples/proposal-new-product-bundle.json)는 구조 설명용이며 근거가 부족한 draft로 명시되어 있다. 새 product/variant/item의 조합도 하나의 승인 묶음으로 처리할 수 있다.

각 변경 항목에는 `field_evidence`가 있고 `field_path`는 operation 내부의 JSON Pointer다. 예를 들어 `/period/effective_from`이 어떤 근거에서 추출됐는지 연결한다. 사용자 판단을 추가하면 origin=reviewer와 이유를 남긴다. 근거 없는 핵심 값을 채우면 승인 차단 대상이다. null 메타데이터나 서버가 만든 ID에 원문 인용을 억지로 요구하지는 않는다.

Pydantic/JSON Schema 타입 검증만으로 업무 승인이 결정되지는 않는다. 양수 수량, 기간 순서, 실제 상품 연결, 업체 역할, 허용된 조건키, 원문 일치·누락·출처 충돌, 대체 순환 등을 서버 서비스가 검증한다. tax=unknown은 원문 미기재를 정직하게 표시하는 값으로 허용할 수 있지만, 거래 조건 자체를 식별하지 못하면 차단한다. 세부 허용 기준은 기준 데이터 규칙으로 확정한다.

PATCH는 자유 JSON Patch를 받지 않고 허용된 changes 전체를 대체한다. 서버가 before·현재 대상 version·diff·검증 결과를 다시 만든다. 잘못된 상품 연결을 사용자가 고쳤다면 수정 이유와 새 근거를 함께 남긴다.

## 6. 원문 근거 조회

```http
GET /api/v1/evidence/00000000-0000-4000-8000-000000000003
GET /api/v1/document-revisions/00000000-0000-4000-8000-000000000004
GET /api/v1/assets/00000000-0000-4000-8000-000000000005/access
```

Evidence는 불변 원문 revision과 연결되며 quote와 위치를 반환한다. 이미지/PDF는 고정 이미지 기준 정규화 bbox, HTML은 block/codepoint offset, 엑셀은 sheet/cell range다. asset access는 권한 확인 후 짧은 URL을 반환한다. URL이나 signed query를 업무 이력의 영구 식별자로 쓰지 않는다.

OCR confidence를 승인 확률로 쓰지 않는다. 리뷰 화면은 추출한 문자와 원문·테이블 구조를 함께 확인하게 한다.

## 7. 목록과 필터

목록은 `{items,next_cursor,has_more}`다. 기본 limit=20, 최대 100. cursor는 검색 조건·마지막 정렬키·신규 자료 watermark에 결합된 서버의 불투명 keyset 값이다. 문서는 first_seen_at 내림차순+ID, 검토함은 created_at 내림차순+ID, 이력은 recorded_at 내림차순+ID로 정렬한다. 정렬키는 불변으로 두어 같은 ID의 중복을 억제하고 페이지 탐색 중 생성된 새 자료는 새 검색에 포함한다. 상태·검색 필드가 동시에 바뀌면 목록 구성은 달라질 수 있으며 완전한 시점 snapshot은 보장하지 않는다. 프런트는 ID 기준으로 중복을 제거하고 상태 변경 후 목록을 새로 조회한다.

as_of를 받는 응답에는 실제 사용한 as_of를 돌려준다. q는 검색어, *_id는 정확한 필터다. recorded 기간은 기록시각, effective 기간은 업무 적용 구간과의 겹침을 검색한다. 게시글 published_from/to는 한국 날짜 범위로 검색한다. 모든 범위의 from은 포함, to는 제외한다. effective_from/to 필터는 해당 구간과 겹치는 이력을 찾는다. 끝이 없는 구간은 열린 구간으로 취급한다. 잘못된 역전 구간은 422다.

최대 파일 크기(초안 20MiB), 페이지 수·재시도·조회 빈도 같은 운영 한도는 설정으로 관리한다. 원문 파일 크기와 OCR에 실제 처리한 이미지·페이지 수를 분리해 기록한다.

## 8. 오류 계약

오류는 `error.code`, `message`, `request_id`, `retryable`과 선택적인 `field_errors`, `details`로 반환한다. 상세 내부 예외·비밀·임의 원문은 노출하지 않는다. 429/503은 Retry-After를 제공할 수 있다.

| HTTP | 대표 code | 프런트 처리 |
|---|---|---|
| 400 | INVALID_CURSOR | 검색 조건과 cursor 재설정 |
| 401 | AUTH_REQUIRED | 로그인으로 이동 |
| 403 | FORBIDDEN / CSRF_INVALID | 권한 안내 또는 토큰 재조회 |
| 404 | NOT_FOUND | 대상 없음/접근 불가 안내 |
| 409 | INVALID_STATE / TARGET_CONFLICT / IDEMPOTENCY_CONFLICT | 최신 상태·차이 확인, 무조건 재시도하지 않음 |
| 412 | STALE_RESOURCE | 편집 입력 보존, 최신 버전 비교 |
| 413 | FILE_TOO_LARGE | 파일 상한 안내 |
| 415 | UNSUPPORTED_MEDIA_TYPE | 허용 형식 안내 |
| 422 | VALIDATION_FAILED | field_errors를 입력과 변경 항목에 연결 |
| 428 | PRECONDITION_REQUIRED | 최신 GET의 ETag 필요 |
| 429 | RATE_LIMITED | Retry-After에 맞춰 대기 |
| 500/503 | INTERNAL_ERROR / TEMPORARY_UNAVAILABLE | request_id 제공, 제한적 재시도 |

FastAPI 기본 422 형식도 이 공통 오류 모양으로 정규화한다. job이 실행 중 실패하면 200 job 조회 안의 status/issues로 전달한다. HTTP 통신 성공과 업무 처리 성공을 혼동하지 않는다.

## 9. v0.2 추가·변경 계약

- GET /analysis-profiles: 사용자 선택 프로필과 고정 prompt/policy/schema 버전을 조회한다.
- POST /analysis-runs: workflow_profile=auto/notice/price_table을 받는다. 202 Job의 analysis_run_id는 재시도 job과 별도 실행 ID다.
- GET /analysis-runs/{analysis_run_id}: 입력·처리 버전·실행 결과·복구 가능 상태를 조회한다. 사용자 직접 checkpoint rewind API는 제공하지 않는다.
- GET /products/{id}/variants: 제품 상세의 다음 규격 페이지를 읽는다. 제품 상세의 규격·공급처 상품은 처음 20개와 next_cursor로 제한한다.
- DocumentRevision.body_text는 최대 8,192자 미리보기이며 body_truncated를 확인한다. 전체 원문은 snapshot/segment로 읽는다.
- 변경안 한 묶음은 최대 50항목이다. 가격표의 독립 행은 여러 변경안으로 나누고 연관 생성·대체만 원자적으로 묶는다.
- MCP Tools/Resources/Prompts는 내부 JSON-RPC 계층이다. Vue의 REST 계약에 /tools/call 같은 공개 경로를 추가하지 않는다.
- BUDGET_EXCEEDED, INCOMPLETE_SOURCE, STALE_PROCESSING_VERSION은 job issues 또는 422/409의 error.code로 구분한다. 상한 도달이 업무 성공으로 바뀌지 않는다.

## 10. 엔드포인트 목록

| Method | 경로 (/api/v1 뒤) | 역할 | 목적 |
|---|---|---|---|
| GET | `/auth/csrf` | 공개 | CSRF 토큰 조회 |
| POST | `/auth/session` | 공개 | 로그인 |
| DELETE | `/auth/session` | reader | 로그아웃 |
| GET | `/auth/me` | reader | 현재 로그인 사용자 |
| GET | `/dashboard` | reader | 작업 요약 |
| GET | `/sources` | reader | 수집 소스 목록 |
| GET | `/sources/{source_id}` | reader | 수집 소스 설정과 접근 상태 |
| PATCH | `/sources/{source_id}` | admin | 수집 일정 등 설정 변경 |
| POST | `/collection-runs` | operator / admin | 신규 글·최근 글 재확인 수집 작업 등록 |
| GET | `/documents` | reader | 원문 게시글 목록 |
| POST | `/documents/import` | operator / admin | 사용자가 제공한 원본 파일 가져오기 |
| GET | `/documents/{document_id}` | reader | 원문 게시글 상세 |
| GET | `/documents/{document_id}/revisions` | reader | 저장된 원문 버전 |
| GET | `/document-revisions/{document_revision_id}` | reader | 고정 원문·첨부·추출 결과 참조 |
| POST | `/analysis-runs` | operator / admin | 고정 원문 버전의 분석 작업 등록 |
| GET | `/jobs` | reader | 처리 작업 목록 |
| GET | `/jobs/{job_id}` | reader | 작업 상태와 결과 |
| POST | `/jobs/{job_id}/retry` | operator / reviewer / admin | 실패·부분 성공 작업의 재시도 등록 |
| POST | `/jobs/{job_id}/cancel` | operator / admin | 수집·분석 취소 요청 |
| GET | `/proposals` | reader | 변경안 검토 작업함 |
| POST | `/proposals` | reviewer / admin | 원문을 근거로 수동 변경안 생성 |
| GET | `/proposals/{proposal_id}` | reader | 변경안·차이·근거·검토 기록 |
| PATCH | `/proposals/{proposal_id}` | reviewer / admin | 변경안 내용 수정 |
| POST | `/proposals/{proposal_id}/validate` | reviewer / admin | 현재 규칙과 기준 데이터로 변경안 재검증 |
| POST | `/proposals/{proposal_id}/decisions` | reviewer / admin | 승인·반려·보류 |
| POST | `/proposals/{proposal_id}/withdraw-approval` | reviewer / admin | 반영 전 승인 철회 |
| GET | `/proposals/{proposal_id}/revisions` | reader | 불변 변경안 내용 이력 |
| POST | `/proposals/{proposal_id}/applications` | reviewer / admin | 승인된 revision의 반영 작업 등록 |
| GET | `/applications/{application_id}` | reader | 반영 결과와 감사 이력 ID |
| GET | `/suppliers` | reader | 공급처·제조사·브랜드 업체 검색 |
| GET | `/products` | reader | 식품 검색 |
| GET | `/products/{product_id}` | reader | 식품·규격·공급처별 상세 정보 |
| GET | `/supplier-items` | reader | 품목코드·규격으로 공급처 상품 후보 검색 |
| GET | `/prices` | reader | 확정 단가 DB를 적용일·조건별 조회 |
| GET | `/products/{product_id}/history` | reader | 생성·변경·정정의 확정 감사 이력 |
| GET | `/supplier-items/{supplier_item_id}/substitutions` | reader | 대체 관계와 구성 조회 |
| GET | `/evidence/{evidence_id}` | reader | 원문 근거와 정확한 위치 |
| GET | `/assets/{asset_id}/access` | reader | 권한 확인 후 단기 원문 접근 URL 발급 |
| GET | `/audit-events/{event_id}` | reader | 생성·변경·정정 이력 한 건 상세 |
| GET | `/analysis-profiles` | reader | 분석 프로필과 고정 프롬프트·정책 버전 |
| GET | `/analysis-runs/{analysis_run_id}` | reader | 분석 실행 입력·버전·결과·복구 가능 상태 |
| GET | `/products/{product_id}/variants` | reader | 식품 규격 페이지 조회 |
