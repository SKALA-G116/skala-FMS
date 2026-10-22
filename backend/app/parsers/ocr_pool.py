"""
==============================================================================
FMS_FILE_SPEC
ocr_pool.py - 격리 OCR 실행과 프로세스 수명 관리
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

    상세 Git 이력: git log --follow -- backend/app/parsers/ocr_pool.py
    공통 규칙: doc/file-header-policy.md

기존 모듈 설명:
    One serialized OCR subprocess: reuse weights, recycle, release idle native memory.
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
    def _stop(self,graceful=True):
        process=self.process;self.process=None;self.responses=None;self.requests=0
        if process:
            if process.poll() is None:
                if graceful:
                    try:
                        process.stdin.write('{"shutdown":true}\n');process.stdin.flush()
                        process.wait(timeout=2)
                    except (OSError,subprocess.TimeoutExpired):pass
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
                if line is None:
                    try:code=self.process.wait(timeout=.2)
                    except subprocess.TimeoutExpired:code=None
                    self._stop(graceful=False)
                    raise Problem(422,'OCR_PROCESS_EXIT','OCR 엔진이 예기치 않게 종료됐습니다. 다시 시도하면 새 작업자로 처리합니다.',[{'exit_code':code}])
                result=json.loads(line)
                if not result.get('ok'):raise ValueError('OCR prediction failed')
                rows=result['rows']
                if not isinstance(rows,list) or len(rows)>2000:raise ValueError('OCR result limit')
                self.requests+=1;return rows
            except queue.Empty:
                self._stop(graceful=False);raise Problem(422,'OCR_TIMEOUT','OCR 처리 시간을 초과했습니다. 이미지 크기나 페이지 수를 줄여 주세요.')
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
