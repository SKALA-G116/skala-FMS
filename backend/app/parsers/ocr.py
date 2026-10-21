"""Isolated PaddleOCR adapter; --serve reuses one model across bounded requests."""
import sys
import json
import contextlib
import tempfile
import gc
from pathlib import Path
from PIL import Image

def engine():
    with contextlib.redirect_stdout(sys.stderr):
        from paddleocr import PaddleOCR
        return PaddleOCR(lang='korean',text_detection_model_name='PP-OCRv5_mobile_det',text_recognition_model_name='korean_PP-OCRv5_mobile_rec',use_doc_orientation_classify=False,use_doc_unwarping=False,use_textline_orientation=False)

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
                if model is None:model=engine()
                response={'ok':True,'rows':recognize(model,request['source'],request.get('page'))}
            except Exception as ex:response={'ok':False,'error':type(ex).__name__}
            print(json.dumps(response,ensure_ascii=False),flush=True);gc.collect()
    else:print(json.dumps(recognize(engine(),sys.argv[1],int(sys.argv[2]) if len(sys.argv)>2 else None),ensure_ascii=False))

if __name__=='__main__':main()
