"""
==============================================================================
FMS_FILE_SPEC
documents.py - 원본 텍스트·표·PDF·이미지 파싱
==============================================================================
설명:
    - 원본 텍스트·표·PDF·이미지 파싱
입력·출력 명세:
    - 입력: 파일 경로·파일명·선택 OCR 환경
    - 출력: 본문·셀·페이지·좌표와 confidence를 갖는 segment 목록
실행 가정:
    - 크기·페이지·셀·픽셀·구간을 제한하고 OCR는 선택 구성
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

    2026-10-21  미지정      v0.1.0   업체 표 직접 정규화·중복 통합·원문 이력 보존

    2026-10-22  김재현(Finn) v0.1.0   자료·Agent·검수 승인·식품 DB 중심 흐름 및 알레르기 표기 정리

    상세 Git 이력: git log --follow -- backend/app/parsers/documents.py
    공통 규칙: doc/file-header-policy.md

기존 모듈 설명:
    Bounded synchronous parsing, executed only in the worker process.
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

import os
import zipfile
import csv
import re
from pathlib import Path
from bs4 import BeautifulSoup
from PIL import Image
from backend.app.infrastructure.database import Problem

MAX_BYTES=20*1024*1024

def parse(path,filename):
    if path.stat().st_size>MAX_BYTES:raise Problem(422,'FILE_TOO_LARGE','파일은 20MB까지 지원합니다.')
    ext=Path(filename).suffix.lower();out=[]
    def block(text,locator,confidence=None,**metadata):
        text=str(text).strip()
        if text:
            if len(out)>=2000:raise Problem(422,'SEGMENT_LIMIT','분석 구간이 2,000개를 넘습니다. 파일을 나누세요.')
            for start in range(0,len(text),3500):out.append({'text':text[start:start+3500],'locator':{**locator,**({'start_offset':start,'end_offset':min(start+3500,len(text))} if locator['kind']=='html' else {})},'confidence':confidence,**metadata})
    if ext in ('.txt','.csv','.tsv','.md','.html','.htm','.json'):
        text=path.read_text(encoding='utf-8-sig')
        if ext in ('.html','.htm'):
            soup=BeautifulSoup(text,'html.parser')
            for el in soup(['script','style','iframe']):el.decompose()
            for table in soup.find_all('table'):
                rendered='\n'.join(' | '.join(cell.get_text(' ',strip=True) for cell in row.find_all(['th','td'],recursive=False)) for row in table.find_all('tr'))
                table.replace_with('\n'+rendered+'\n')
            text=(soup.select_one('#bo_v_con') or soup).get_text('\n',strip=True)
        from backend.app.domains.catalog.record import header_mapping; from backend.app.domains.catalog.record import from_table_row
        mapping=None;delimiter=None
        for i,line in enumerate(text.splitlines()):
            locator={'kind':'html','block_id':f'line-{i+1}'};metadata={}
            candidates=[delimiter] if delimiter else ['\t','|',',']
            row=None
            for candidate in candidates:
                cells=next(csv.reader([line],delimiter=candidate));cells=cells[1:-1] if candidate=='|' and line.strip().startswith('|') and line.strip().endswith('|') else cells
                detected=header_mapping(cells)
                if detected:mapping=detected;delimiter=candidate;metadata['structured_table_header']=True;row=cells;break
                if delimiter:row=cells
            if mapping and row and not metadata and not all(re.fullmatch(r'[:\s-]*',str(cell)) for cell in row):
                # End a table at prose or a blank line; never reinterpret prose as a row.
                if len(row)>max(mapping.values()):
                    record=from_table_row(row,mapping,locator)
                    if record:metadata['food_record']=record
                else:mapping=None;delimiter=None
            block(line,locator,**metadata)
    elif ext in ('.xlsx','.xls'):
        from backend.app.parsers.xlsx_merges import merge_anchors,expand_row
        merges=merge_anchors(path) if ext=='.xlsx' else {}
        if ext=='.xlsx':
            with zipfile.ZipFile(path) as z:
                if sum(x.file_size for x in z.infolist())>100*1024*1024:raise Problem(422,'EXPANDED_LIMIT','압축 해제 크기가 너무 큽니다.')
            import openpyxl
            excel_stream=path.open('rb')
            book=openpyxl.load_workbook(excel_stream,read_only=True,data_only=True)
            sheets=((s.title,s.iter_rows(values_only=True)) for s in book)
        else:
            import xlrd
            book=xlrd.open_workbook(path,on_demand=True)
            sheets=((s.name,(s.row_values(i) for i in range(s.nrows))) for s in book.sheets())
        cells=0
        try:
            from backend.app.domains.catalog.record import header_mapping; from backend.app.domains.catalog.record import from_table_row
            for name,rows in sheets:
                mapping=None;headers=None;anchor_values={}
                for i,row in enumerate(rows,1):
                    cells+=sum(v is not None and v!='' for v in row)
                    if i>20000 or cells>200000:raise Problem(422,'SHEET_LIMIT','표의 행·셀 제한을 초과했습니다.')
                    if not any(v is not None and str(v).strip() for v in row):continue
                    locator={'kind':'spreadsheet','sheet_name':name,'cell_range':f'A{i}:{column(len(row))}{i}'}
                    expanded,merged_sources=expand_row(i,row,merges.get(name,{}),anchor_values)
                    detected=header_mapping(expanded);metadata={}
                    if detected:
                        mapping=detected;headers=expanded;metadata['structured_table_header']=True
                        name_col=mapping.get('food_name')
                        if name_col is not None and 'variant_label' not in mapping:
                            for col,anchor in merged_sources.items():
                                if expanded[col]==expanded[name_col] and col!=name_col:mapping['variant_label']=col;break
                    elif mapping:
                        record=from_table_row(expanded,mapping,locator,headers=headers)
                        if record:
                            for field,index in mapping.items():
                                if index in merged_sources and field in record['field_sources']:
                                    record['field_sources'][field].update(locator={**locator,'cell_range':merged_sources[index]},origin='merged_cell')
                            metadata['food_record']=record
                    block(' | '.join('' if v is None else str(v) for v in row),locator,**metadata)
        finally:
            if ext=='.xlsx':book.close();excel_stream.close()
            else:book.release_resources()
    elif ext=='.pdf':
        from pypdf import PdfReader
        reader=PdfReader(path)
        if len(reader.pages)>20:raise Problem(422,'PAGE_LIMIT','PDF는 20페이지까지 지원합니다.')
        for i,page in enumerate(reader.pages):
            text=page.extract_text() or ''
            if not text.strip():
                if os.getenv('FOOD_OCR_ENABLED','false').lower()!='true':raise Problem(422,'OCR_NOT_CONFIGURED','스캔 PDF 처리를 위해 OCR를 설정하세요.')
                for row in ocr_result(path,i+1):block(row['text'],row['locator'],row['confidence'])
                continue
            block(text,{'kind':'html','block_id':f'pdf-page-{i+1}'})
    elif ext in ('.png','.jpg','.jpeg','.webp','.gif'):
        with Image.open(path) as im:
            if im.width*im.height>16000000:raise Problem(422,'PIXEL_LIMIT','이미지는 1,600만 픽셀까지 지원합니다.')
        if os.getenv('FOOD_OCR_ENABLED','false').lower()!='true':raise Problem(422,'OCR_NOT_CONFIGURED','PaddleOCR가 설정되지 않았습니다. 텍스트·Excel 파일을 사용하거나 OCR 작업자를 설정하세요.')
        for row in ocr_result(path):block(row['text'],row['locator'],row['confidence'])
    else:raise Problem(422,'UNSUPPORTED_FILE','TXT, CSV, HTML, XLSX, XLS, PDF, PNG, JPEG, WEBP를 지원합니다.')
    if not out:raise Problem(422,'EMPTY_DOCUMENT','분석할 텍스트가 없습니다.')
    return out

def column(n):
    s=''
    while n:n,r=divmod(n-1,26);s=chr(65+r)+s
    return s or 'A'

def ocr_result(path,page=None):
    from backend.app.parsers.ocr_pool import OCR
    return OCR.request(path,page)
