"""
==============================================================================
FMS_FILE_SPEC
test_parsers_mcp.py - 기능·경계·회귀 검증
==============================================================================
설명:
    - 기능·경계·회귀 검증
입력·출력 명세:
    - 입력: 테스트 fixture·가상 입력·명시적 mock/테스트 대역
    - 출력: assert 결과와 실패 사유
실행 가정:
    - DB 통합 테스트는 별도 _test DB·임시 assets 사용; 대역과 실제 모델 검증을 구분
작성 정보:
    - 작성자: 김재현(Finn)
    - 이메일: penguin.klg@gmail.com
    - 작성일: 2026-10-21 (최초 Git 등록일 기준)
    - 라이선스: 미지정
    - 버전: 0.1.0
    - 상태: Development
변경 이력 (Revision History):
    DATE        AUTHOR      VERSION  DESCRIPTION
    --------------------------------------------------------------------
    2026-10-21  미지정      v0.1.0   최초 Git 등록 a11ef05a
    2026-10-21  미지정      v0.1.0   파일 역할·입출력·가정·이력 명세 추가

    2026-10-21  미지정      v0.1.0   첨부 진행·취소와 완료 건수 회귀 검증 추가

    2026-10-21  김재현(Finn) v0.1.0   Agent 도구 선택 기반 리빌드·업무 경계 및 검증

    상세 Git 이력: git log --follow -- backend/tests/test_parsers_mcp.py
    공통 규칙: doc/file-header-policy.md
==============================================================================
"""

# FMS_MODULE_METADATA_BEGIN
__author__ = "김재현(Finn)"
__email__ = "penguin.klg@gmail.com"
__version__ = "0.1.0"
__status__ = "Development"
# FMS_MODULE_METADATA_END

# ---------------------------------------------------------------------------
# 1. Imports / Module implementation
# ---------------------------------------------------------------------------
import asyncio,os,sys
from pathlib import Path
import pytest
from backend.app.parsers.documents import parse
from backend.app.infrastructure.database import Problem; from backend.app.infrastructure.database import ROOT

def test_excel_cell_provenance(tmp_path):
    import openpyxl
    p=tmp_path/'table.xlsx';wb=openpyxl.Workbook();ws=wb.active;ws.title='단가표';ws.append(['품목','가격']);ws.append(['두부',15000]);wb.save(p)
    result=parse(p,p.name);assert result[1]['text']=='두부 | 15000';assert result[1]['locator']['cell_range']=='A2:B2';assert result[1]['locator']['sheet_name']=='단가표'

def test_html_strips_script_and_image_limits(tmp_path):
    p=tmp_path/'a.html';p.write_text('<div id="bo_v_con">공급 공지<script>malicious()</script></div>');assert parse(p,p.name)[0]['text']=='공급 공지'
    from PIL import Image
    p=tmp_path/'huge.png';Image.new('L',(4001,4000)).save(p)
    with pytest.raises(Problem) as e:parse(p,p.name)
    assert e.value.code=='PIXEL_LIMIT'

def test_stdio_mcp_capability_boundary():
    from fastmcp import Client
    from fastmcp.client.transports import StdioTransport
    async def run(host):
        transport=StdioTransport(command=sys.executable,args=['-m','backend.app.mcp.server']+(['--host'] if host else []),cwd=str(ROOT),env=dict(os.environ))
        async with Client(transport) as c:
            tools=await c.list_tools();assert len(tools)==(7 if host else 4)
            assert not any(t.name in ['approve','apply','delete','execute_sql'] for t in tools)
            templates=await c.list_resource_templates();assert len(templates)==5
            prompts=await c.list_prompts();assert len(prompts)==3
            result=await c.read_resource('food://schemas/food-change-v1');assert result
            assert await c.read_resource('food://agent/tools')
            found=await c.call_tool('find_product_candidates',{'query':'두부','limit':2});assert not found.is_error
    asyncio.run(run(False));asyncio.run(run(True))

def test_site_login_and_attachment_access_boundary():
    import httpx
    from urllib.parse import parse_qs
    from backend.app.connectors.school062 import SiteClient
    logged=False
    def handle(req):
        nonlocal logged
        if req.url.path=='/bbs/login.php':return httpx.Response(200,text='<form action="/bbs/login_check.php"><input name="mb_id"></form>')
        if req.url.path=='/bbs/login_check.php':
            form=parse_qs(req.content.decode());assert form['mb_id']==['member'];assert form['auto_login']==['on'];logged=True;return httpx.Response(302,headers={'location':'https://school062.com/'})
        if req.url.path=='/':return httpx.Response(200,text='<a href="/bbs/logout.php">로그아웃</a>' if logged else '로그인')
        if req.url.path=='/bbs/download.php':return httpx.Response(200,text='<script>alert("로그인 필요");</script>',headers={'content-type':'text/html'})
        return httpx.Response(200,text='<h2 id="bo_v_title">공급 공지</h2><div id="bo_v_con">내용</div><div id="bo_v_file"><a href="/bbs/download.php?no=0"><strong>단가.xlsx</strong></a></div>')
    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        site=SiteClient(client);assert site.login({'username':'member','password':'secret','auto_login':True})
        p=site.post('product_01','1');assert p['issues'][0]['code']=='SOURCE_LOGIN_REQUIRED';assert not p['assets']
    from backend.app.connectors.school062 import safe_url
    for url in ['http://school062.com','https://evil.example/','https://school062.com:123/a']:
        with pytest.raises(Problem):safe_url(url)


def test_attachment_progress_and_cancellation_are_not_swallowed():
    import httpx
    from backend.app.connectors.school062 import SiteClient
    def handle(req):
        if req.url.path == '/asset.png':
            return httpx.Response(200,content=b'image bytes',headers={'content-type':'image/png'})
        return httpx.Response(200,text='<h2 id="bo_v_title">공지</h2><div id="bo_v_con"><img src="/asset.png"></div>')
    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        site=SiteClient(client);messages=[];site.progress=messages.append
        post=site.post('product_01','27747')
        assert len(post['assets'])==1
        assert any('첨부 1/1' in message and '다운로드 시작' in message for message in messages)
        assert any('MB 받음' in message for message in messages)
        def cancelled(message):raise Problem(409,'CANCELLED','취소된 작업입니다.')
        site.progress=cancelled
        with pytest.raises(Problem) as error:site.post('product_01','27747')
        assert error.value.code=='CANCELLED'


def test_oversized_attachment_is_rejected_before_reading_body():
    import httpx
    from backend.app.connectors.school062 import SiteClient
    class UnreadBody(httpx.SyncByteStream):
        def __iter__(self):raise AssertionError('oversized response body must not be read')
    with httpx.Client(transport=httpx.MockTransport(lambda req:httpx.Response(200,headers={'content-length':str(21*1024*1024)},stream=UnreadBody()))) as client:
        with pytest.raises(Problem) as error:SiteClient(client).request('https://school062.com/large.xlsx')
        assert error.value.code=='SOURCE_SIZE'
