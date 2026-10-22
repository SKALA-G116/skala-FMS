"""
==============================================================================
FMS_FILE_SPEC
xlsx_images.py - XLSX 삽입 이미지·셀 anchor 추출
==============================================================================
설명:
    - XLSX 삽입 이미지·셀 anchor 추출
입력·출력 명세:
    - 입력: XLSX 경로·삽입 이미지 번호
    - 출력: 시트·행 범위·미디어 목록 또는 크기를 제한한 이미지 bytes
실행 가정:
    - 외부 관계를 읽지 않고 ZIP·미디어 크기·픽셀·이미지 수를 제한
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

    상세 Git 이력: git log --follow -- backend/app/parsers/xlsx_images.py
    공통 규칙: doc/file-header-policy.md

기존 모듈 설명:
    Bounded XLSX drawing inventory with explicit cell anchors and safe media reads.
==============================================================================
"""

# FMS_MODULE_METADATA_BEGIN
__author__ = '김재현(Finn)'
__email__ = 'penguin.klg@gmail.com'
__version__ = "0.1.0"
__status__ = "Development"
# FMS_MODULE_METADATA_END

# ---------------------------------------------------------------------------
# 1. Imports / Module implementation
# ---------------------------------------------------------------------------

import posixpath
import zipfile
from xml.etree import ElementTree as ET
from pathlib import Path
from PIL import Image
from io import BytesIO
from backend.app.infrastructure.database import Problem
from backend.app.runtime.limits import MAX_FILE_BYTES

M='{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
D='{http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing}'
A='{http://schemas.openxmlformats.org/drawingml/2006/main}'
R='{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'

def target(base,value):
    name=posixpath.normpath(value.lstrip('/') if value.startswith('/') else posixpath.join(posixpath.dirname(base),value))
    if not name.startswith('xl/'):raise Problem(422,'XLSX_IMAGE_PATH','엑셀 이미지 경로가 올바르지 않습니다.')
    return name

def relationships(z,member):
    path=posixpath.join(posixpath.dirname(member),'_rels',posixpath.basename(member)+'.rels')
    if path not in z.namelist():return {}
    return {r.attrib['Id']:target(member,r.attrib['Target']) for r in ET.fromstring(z.read(path)) if r.attrib.get('TargetMode')!='External'}

def inventory(path):
    result=[]
    with zipfile.ZipFile(path) as z:
        infos=z.infolist()
        if len(infos)>5000 or sum(i.file_size for i in infos)>100*1024*1024:raise Problem(422,'EXPANDED_LIMIT','압축 해제 크기가 너무 큽니다.')
        workbook='xl/workbook.xml';sheets=ET.fromstring(z.read(workbook));rels=relationships(z,workbook)
        for sheet in sheets.findall(M+'sheets/'+M+'sheet'):
            member=rels.get(sheet.attrib.get(R+'id'))
            if not member:continue
            sheet_rels=relationships(z,member)
            for drawing in ET.fromstring(z.read(member)).findall(M+'drawing'):
                drawing_member=sheet_rels.get(drawing.attrib.get(R+'id'))
                if not drawing_member:continue
                media_rels=relationships(z,drawing_member)
                for anchor in ET.fromstring(z.read(drawing_member)):
                    blip=anchor.find('.//'+A+'blip')
                    if blip is None or blip.attrib.get(R+'embed') not in media_rels:continue
                    media=media_rels[blip.attrib[R+'embed']]
                    if not media.startswith('xl/media/'):raise Problem(422,'XLSX_IMAGE_PATH','엑셀 삽입 이미지 경로가 올바르지 않습니다.')
                    start=anchor.find(D+'from');end=anchor.find(D+'to');row_start=row_end=None
                    if start is not None:
                        row_start=int(start.findtext(D+'row'))+1;row_end=row_start
                        if end is not None:row_end=max(row_start,int(end.findtext(D+'row'))+(1 if int(end.findtext(D+'rowOff','0')) else 0))
                        if not 1<=row_start<=row_end<=20000:raise Problem(422,'SHEET_LIMIT','이미지의 행 범위가 처리 한도를 초과했습니다.')
                    result.append({'index':len(result)+1,'member':media,'sheet_name':sheet.attrib['name'],'row_start':row_start,'row_end':row_end})
                    if len(result)>2000:raise Problem(422,'XLSX_IMAGE_LIMIT','엑셀 삽입 이미지가 2,000개를 초과했습니다. 자료를 나눠 주세요.')
    return result

def read_image(path,index,descriptors=None):
    descriptor=next((d for d in (inventory(path) if descriptors is None else descriptors) if d['index']==index),None)
    if descriptor is None:raise Problem(404,'XLSX_IMAGE_NOT_FOUND','삽입 이미지를 찾을 수 없습니다.')
    with zipfile.ZipFile(path) as z:
        if z.getinfo(descriptor['member']).file_size>MAX_FILE_BYTES:raise Problem(422,'FILE_TOO_LARGE','삽입 이미지는 25MB까지 지원합니다.')
        content=z.read(descriptor['member'])
    try:
        with Image.open(BytesIO(content)) as im:
            if im.width*im.height>16000000:raise Problem(422,'PIXEL_LIMIT','삽입 이미지는 1,600만 픽셀까지 지원합니다.')
            mime={'PNG':'image/png','JPEG':'image/jpeg','WEBP':'image/webp','GIF':'image/gif'}.get(im.format)
            if not mime:raise ValueError('unsupported raster')
    except (OSError,ValueError,Image.DecompressionBombError):raise Problem(422,'XLSX_IMAGE_FORMAT','삽입 이미지 형식을 자동 분석할 수 없습니다. PNG·JPEG·WEBP·GIF를 사용하세요.')
    return descriptor,content,mime
