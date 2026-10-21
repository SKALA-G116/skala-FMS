from psycopg.types.json import Jsonb
from backend.app.infrastructure.database import Problem
from backend.app.infrastructure.database import now
from backend.app.infrastructure.database import uid

def enqueue(c,kind,payload,run=None,parent=None):
    job={'id':uid(),'type':kind,'status':'queued','stage':'대기 중','processed_count':0,'total_count':None,'attempt':1,'created_at':now(),'started_at':None,'finished_at':None,'parent_job_id':parent,'issues':[],'result':None,'allowed_actions':['cancel'] if kind!='apply' else [],'analysis_run_id':run}
    c.execute('INSERT INTO jobs(id,type,data,payload) VALUES(%s,%s,%s,%s)',(job['id'],kind,Jsonb(job),Jsonb(payload)));return job

def getjob(c,id,lock=False):
    r=c.execute('SELECT data FROM jobs WHERE id=%s'+(' FOR UPDATE' if lock else ''),(id,)).fetchone()
    if not r:raise Problem(404,'NOT_FOUND','작업을 찾을 수 없습니다.')
    return r['data']

def savejob(c,j):c.execute('UPDATE jobs SET data=%s,status=%s WHERE id=%s',(Jsonb(j),j['status'],j['id']))
