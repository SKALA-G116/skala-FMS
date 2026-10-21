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
            tools=await c.list_tools();assert len(tools)==(6 if host else 3)
            assert not any(t.name in ['approve','apply','delete','execute_sql'] for t in tools)
            templates=await c.list_resource_templates();assert len(templates)==5
            prompts=await c.list_prompts();assert len(prompts)==3
            result=await c.read_resource('food://schemas/food-change-v1');assert result
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
