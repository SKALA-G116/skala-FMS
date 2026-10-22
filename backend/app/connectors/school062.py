"""
==============================================================================
FMS_FILE_SPEC
school062.py - 허용된 식품 사이트 수집 어댑터
==============================================================================
설명:
    - 허용된 식품 사이트 수집 어댑터
입력·출력 명세:
    - 입력: 게시판/게시글 ID·회원 연결 설정·HTTP client
    - 출력: 본문·첨부·게시 정보·접근 오류
실행 가정:
    - 허용된 HTTPS 호스트만 사용하고 로그인 실패를 데이터로 오인하지 않음
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

    2026-10-21  미지정      v0.1.0   수집 진행 표시·갱신·완료 건수 수정

    2026-10-22  김재현(Finn) v0.1.0   자료·Agent·검수 승인·식품 DB 중심 흐름 및 알레르기 표기 정리

    상세 Git 이력: git log --follow -- backend/app/connectors/school062.py
    공통 규칙: doc/file-header-policy.md

기존 모듈 설명:
    Authenticated, bounded GNUboard connector. No bypass and no arbitrary hosts.
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

from urllib.parse import urljoin,urlparse,parse_qs,urlencode,unquote
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import re,time,json,hashlib
import httpx
from bs4 import BeautifulSoup
from backend.app.infrastructure.database import Problem
HOSTS={'school062.com','www.school062.com'}
BASE='https://school062.com'
def safe_url(url):
    p=urlparse(url)
    if p.scheme!='https' or p.hostname not in HOSTS or p.port not in (None,443) or p.username:raise Problem(422,'SOURCE_URL','허용된 사이트 URL이 아닙니다.')
    return url
class SiteClient:
    def __init__(self,client=None):
        self.client=client or httpx.Client(timeout=httpx.Timeout(25,connect=10),headers={'User-Agent':'FoodLedger/0.2','Referer':BASE},follow_redirects=False);self.owns=client is None;self.last_request=0;self.progress=None
    def close(self):
        if self.owns:self.client.close()
    def request(self,url,method='GET',data=None,progress=None):
        for _ in range(5):
            safe_url(url)
            if self.owns:
                pause=0.3-(time.monotonic()-self.last_request)
                if pause>0:time.sleep(pause)
                self.last_request=time.monotonic()
            with self.client.stream(method,url,data=data) as r:
                if r.is_redirect:url=urljoin(url,r.headers['location']);method='GET';data=None;continue
                r.raise_for_status();content=bytearray();reported=0
                if progress:progress('다운로드 시작')
                declared=r.headers.get('content-length','')
                if declared.isdigit() and int(declared)>20*1024*1024:
                    raise Problem(422,'SOURCE_SIZE','원격 파일이 20MB를 초과했습니다.')
                for b in r.iter_bytes():
                    content.extend(b)
                    if len(content)>20*1024*1024:raise Problem(422,'SOURCE_SIZE','원격 파일이 20MB를 초과했습니다.')
                    if progress and time.monotonic()-reported>=1:
                        progress(f'{len(content)/1024/1024:.1f}MB 받음');reported=time.monotonic()
                return bytes(content),r.headers,str(r.url)
        raise Problem(422,'SOURCE_REDIRECT','리다이렉트가 너무 많습니다.')
    def text(self,url):return self.request(url)[0].decode('utf-8','replace')
    def authenticated(self,html):return bool(BeautifulSoup(html,'html.parser').select('a[href*="logout.php"]'))
    def login(self,cfg):
        if not cfg:return False
        for item in cfg.get('cookies',[]):
            if item.get('domain','').lstrip('.') in HOSTS:self.client.cookies.set(item['name'],item['value'],domain=item['domain'],path=item.get('path','/'))
        if self.authenticated(self.text(BASE+'/')):return True
        page=BeautifulSoup(self.text(BASE+'/bbs/login.php'),'html.parser');form=page.select_one('form:has(input[name="mb_id"])')
        if not form:raise Problem(422,'LOGIN_FORM_CHANGED','사이트 로그인 양식이 바뀌었습니다.')
        action=safe_url(urljoin(BASE+'/bbs/login.php',form.get('action','')))
        fields={e['name']:e.get('value','') for e in form.select('input[type="hidden"][name]')}
        fields.update(mb_id=cfg['username'],mb_password=cfg['password'],url=BASE)
        if cfg.get('auto_login',True):fields['auto_login']='on'
        self.request(action,'POST',fields)
        if not self.authenticated(self.text(BASE+'/')):raise Problem(401,'SOURCE_LOGIN_FAILED','사이트 로그인에 실패했습니다. 회원 정보·계정 상태·추가 인증 여부를 확인하세요.')
        return True
    def cookies(self):return [{'name':c.name,'value':c.value,'domain':c.domain,'path':c.path,'secure':c.secure} for c in self.client.cookies.jar if c.domain.lstrip('.') in HOSTS]
    def list_posts(self,board,page=1):
        html=self.text(BASE+'/bbs/board.php?'+urlencode({'bo_table':board,'page':page}));soup=BeautifulSoup(html,'html.parser');seen=set();posts=[]
        for a in soup.select('#bo_list a[href],.tbl_head01 a[href]'):
            q=parse_qs(urlparse(urljoin(BASE,a['href'])).query)
            if q.get('bo_table')==[board] and q.get('wr_id') and q['wr_id'][0].isdigit():
                id=q['wr_id'][0]
                if id not in seen:seen.add(id);posts.append(id)
        if not posts and page==1 and not soup.select('#bo_list'):raise Problem(422,'BOARD_LAYOUT_CHANGED','게시판 목록을 확인할 수 없습니다.')
        return posts
    def post(self,board,post):
        url=BASE+'/bbs/board.php?'+urlencode({'bo_table':board,'wr_id':post});soup=BeautifulSoup(self.text(url),'html.parser');body=soup.select_one('#bo_v_con');title=soup.select_one('#bo_v_title')
        if not body:raise Problem(422,'POST_UNAVAILABLE','게시글이 삭제되었거나 접근 권한이 없습니다.')
        for el in body(['script','style','iframe']):el.decompose()
        title=title.get_text(' ',strip=True) if title else f'{board}-{post}';text=body.get_text('\n',strip=True);author=soup.select_one('#bo_v_info .sv_member');date=soup.select_one('#bo_v_info .if_date');published=None
        if date:
            m=re.search(r'(\d{2,4}-\d{2}-\d{2}\s+\d{2}:\d{2})',date.get_text(' ',strip=True))
            if m:
                value=m[1];fmt='%y-%m-%d %H:%M' if len(value.split('-')[0])==2 else '%Y-%m-%d %H:%M'
                published=datetime.strptime(value,fmt).replace(tzinfo=ZoneInfo('Asia/Seoul')).isoformat()
        links=[]
        for image in body.select('img[src]'):links.append((urljoin(url,image['src']),Path(urlparse(image['src']).path).name,'image'))
        for a in soup.select('#bo_v_file a[href]'):
            if 'download.php' in a['href']:
                name=(a.select_one('strong') or a).get_text(' ',strip=True);match=re.search(r'([^/\\]+\.(?:xlsx?|pdf|png|jpe?g|webp|gif|hwp|hwpx))',name,re.I)
                links.append((urljoin(url,a['href']),match[1] if match else name[:120],'attachment'))
        assets=[];issues=[];seen=set();total=0
        for index,(link,name,kind) in enumerate(links,1):
            if link in seen:continue
            seen.add(link)
            if len(seen)>20:issues.append({'code':'ATTACHMENT_LIMIT','message':'첨부가 20개를 초과했습니다.'});break
            try:
                def download_progress(detail):
                    if self.progress:self.progress(f'첨부 {index}/{min(len(links),20)} · {name[:60]} · {detail}')
                content,headers,final=self.request(link,progress=download_progress);mime=headers.get('content-type','').split(';')[0]
                if mime=='text/html' or content.lstrip().startswith((b'<!doctype',b'<html',b'<script')):
                    raise Problem(401,'SOURCE_LOGIN_REQUIRED','첨부를 받으려면 사이트 로그인 또는 해당 파일 접근 권한이 필요합니다.')
                total+=len(content)
                if total>60*1024*1024:raise Problem(422,'DOCUMENT_SIZE','게시글 첨부 합계가 60MB를 초과했습니다.')
                cd=headers.get('content-disposition','');fn=re.search(r"filename\*=UTF-8''([^;]+)",cd,re.I) or re.search(r'filename="?([^";]+)',cd,re.I)
                if fn:name=unquote(fn[1]).strip()
                name=Path(name).name
                if not Path(name).suffix:
                    name='attachment'+{'image/png':'.png','image/jpeg':'.jpg','application/pdf':'.pdf','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet':'.xlsx'}.get(mime,'.bin')
                assets.append({'filename':name,'content':content,'source_url':link,'kind':kind,'content_type':mime})
            except (Problem,httpx.HTTPError) as ex:
                if isinstance(ex,Problem) and ex.code in ('CANCELLED','LEASE_LOST'):raise
                issues.append({'code':ex.code if isinstance(ex,Problem) else 'ATTACHMENT_FAILED','message':ex.message if isinstance(ex,Problem) else '첨부 다운로드에 실패했습니다.','url':link,'filename':name})
        return {'url':url,'board':board,'post':post,'title':title,'body':text,'author':author.get_text(' ',strip=True) if author else None,'published_at':published,'assets':assets,'issues':issues}
