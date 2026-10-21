# skala-FMS · 식품장부

학교급식 게시글·이미지·첨부 단가표를 표준 식품 정보로 정리하고, 원문 대조와 승인 후 식품·단가·이력을 관리하는 AI 서비스입니다.

**Vue 3 · FastAPI · LangGraph · MCP · Ollama · PostgreSQL/JSONB**

- [프로젝트 명세·실행 방법·검증 결과 — readmd.md](readmd.md)
- [초기 도메인 리팩토링 내역](doc/food-agent/initial-refactor.md)
- [상세 설계·API 계약](doc/food-agent/README.md)
- [기존 ZIP 코드 보존 위치](legacy/README.md)

백엔드는 `backend/app/domains/` 아래 인증, 수집자료, 식품, 단가, 분석, 검토승인, 작업, 대시보드 조회로 분리했습니다. 실제 계정·수집 자료·모델 가중치·DB 파일은 저장소에 포함하지 않습니다.
