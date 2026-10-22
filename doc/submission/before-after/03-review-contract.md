<!--
==============================================================================
FMS_FILE_SPEC
03-review-contract.md - 프로젝트 문서 03-review-contract
==============================================================================
설명:
    - 프로젝트 문서 03-review-contract
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

    상세 Git 이력: git log --follow -- doc/submission/before-after/03-review-contract.md
    공통 규칙: doc/file-header-policy.md
==============================================================================
-->
# 03. 추출·검토가 됐는데 최종 승인이 실패한 문제

## Before

상품 한 개에 표·OCR 근거 22~23개가 연결됐지만 승인 계약의 `FieldEvidence.evidence_ids`는 최대20개였습니다. 통합 과정은 근거를 보존했으나 승인 API가 거절했습니다. JSON Schema 오류에 UUID 배열 전체가 포함되고 화면에서 중복 출력되어 사용자가 원인을 알아보기 어려웠습니다.

## After

| 수정 | 이유 |
|---|---|
| 생성·승인 JSON Schema 상한을 2,000으로 통일 | 분석 구간의 유한한 상한에 맞추며 근거를 임의 삭제하지 않음 |
| UUID·중복·문서 소속·필드 경로 검증 유지 | 상한 확대가 승인 검증 해제를 뜻하지 않도록 함 |
| 같은 근거 조회 캐시 | 여러 필드가 같은 evidence를 참조할 때 중복 DB 읽기 감소 |
| 짧은 오류 경로·안내, 화면 중복 제거 | 원본 UUID 덤프 대신 사용자가 처리할 수 있는 실패 사유 표시 |

## 검증

격리 DB에서 **근거 41개 → 품목 확인 → 승인 → apply → 감사 이력의 41개 보존**을 검증했습니다. 2,000개 허용·2,001개 차단·잘못된 UUID·중복 근거 차단도 검사했습니다. 실제 사용자 자료를 대신 승인하지 않았으며 첨부 오류의 과거 검토본은 현재 DB에 없어 그 건의 운영 재승인 성공을 주장하지 않습니다.

코드: `infrastructure/contracts.py`, `review/proposals.py`, `frontend/src/utils/reviewJourney.js`, 두 JSON Schema. 테스트: `test_workflow.py::test_review_approval_preserves_more_than_twenty_source_references`, `frontend/tests/reviewJourney.test.js`.

성능 측정은 별도로 하지 않았습니다. 캐시는 중복 조회 경로를 줄이는 수정이며 지연시간 감소율을 측정한 결과가 아닙니다. [상세 계약 수정](../../food-agent/review-evidence-contract.md)

발표 문장: “추출 결과가 많아진 뒤 승인 계약의 옛 20개 제한이 발목을 잡았습니다. 근거를 자르지 않고 계약을 맞추고, 실제 반영 후 이력까지 보존되는지 테스트했습니다.”

[사례 목록](../before-after.md) · [README](../../../README.md)
