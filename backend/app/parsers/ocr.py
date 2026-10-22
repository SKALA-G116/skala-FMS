"""
==============================================================================
FMS_FILE_SPEC
ocr.py - 격리 OCR 실행과 프로세스 수명 관리
==============================================================================
설명:
    - 격리 OCR 실행과 프로세스 수명 관리
입력·출력 명세:
    - 입력: 이미지/PDF 경로·페이지·timeout·OCR 환경
    - 출력: 인식 텍스트·confidence·locator 또는 OCR 오류
실행 가정:
    - 가중치 재사용·직렬 요청·유휴 종료·임시 자원 정리
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

    2026-10-22  김재현(Finn) v0.1.0   OCR 정상 종료·native 충돌 격리 및 재시작 검증

    상세 Git 이력: git log --follow -- backend/app/parsers/ocr.py
    공통 규칙: doc/file-header-policy.md

기존 모듈 설명:
    Isolated PaddleOCR adapter; --serve reuses one model across bounded requests.
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

import sys
import json
import contextlib
import tempfile
import gc
import os
from pathlib import Path
from PIL import Image

def engine():
    with contextlib.redirect_stdout(sys.stderr):
        import paddle
        # Parent owns timeout/termination. Paddle's fatal-signal handler can
        # recurse while a macOS native thread pool is being stopped.
        paddle.disable_signal_handler()
        from paddleocr import PaddleOCR
        return PaddleOCR(lang='korean',device='cpu',cpu_threads=2,enable_mkldnn=False,text_detection_model_name='PP-OCRv5_mobile_det',text_recognition_model_name='korean_PP-OCRv5_mobile_rec',use_doc_orientation_classify=False,use_doc_unwarping=False,use_textline_orientation=False)

def recognize(model,source,page=None):
    with tempfile.TemporaryDirectory() as directory:
        path=str(Path(directory)/'page.png')
        if page:
            import pypdfium2 as pdfium
            pdf=pdfium.PdfDocument(source)
            try:
                image=pdf[page-1].render(scale=150/72).to_pil()
                try:image.save(path)
                finally:image.close()
            finally:pdf.close()
        else:
            with Image.open(source) as image:
                converted=image.convert('RGB')
                try:converted.save(path)
                finally:converted.close()
        with Image.open(path) as image:w,h=image.size
        if w*h>16000000:raise ValueError('pixel limit')
        rows=[]
        with contextlib.redirect_stdout(sys.stderr):
            for result in model.predict(path):
                data=result.json
                if isinstance(data,str):data=json.loads(data)
                data=data.get('res',data)
                for text,score,box in zip(data['rec_texts'],data['rec_scores'],data['rec_boxes']):
                    if len(rows)>=2000:raise ValueError('OCR segment limit')
                    x1,y1,x2,y2=map(float,box)
                    rows.append({'text':text,'confidence':float(score),'locator':{'kind':'pdf' if page else 'image','page_number':page or 1,'bbox':[x1/w,y1/h,x2/w,y2/h],'image_width':w,'image_height':h}})
        return rows

def main():
    if '--serve' in sys.argv:
        model=None
        for line in sys.stdin:
            try:
                request=json.loads(line)
                if request.get('shutdown') is True:break
                if model is None:model=engine()
                response={'ok':True,'rows':recognize(model,request['source'],request.get('page'))}
            except Exception as ex:response={'ok':False,'error':type(ex).__name__}
            print(json.dumps(response,ensure_ascii=False),flush=True);gc.collect()
        # This dedicated subprocess holds only disposable native model state.
        # Do not run Paddle thread-pool destructors during interpreter teardown.
        sys.stdout.flush();sys.stderr.flush();os._exit(0)
    else:print(json.dumps(recognize(engine(),sys.argv[1],int(sys.argv[2]) if len(sys.argv)>2 else None),ensure_ascii=False))

if __name__=='__main__':main()
