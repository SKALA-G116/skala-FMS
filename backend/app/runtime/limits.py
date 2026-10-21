"""Bounded resources shared by HTTP, inference and queue workers."""
import os
import sys
import resource

def integer(name,default,minimum,maximum):
    try:return min(max(int(os.getenv(name,str(default))),minimum),maximum)
    except ValueError:return default

MODEL_CONCURRENCY=integer('FOOD_MODEL_CONCURRENCY',1,1,2)

MODEL_TIMEOUT=integer('FOOD_MODEL_TIMEOUT_SECONDS',240,10,600)

MODEL_INPUT_BYTES=integer('FOOD_MODEL_INPUT_BYTES',11000,4000,11000)

EXTRACTION_BYTES=integer('FOOD_EXTRACTION_MAX_BYTES',4*1024*1024,65536,8*1024*1024)

REPORT_BYTES=integer('FOOD_REPORT_MAX_BYTES',8*1024*1024,65536,16*1024*1024)

RUN_INPUT_TOKENS=integer('FOOD_RUN_INPUT_TOKENS',500000,1000,1000000)

RUN_OUTPUT_TOKENS=integer('FOOD_RUN_OUTPUT_TOKENS',200000,1000,400000)

ATTEMPT_SECONDS=integer('FOOD_ANALYSIS_SLICE_SECONDS',600,10,1800)

OCR_IDLE_SECONDS=integer('FOOD_OCR_IDLE_SECONDS',60,10,600)

OCR_MAX_REQUESTS=integer('FOOD_OCR_MAX_REQUESTS',20,1,100)

def peak_rss_bytes():
    value=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return value if sys.platform=='darwin' else value*1024
