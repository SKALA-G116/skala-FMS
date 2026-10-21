"""Register durable analysis without calling an LLM inside the HTTP transaction."""
from backend.app.infrastructure.database import get
from backend.app.infrastructure.database import put
from backend.app.infrastructure.database import uid
from backend.app.infrastructure.database import now
from backend.app.domains.jobs.service import enqueue
from backend.app.domains.jobs.service import getjob

def queue_analysis(c,revision_id,force=False):
    from backend.app.domains.ingestion.archives import state
    revision=get(c,'revision',revision_id);get(c,'document',revision['document_id'],True)
    if state(c,'document',revision['document_id'])['archived']:return None,None
    c.execute('SELECT pg_advisory_xact_lock(hashtext(%s))',('analysis:'+revision_id,))
    rev=get(c,'revision',revision_id)
    existing=c.execute("SELECT data FROM app_records WHERE kind='analysis_run' AND data->>'document_revision_id'=%s ORDER BY created_at DESC LIMIT 1",(revision_id,)).fetchone()
    if existing and existing['data'].get('job_id') and (not force or getjob(c,existing['data']['job_id'])['status'] in ('queued','running')) and existing['data'].get('mode')==__import__('os').getenv('FOOD_ANALYSIS_MODE','agent'):return existing['data'],None
    run={'id':uid(),'document_revision_id':revision_id,'workflow_profile':'auto','status':'queued','created_at':now(),'mode':__import__('os').getenv('FOOD_ANALYSIS_MODE','agent')}
    if rev.get('extraction_ids') and not rev.get('parse_issues'):run['extraction_id']=rev['extraction_ids'][-1]
    job=enqueue(c,'analyze',{'document_revision_id':revision_id,'workflow_profile':'auto'},run['id']);run['job_id']=job['id'];put(c,'analysis_run',run)
    doc=get(c,'document',rev['document_id']);doc['analysis_status']='queued';put(c,'document',doc);return run,job
