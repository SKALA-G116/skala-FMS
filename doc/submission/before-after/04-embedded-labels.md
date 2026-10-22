<!--
==============================================================================
FMS_FILE_SPEC
04-embedded-labels.md - 프로젝트 문서 04-embedded-labels
==============================================================================
설명:
    - 프로젝트 문서 04-embedded-labels
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

    상세 Git 이력: git log --follow -- doc/submission/before-after/04-embedded-labels.md
    공통 규칙: doc/file-header-policy.md
==============================================================================
-->
# 04. 표의 셀은 읽었지만 라벨 이미지의 핵심 정보가 빠진 문제

## Before

XLSX 파서가 셀 값만 읽었습니다. 단가표 오른쪽에 삽입한 라벨 이미지의 원재료·알레르기는 텍스트 셀에 없으므로 DTO를 채울 수 없었습니다. 사용자가 제공한 맘스케익 단가표 화면이 이 요구를 보여 주었습니다.

## After

XLSX drawing 관계의 내부 이미지를 읽고 시트·행 anchor를 보존합니다. 이미지별 OCR를 수행한 후 Agent가 `extract_image_regions`를 선택하면 해당 행의 표 정보와 함께 의미를 추출합니다. 표의 상품명·규격·가격은 유지하고 원재료·알레르기 등 빈 속성을 보완합니다. 명확한 상품 행이 이미 있으면 영역 분류 LLM을 다시 호출하지 않습니다.

표와 이미지 근거는 같은 검토 품목에 연결되며 원본 라벨을 인증된 미리보기로 대조할 수 있습니다. 여러 행에 걸쳐 연결이 모호하면 한 상품에 임의로 붙이지 않습니다. 파일당 앞의40개 이미지만 순차 OCR하고, 초과분·실패분은 원문 확인으로 남깁니다. 표 행은 초과 때문에 버리지 않습니다.

## 검증 범위

| 테스트 | 확인한 내용 |
|---|---|
| `test_xlsx_embedded_images_keep_separate_anchors_and_ocr_sources` | 두 이미지의 행·근거 구분, OCR 미설정 시 표 보존 |
| `test_agent_enriches_table_row_from_embedded_label_and_previews_parent_asset` | 원래 상품명·50g 유지, 우유 원재료·함유 정보 보완, 검토 품목1개, 근거2개, 잘못된 서명 차단 |
| `test_xlsx_image_budget_preserves_table_rows` | 이미지41개 중40개 처리·1개 확인 필요, 표 행 보존 |

합성 XLSX와 모의 OCR/LLM으로 파이프라인을 검증했습니다. 사용자 제공 캡처의 실제 라벨 인식 성공률을 측정한 것이 아니므로 이를 Before/After 정확도 수치로 제시하지 않습니다. 구형 XLS 그림·외부 연결 이미지·SVG·WMF·텍스트 PDF 내부 그림은 이 추가 기능의 범위가 아닙니다.

코드: `parsers/xlsx_images.py`, `parsers/documents.py`, `analysis/planning.py`, `analysis/agent.py`, `SourceComparison.vue`. [상세 지원 범위](../../food-agent/embedded-table-images.md)

발표 문장: “표 안에도 라벨 이미지가 있었습니다. 셀 파싱과 OCR를 상품 행 기준으로 합쳐, 이미지의 정보를 같은 DTO와 검수 화면으로 전달하도록 바꿨습니다.”

[사례 목록](../before-after.md) · [README](../../../README.md)
