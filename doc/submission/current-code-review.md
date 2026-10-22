<!--
==============================================================================
FMS_FILE_SPEC
current-code-review.md - 프로젝트 문서 current-code-review
==============================================================================
설명:
    - 프로젝트 문서 current-code-review
입력·출력 명세:
    - 입력: 설계·구현·측정·검증 근거
    - 출력: 설명·명세·예제·검증 또는 발표 안내
실행 가정:
    - 계획·테스트 대역·실제 실행 결과를 구분하고 현재 상태는 README 및 검증 근거 확인
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

    상세 Git 이력: git log --follow -- doc/submission/current-code-review.md
    공통 규칙: doc/file-header-policy.md
==============================================================================
-->
# 현재 코드와 발표 자료 대조 · 2026-10-22

기준: `main` 커밋 `402f0c7dca19320d91c4c33dd3e8fcdbb012c452`(PR #13 병합). 이 문서 갱신에서는 서비스 로직을 변경하지 않았습니다.

| 기능 | 현재 코드 확인 위치 | 발표에서 설명할 범위 |
|---|---|---|
| 자료별 도구 선택 | [planning.py](../../backend/app/domains/analysis/planning.py) | 읽힌 열·본문·OCR 근거로 네 도구 중 선택, 선택 결과 검증 |
| 도구 실행·DTO 통합 | [agent.py](../../backend/app/domains/analysis/agent.py) | 표 정리·텍스트·이미지 추출·수동 검수 요청 분기 |
| LangGraph | [workflow.py](../../backend/app/domains/analysis/workflow.py) | Agent 모드의 extract→plan→execute_tools→match(선택)→export |
| 검수함·통합 표 | [업무 흐름 명세](../food-agent/review-material-flow.md) | 분석 전 자료 표시, 원본 행과 통합 DTO 및 검수 링크 연결 |
| 승인·반영 | [도구와 그래프 상세](../food-agent/agent-tools-langgraph.md) | 그래프의 초안 생성 후 CMS 승인 절차로 확정 DB 반영 |

네 도구는 execute_tools 내부에서 실행합니다. 도구마다 별도 LangGraph나 Multi-Agent를 만든 구조는 아닙니다. OCR은 도구 계획 전 extract에서 준비하며, MCP stdio 서버는 별도 진입점입니다. CMS worker는 도메인 서비스를 직접 호출합니다. 사람 승인은 LangGraph interrupt가 아니라 별도 API/작업 절차입니다. 규칙 모드의 propose 경로와 실제 Agent 모드를 구분합니다.

## 현재 화면과 집계

[조회 기록 JSON](current-code-evidence.json)은 2026-10-22 13:24 KST의 읽기 전용 집계입니다. 캡처는 같은 작업 중 현재 서비스에서 저장했습니다. 저장된 분석은 그보다 먼저 실행된 결과이며 현재 기준 커밋에서 새로 추론한 벤치마크가 아닙니다.

| 현재 캡처 | 확인한 내용 |
|---|---|
| [검수함](screenshots/current/01-review-inbox.png) | 분석 전·진행 중 자료 포함5건 |
| [통합 표](screenshots/current/02-table-dto.png) | 원본 행에 DTO·알레르기·검수 경로 연결 |
| [라벨 검수](screenshots/current/03-label-review.png) | 생크림 오믈렛 라벨·OCR 위치와 규격 대조 |
| [도구 실행](screenshots/current/04-agent-tools.png) | 표 정리·이미지 추출·원문 확인 요청 이유 |

맘스케익 run `edaa7032-b1ca-40a9-a564-69231edc018e`: 후보13개, 확인0·제외1·대기12, 원문 확인13구간, 모델 호출20회, 통합 DTO 연결13행, 알레르기 목록 채움9행입니다. 이 수치는 정확도를 뜻하지 않습니다. `()`·발주 안내 문장을 상품으로 인식한 후보와 보관 방법이 알레르기 원문에 들어간 사례가 남아 있습니다. 원재료 정보도 공란이 있어 완전 추출로 소개하지 않습니다.

## 검증과 보존 범위

- 현재 코드 백엔드165개 테스트 통과: 운영 DB와 분리한 food_fms_refactor_test DB·규칙 모드.
- 프론트엔드16개 테스트 및 Vite 배포 빌드 통과.
- 자료를 촬영하기 위한 신규 수집·모델 추론·품목 수정·승인은 수행하지 않음.
- 과거18행·6.027초와 단일 planner 호출은 [기존 실행 JSON](table-demo-result.json)에 보존. 현재 대표 결과에서 제외.
- [Before/After](before-after.md)는 수정 당시의 입력·코드·검증 조건을 유지. 현재 사례와 성능 비교하지 않음.

다음 검증은 업체별 정답셋의 필드 정확도·누락률, 안내 문장 제거, 알레르기 근거 검증, 반복 실행의 전체 지연시간과 메모리 측정입니다.
