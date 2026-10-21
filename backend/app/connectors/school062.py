"""Authenticated, bounded GNUboard connector. No bypass and no arbitrary hosts."""
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
        self.client=client or httpx.Client(timeout=httpx.Timeout(25,connect=10),headers={'User-Agent':'FoodLedger/0.2','Referer':BASE},follow_redirects=False);self.owns=client is None;self.last_request=0
    def close(self):
        if self.owns:self.client.close()
    def request(self,url,method='GET',data=None):
        for _ in range(5):
            safe_url(url)
            if self.owns:
                pause=0.3-(time.monotonic()-self.last_request)
                if pause>0:time.sleep(pause)
                self.last_request=time.monotonic()
            with self.client.stream(method,url,data=data) as r:
                if r.is_redirect:url=urljoin(url,r.headers['location']);method='GET';data=None;continue
                r.raise_for_status();content=bytearray()
                for b in r.iter_bytes():
                    content.extend(b)
                    if len(content)>20*1024*1024:raise Problem(422,'SOURCE_SIZE','원격 파일이 20MB를 초과했습니다.')
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
        for link,name,kind in links:
            if link in seen:continue
            seen.add(link)
            if len(seen)>20:issues.append({'code':'ATTACHMENT_LIMIT','message':'첨부가 20개를 초과했습니다.'});break
            try:
                content,headers,final=self.request(link);mime=headers.get('content-type','').split(';')[0]
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
            except (Problem,httpx.HTTPError) as ex:issues.append({'code':ex.code if isinstance(ex,Problem) else 'ATTACHMENT_FAILED','message':ex.message if isinstance(ex,Problem) else '첨부 다운로드에 실패했습니다.','url':link})
        return {'url':url,'board':board,'post':post,'title':title,'body':text,'author':author.get_text(' ',strip=True) if author else None,'published_at':published,'assets':assets,'issues':issues}
