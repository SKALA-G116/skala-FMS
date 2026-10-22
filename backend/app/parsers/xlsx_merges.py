"""
==============================================================================
FMS_FILE_SPEC
xlsx_merges.py - 프로젝트 설정 xlsx_merges.py
==============================================================================
설명:
    - 프로젝트 설정 xlsx_merges.py
입력·출력 명세:
    - 입력: 도구별 설정·실행 환경
    - 출력: 해당 도구의 구성 또는 실행 결과
실행 가정:
    - 실제 비밀값과 로컬 실행 데이터는 Git에서 제외
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

    2026-10-22  김재현(Finn) v0.1.0   자료·Agent·검수 승인·식품 DB 중심 흐름 및 알레르기 표기 정리

    상세 Git 이력: git log --follow -- backend/app/parsers/xlsx_merges.py
    공통 규칙: doc/file-header-policy.md

기존 모듈 설명:
    Read explicit XLSX merge anchors without loading the workbook into memory.
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
from openpyxl.utils.cell import range_boundaries,get_column_letter
from backend.app.infrastructure.database import Problem


MAX_MERGE_CELLS=200000

def merge_anchors(path):
    result={};total=0
    with zipfile.ZipFile(path) as archive:
        if len(archive.infolist())>5000 or sum(i.file_size for i in archive.infolist())>100*1024*1024:
            raise Problem(422,'EXPANDED_LIMIT','압축 해제 크기가 너무 큽니다.')
        main='{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
        relations=ET.fromstring(archive.read('xl/_rels/workbook.xml.rels'))
        targets={r.attrib['Id']:r.attrib['Target'] for r in relations if r.attrib.get('Type','').endswith('/worksheet')}
        workbook=ET.fromstring(archive.read('xl/workbook.xml'))
        for sheet in workbook.findall(main+'sheets/'+main+'sheet'):
            rid=sheet.attrib.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
            target=targets.get(rid)
            if not target:continue
            member=posixpath.normpath(target.lstrip('/') if target.startswith('/') else posixpath.join('xl',target))
            if not member.startswith('xl/') or member not in archive.namelist():continue
            anchors={}
            with archive.open(member) as stream:
                for _,element in ET.iterparse(stream,events=('end',)):
                    if element.tag==main+'mergeCell':
                        left,top,right,bottom=range_boundaries(element.attrib['ref'])
                        if bottom>20000 or right>100 or total+(bottom-top+1)*(right-left+1)>MAX_MERGE_CELLS:
                            raise Problem(422,'SHEET_LIMIT','병합 셀 범위가 처리 한도를 초과했습니다.')
                        total+=(bottom-top+1)*(right-left+1)
                        for row in range(top,bottom+1):
                            for col in range(left,right+1):anchors[(row,col)]=(top,left)
                    element.clear()
            result[sheet.attrib['name']]=anchors
    return result


def expand_row(row_number,row,anchors,values):
    result=list(row);sources={}
    for col,value in enumerate(row,1):
        key=(row_number,col);anchor=anchors.get(key)
        if anchor==key:values[key]=value
        elif anchor and value in (None,'') and anchor in values:
            result[col-1]=values[anchor]
            if result[col-1] not in (None,''):sources[col-1]=get_column_letter(anchor[1])+str(anchor[0])
    return result,sources
