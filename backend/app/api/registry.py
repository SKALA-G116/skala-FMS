"""
==============================================================================
FMS_FILE_SPEC
registry.py - 프로젝트 설정 registry.py
==============================================================================
설명:
    - 프로젝트 설정 registry.py
입력·출력 명세:
    - 입력: 도구별 설정·실행 환경
    - 출력: 해당 도구의 구성 또는 실행 결과
실행 가정:
    - 실제 비밀값과 로컬 실행 데이터는 Git에서 제외
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

    2026-10-21  미지정      v0.1.0   자료별 검수함 조회 경로 등록

    상세 Git 이력: git log --follow -- backend/app/api/registry.py
    공통 규칙: doc/file-header-policy.md

기존 모듈 설명:
    Explicit domain ownership: no request writes outside the shared transaction.
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

from backend.app.domains.identity import api as identity
from backend.app.domains.ingestion import api as ingestion
from backend.app.domains.pricing import api as pricing
from backend.app.domains.catalog import api as catalog
from backend.app.domains.analysis import api as analysis
from backend.app.domains.jobs import api as jobs
from backend.app.domains.review import api as review
from backend.app.domains.reporting import api as reporting

DOMAINS = (identity, ingestion, pricing, catalog, analysis, jobs, review, reporting,)

HANDLERS = {
    'auth': identity.handle,
    'document-selections': ingestion.handle,
    'document-actions': ingestion.handle,
    'price-workbooks': pricing.handle,
    'price-sheets': pricing.handle,
    'dashboard': reporting.handle,
    'sources': ingestion.handle,
    'collection-runs': ingestion.handle,
    'documents': ingestion.handle,
    'document-revisions': ingestion.handle,
    'analysis-profiles': analysis.handle,
    'analysis-runs': analysis.handle,
    'jobs': jobs.handle,
    'proposals': review.handle,
    'review-inbox': review.handle,
    'applications': review.handle,
    'suppliers': catalog.handle,
    'foods': catalog.handle,
    'products': catalog.handle,
    'supplier-items': catalog.handle,
    'prices': pricing.handle,
    'evidence': ingestion.handle,
    'audit-events': review.handle,
    'assets': ingestion.handle,
}

def handler_for(root):
    return HANDLERS[root]
