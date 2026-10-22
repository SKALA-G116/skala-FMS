<!--
==============================================================================
FMS_FILE_SPEC
02-ocr-lifecycle.md - 프로젝트 문서 02-ocr-lifecycle
==============================================================================
설명:
    - 프로젝트 문서 02-ocr-lifecycle
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

    상세 Git 이력: git log --follow -- doc/submission/before-after/02-ocr-lifecycle.md
    공통 규칙: doc/file-header-policy.md
==============================================================================
-->
# 02. Python OCR 프로세스가 종료되는 문제

## Before: 사용자 환경에서 확인한 현상

macOS crash report는 별도 Python3.11 OCR 자식의 `libpaddle.so` native thread pool·FailureSignalHandler를 포함한 SIGSEGV를 기록했습니다. 부모 Agent worker와 API는 실행 중이었습니다. 이 보고서로 OOM이나 모든 Python 프로세스의 종료를 단정할 수는 없습니다.

기존 수명 관리는 유휴 종료에도 즉시 SIGTERM을 보냈습니다. 종료 신호와 native 정리 과정의 충돌 가능성을 점검했으나 Paddle 내부의 최초 결함은 확정하지 않았습니다.

## After: 오류를 숨기는 대신 종료·복구 경계를 분리

- 정상 유휴 종료에는 JSON shutdown을 먼저 요청하고, 제한 시간 후에만 TERM/KILL로 진행합니다.
- 전용 OCR 자식은 정상 응답을 마친 뒤 flush와 `os._exit(0)`으로 interpreter teardown을 피합니다. API·Agent 부모에는 적용하지 않습니다.
- Paddle signal handler 비활성화, CPU threads 2, MKLDNN 비활성화로 환경을 명시합니다.
- 예기치 않은 종료는 `OCR_PROCESS_EXIT`와 exit code로 보고합니다. 다음 요청은 새 자식으로 처리하며 무한 재시도는 하지 않습니다.

## 검증 결과

실제 PaddleOCR3.7.0/PaddlePaddle3.3.1과 합성 이미지에서 각각 “같은 PID로 인식 2회 → expire_idle”을 실행했습니다.

| 관찰 | 사이클 1 | 사이클 2 |
|---|---:|---:|
| 인식 결과 행 | 1 | 1 |
| 프로세스 재사용 | 확인 | 확인 |
| 종료 코드 | 0 | 0 |
| 관찰 시간 | 3.06초 | 2.04초 |

이 시간은 두 차례 관찰값이며 Before/After 속도 개선 비교가 아닙니다. 로컬 원자료는 `.local/ocr-stability-check.json`이고, 공개 가능한 관찰 요약은 위 표와 [상세 대응 기록](../../food-agent/ocr-stability.md)에 있습니다. 원본 crash report의 개인 경로는 저장소에 복사하지 않습니다.

코드: `backend/app/parsers/ocr.py`, `ocr_pool.py`. 테스트: `test_async_runtime.py`의 `test_ocr_idle_close_uses_shutdown_protocol_without_sigterm`, `test_ocr_unexpected_exit_is_distinct_and_next_request_can_recover`, `test_ocr_engine_owns_signal_handling_and_limits_cpu_threads`.

장시간·다양한 이미지에서 충돌이 사라졌다는 보장은 아닙니다. 재발하면 추론 중 충돌인지 종료 중 충돌인지부터 새 report와 exit code로 구분합니다.

발표 문장: “Python 전체가 아니라 OCR 자식이 충돌했습니다. 정상 종료와 비정상 종료를 분리하고, 실제 인식·유휴 종료를 두 차례 확인했습니다.”

[사례 목록](../before-after.md) · [README](../../../README.md)
