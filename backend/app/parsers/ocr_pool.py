"""One serialized OCR subprocess: reuse weights, recycle, release idle native memory."""
import os
import sys
import json
import time
import subprocess
import threading
import queue
import atexit
from pathlib import Path
from backend.app.infrastructure.database import Problem
from backend.app.runtime.limits import OCR_IDLE_SECONDS
from backend.app.runtime.limits import OCR_MAX_REQUESTS

class OCRProcess:
    def __init__(self,command=None):
        self.command=command;self.lock=threading.Lock();self.process=None;self.responses=None;self.requests=0;self.last_used=0
    def _stop(self):
        process=self.process;self.process=None;self.requests=0
        if process:
            if process.poll() is None:
                process.terminate()
                try:process.wait(timeout=2)
                except subprocess.TimeoutExpired:process.kill();process.wait(timeout=2)
            for pipe in (process.stdin,process.stdout):
                if pipe:
                    try:pipe.close()
                    except OSError:pass
    def _start(self):
        self._stop();env=os.environ.copy()
        for key in ('OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS'):env.setdefault(key,'2')
        command=self.command or [os.getenv('FOOD_OCR_PYTHON',sys.executable),'-u','-m','backend.app.parsers.ocr','--serve']
        process=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,bufsize=1,cwd=str(Path(__file__).resolve().parents[3]),env=env)
        responses=queue.Queue(maxsize=1);self.process=process;self.responses=responses
        def read():
            while True:
                line=process.stdout.readline(4*1024*1024+1)
                if not line:
                    try:responses.put_nowait(None)
                    except queue.Full:pass
                    return
                if len(line)>4*1024*1024 or not line.endswith('\n'):
                    try:responses.put_nowait(None)
                    except queue.Full:pass
                    return
                try:responses.put_nowait(line)
                except queue.Full:return
        threading.Thread(target=read,daemon=True,name='ocr-json-reader').start()
    def request(self,path,page=None,timeout=120):
        with self.lock:
            if self.process is None or self.process.poll() is not None or self.requests>=OCR_MAX_REQUESTS:self._start()
            try:
                self.process.stdin.write(json.dumps({'source':str(path),'page':page})+'\n');self.process.stdin.flush()
                line=self.responses.get(timeout=timeout)
                if line is None:raise ValueError('OCR worker exited')
                result=json.loads(line)
                if not result.get('ok'):raise ValueError('OCR prediction failed')
                rows=result['rows']
                if not isinstance(rows,list) or len(rows)>2000:raise ValueError('OCR result limit')
                self.requests+=1;return rows
            except queue.Empty:
                self._stop();raise Problem(422,'OCR_TIMEOUT','OCR 처리 시간을 초과했습니다. 이미지 크기나 페이지 수를 줄여 주세요.')
            except (ValueError,OSError,KeyError,TypeError):
                self._stop();raise Problem(422,'OCR_FAILED','OCR 작업자를 다시 시작했습니다. 재시도해 주세요.')
            finally:self.last_used=time.monotonic()
    def expire_idle(self):
        if self.lock.acquire(blocking=False):
            try:
                if self.process and time.monotonic()-self.last_used>=OCR_IDLE_SECONDS:self._stop()
            finally:self.lock.release()
    def close(self):
        with self.lock:self._stop()

OCR=OCRProcess()

atexit.register(OCR.close)
