<!--
==============================================================================
FMS_FILE_SPEC
ocr-stability.md - 프로젝트 문서 ocr-stability
==============================================================================
설명:
    - 프로젝트 문서 ocr-stability
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

    상세 Git 이력: git log --follow -- doc/food-agent/ocr-stability.md
    공통 규칙: doc/file-header-policy.md
==============================================================================
-->
# OCR 자식 프로세스 충돌 대응 · 2026-10-22

## 확인한 현상

사용자 제공 macOS 보고서는 Python3.11 OCR 자식에서 `libpaddle.so`의 네이티브 thread pool과 `FailureSignalHandler`를 포함한 SIGSEGV를 기록했다. 메인 스레드는 입력 대기 상태였고 부모인 Python3.14 Agent 작업자와 API는 실행 중이었다. 이 보고서는 시스템 메모리 부족 종료를 입증하지 않는다.

기존 코드는 60초 유휴·요청 수 상한·작업자 종료에서 OCR 자식에 즉시 SIGTERM을 보냈다. 종료 경로와 네이티브 신호 처리/정리의 충돌이 가능한 원인이다. 보고서만으로 Paddle 내부의 최초 결함 위치나 메모리 원인을 확정하지 않는다.

## 적용 내용

- OCR subprocess의 유휴·정상 종료는 JSON shutdown 요청을 먼저 보내고 최대2초 기다린다. 정지하지 않는 경우에만 SIGTERM, 이후 SIGKILL로 제한한다.
- Paddle 초기화 시 `disable_signal_handler()`를 사용해 subprocess의 중단 정책을 부모가 관리하게 한다. 실제 메모리 접근 오류 자체를 해결하는 API는 아니다.
- CPU inference threads를2로 명시하고 MKLDNN을 끈다. 환경 변수만으로 추론 스레드 수를 제한했다고 가정하지 않는다.
- 전용 OCR serve 프로세스가 정상 shutdown/EOF를 받으면 stdout/stderr를 flush한 뒤 `os._exit(0)`으로 종료한다. 작업을 마친 폐기 가능한 모델 프로세스에서만 사용해 native thread pool의 Python interpreter teardown을 피한다. API나 Agent 부모에는 적용하지 않는다.
- timeout에는 정상 종료 응답을 기다리는 추가 단계를 생략하고 강제 종료 경로를 사용한다.
- 예기치 않은 종료는 `OCR_PROCESS_EXIT`와 exit code로 구별한다. 다음 요청은 새 자식으로 처리한다. 무한 자동 재시도는 하지 않는다.

## 검증

- 백엔드 전체145개 테스트 통과. 정상 shutdown 시 SIGTERM 미발송·exit0, timeout 정리, 비정상 exit code 식별과 다음 요청 복구, CPU/handler 설정 검증을 포함한다.
- 실제 설치된 PaddleOCR3.7.0/PaddlePaddle3.3.1 환경에서 합성 이미지로 두 차례 `인식 2회(같은 PID 재사용) + expire_idle`를 실행했다. 두 사이클 모두 결과1행과 정상 종료0을 확인했다.
- 검증에서 기존 식품 DB를 수정하지 않았다. 현재 대기 중인 분석은 정상 종료 경계에서 queued로 돌아간 뒤 새 작업자로 재개했다.

검증은 종료 경로 회귀와 짧은 실제 실행이다. 모든 이미지·장시간 운전에서 native 충돌이 없음을 보장하지 않으며, 같은 증상이 재발하면 새 crash report와 종료 코드로 추론 중 충돌인지 정상 종료 중 충돌인지 구분한다.

공식 코드: [Paddle 신호 처리 API](https://github.com/PaddlePaddle/Paddle/blob/develop/python/paddle/__init__.py), [PaddleOCR CPU 공통 설정](https://github.com/PaddlePaddle/PaddleOCR/blob/main/paddleocr/_common_args.py).
