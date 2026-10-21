"""
==============================================================================
FMS_FILE_SPEC
mcp_server.py - 식품 도메인 MCP stdio 제공
==============================================================================
설명:
    - 식품 도메인 MCP stdio 제공
입력·출력 명세:
    - 입력: Tool 인자·Resource URI·Prompt 이름·선택 host 모드
    - 출력: 제한된 조회/초안 Tool 결과·정책/근거·작업 안내
실행 가정:
    - 기본 서버에 승인·최종 반영·임의 SQL을 노출하지 않음
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

    상세 Git 이력: git log --follow -- mcp_server.py
    공통 규칙: doc/file-header-policy.md

기존 모듈 설명:
    Food-domain MCP stdio entry point; --host exposes trusted host tools only.
==============================================================================
"""

# FMS_MODULE_METADATA_BEGIN
__author__ = "미지정"
__email__ = "미지정"
__version__ = "0.1.0"
__status__ = "Development"
# FMS_MODULE_METADATA_END

# ---------------------------------------------------------------------------
# 1. Imports / Module implementation
# ---------------------------------------------------------------------------

from backend.app.infrastructure.database import init, pool
from backend.app.mcp.server import mcp

if __name__ == '__main__':
    init()
    try:
        mcp.run(transport='stdio', show_banner=False)
    finally:
        pool.close()
