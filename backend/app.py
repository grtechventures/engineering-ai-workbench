import json, os, secrets, time, uuid
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ConfigDict, StrictInt
from typing import Literal
from .engine import Engine, ROOT, digest
from .models import PUBLIC_PROMPTS
from .worker import worker_status
from .agents import AgentConfig
from .schedules import ScheduleConfig
from contextlib import asynccontextmanager

TOKEN=secrets.token_urlsafe(32)
engine=Engine()
@asynccontextmanager
async def lifespan(app):
    engine.start_scheduler()
    try:yield
    finally:engine.stop_scheduler()

app=FastAPI(lifespan=lifespan,title='Engineering AI Workbench',docs_url=None,redoc_url=None,openapi_url=None)
class Payload(BaseModel):model_config=ConfigDict(extra='forbid')
class JobRequest(Payload):
    request:str=Field(min_length=1,max_length=2000)
    workflow:Literal['compare','extension']='compare'
class Action(Payload):
    action:Literal['approve','reject','resume','cancel']
    fingerprint:str=''
class Promote(Payload):
    job_id:str
    name:str=Field(min_length=1,max_length=80)
class Memory(Payload):
    text:str=Field(min_length=1,max_length=500)
    scope:Literal['personal','project']='project'
    source:str=Field(default='User-authored note',min_length=1,max_length=300)
    job_id:str|None=None
class Decision(Payload):
    action:Literal['approve','retire']
    revision:int|None=None
class ScheduleAction(Payload):
    action:Literal['approve','pause','resume','cancel']
    fingerprint:str
class Replay(Payload):mode:Literal['snapshot','current']='snapshot'
class Study(Payload):
    job_id:str
    windows:list[StrictInt]=Field(default_factory=lambda:[1,3,5,9],min_length=1,max_length=8)
    budget_seconds:int=Field(default=5,ge=1,le=10)
class PluginSwitch(Payload):enabled:bool
class Reason(Payload):topic:Literal['rmse','validation','sampling']
class AgentEdit(Payload):
    config:AgentConfig
    revision:int|None=None
class AgentTask(Payload):request:str=Field(min_length=1,max_length=2000)
class ConversationStart(Payload):agent_id:str

@app.middleware('http')
async def local_boundary(request:Request,call_next):
    host=request.headers.get('host','')
    if host.split(':')[0] not in ('127.0.0.1','localhost','testserver'):
        return JSONResponse({'detail':'Local prototype only'},status_code=403)
    origin=request.headers.get('origin')
    if origin and origin!=str(request.base_url).rstrip('/'):
        return JSONResponse({'detail':'Cross-origin request blocked'},status_code=403)
    if request.method not in ('GET','HEAD'):
        if request.headers.get('x-workbench-token')!=TOKEN:
            return JSONResponse({'detail':'Reload the workbench to authorize this local request'},status_code=403)
        if int(request.headers.get('content-length','0'))>20000:
            return JSONResponse({'detail':'Request is too large'},status_code=413)
    response=await call_next(request)
    response.headers['Cache-Control']='no-store'
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
    return response

@app.exception_handler(ValueError)
async def bad_request(request,exc):return JSONResponse({'detail':str(exc)},status_code=409)
@app.exception_handler(KeyError)
async def not_found(request,exc):return JSONResponse({'detail':'Item not found'},status_code=404)

@app.get('/api/bootstrap')
def bootstrap():
    with engine.lock:
        jobs=[{k:x[k] for k in ['id','request','status','created','updated','error','extension']} for x in engine.db.execute('SELECT * FROM jobs ORDER BY created DESC')]
    return {'token':TOKEN,'jobs':jobs,'catalog':engine.catalog(),'models':engine.gateway.info(),'worker':worker_status(),
            'project':{'name':'Response validation','classification':'Synthetic data','runs':['Run A · baseline','Run B · revision']},
            'identity':'Local demo reviewer','version':'0.4.0','scheduler':{'running':bool(engine.scheduler_thread and engine.scheduler_thread.is_alive()),'error':engine.scheduler_error},'storage':engine.artifacts.info(),'agents':engine.list_agents(),'conversations':engine.conversation_list()}

@app.get('/api/schedules')
def schedules():return engine.schedule_list()
@app.post('/api/schedules')
def create_schedule(body:ScheduleConfig):return engine.schedule_create(body.model_dump())
@app.post('/api/schedules/{sid}/action')
def schedule_action(sid:str,body:ScheduleAction):return engine.schedule_action(sid,body.action,body.fingerprint)

@app.post('/api/conversations')
def new_conversation(body:ConversationStart):return engine.conversation_create(body.agent_id)
@app.get('/api/conversations/{cid}')
def get_conversation(cid:str):return engine.conversation_get(cid)
@app.post('/api/conversations/{cid}/messages')
def message(cid:str,body:AgentTask):return engine.conversation_send(cid,body.request)

@app.post('/api/agents')
def create_agent(body:AgentEdit):return engine.agent_save(body.config.model_dump())
@app.post('/api/agents/{aid}')
def update_agent(aid:str,body:AgentEdit):return engine.agent_save(body.config.model_dump(),aid,body.revision)
@app.post('/api/agents/{aid}/enabled')
def enable_agent(aid:str,body:PluginSwitch):return engine.agent_switch(aid,body.enabled)
@app.post('/api/agents/{aid}/run')
def run_agent(aid:str,body:AgentTask):return {'id':engine.create(body.request,agent=engine.agent_get(aid))}
@app.post('/api/jobs/{j}/clarify')
def clarify_job(j:str,body:AgentTask):
    item=engine.get(j)
    if item['status']!='needs_input' or not item.get('agent'):raise ValueError('This job is not awaiting clarification')
    # A new job preserves the original request and its decision record.
    child=engine.create(body.request,agent=item['agent'])
    engine.event(child,'clarification','Revised task from an earlier clarification request')
    engine.event(j,'clarification','A revised task was submitted as a new job')
    return {'id':child}
@app.post('/api/jobs')
def new_job(body:JobRequest):
    return {'id':engine.create(body.request,body.workflow=='extension')}
@app.get('/api/jobs/{j}')
def job(j:str):return engine.get(j)
@app.post('/api/jobs/{j}/action')
def action(j:str,body:Action):engine.act(j,body.action,body.fingerprint);return {'ok':True}
@app.post('/api/jobs/{j}/explain')
def explain(j:str):
    item=engine.get(j)
    if not item['result']:raise ValueError('A numerical result is required')
    try: text=engine.gateway.complete('local','Explain these computed comparison metrics without inventing limits. State that the data is synthetic.',engineering_context=item['result']['metrics'])
    except Exception as e:raise ValueError('Local model request failed or is not configured. Check the server configuration.') from e
    engine.event(j,'local_model','Local model produced a draft explanation; numerical results were unchanged')
    return {'text':text,'label':'Local model draft — review required'}
@app.get('/api/jobs/{j}/report')
def report(j:str):
    return Response(json.dumps(engine.evidence(j),indent=2),media_type='application/json',headers={'Content-Disposition':'attachment; filename="comparison-evidence.json"'})
@app.post('/api/jobs/{j}/replay')
def replay_job(j:str,body:Replay):return engine.replay(j,body.mode)
@app.get('/api/studies')
def studies():return engine.study_list()
@app.post('/api/studies')
def study(body:Study):return engine.study_create(body.job_id,body.windows,body.budget_seconds)
@app.post('/api/studies/{sid}/action')
def study_action(sid:str,body:Action):return engine.study_act(sid,body.action,body.fingerprint)
@app.get('/api/studies/{sid}/report')
def study_report(sid:str):
    return Response(json.dumps(engine.study_get(sid),indent=2),media_type='application/json',headers={'Content-Disposition':'attachment; filename="study-evidence.json"'})
@app.get('/api/knowledge/search')
def knowledge_search(q:str=''):return engine.knowledge_search(q[:2000])
@app.post('/api/skills')
def promote(body:Promote):
    item=engine.get(body.job_id)
    if item['status']!='accepted':raise ValueError('Accept the engineering report before proposing a reusable skill')
    sid=uuid.uuid4().hex
    with engine.lock:
        engine.db.execute('INSERT INTO skills VALUES(?,?,?,?,?,?)',(sid,body.name,'Reusable comparison workflow proposed from an accepted job. Each run uses the current authorized inputs.','candidate','0.1.0',body.job_id));engine.db.commit()
    engine.event(body.job_id,'skill','Proposed a reusable skill for a separate release review');return {'id':sid}
@app.post('/api/skills/{sid}/decision')
def skill_decision(sid:str,body:Decision):
    if sid=='compare-runs':raise ValueError('The bundled baseline is managed through the plugin')
    with engine.lock:
        row=engine.db.execute('SELECT * FROM skills WHERE id=?',(sid,)).fetchone()
        if not row:raise KeyError(sid)
        if body.action=='approve' and row['status']!='candidate':raise ValueError('Only a candidate can be released')
        engine.db.execute('UPDATE skills SET status=? WHERE id=?',('released' if body.action=='approve' else 'retired',sid));engine.db.commit()
    return {'ok':True}
@app.post('/api/skills/{sid}/run')
def skill_run(sid:str):
    with engine.lock:row=engine.db.execute('SELECT * FROM skills WHERE id=?',(sid,)).fetchone()
    if not row or row['status']!='released':raise ValueError('Only released skills can run')
    extension=bool(engine.get(row['job_id'])['extension']) if row['job_id'] else False
    # This prototype reuses the recipe. Extension scripts still require fresh review.
    return {'id':engine.create('Run skill: '+row['name'],extension)}
@app.post('/api/knowledge')
def memory(body:Memory):
    return engine.knowledge_propose(body.text,body.scope,body.source,body.job_id)
@app.post('/api/knowledge/{mid}/decision')
def memory_decision(mid:str,body:Decision):
    engine.knowledge_decide(mid,body.action,body.revision)
    return {'ok':True}
@app.post('/api/plugin')
def plugin(body:PluginSwitch):
    with engine.lock:
        engine.db.execute("UPDATE settings SET value=? WHERE key='plugin'",('enabled' if body.enabled else 'disabled',));engine.db.commit()
    return {'ok':True}
@app.post('/api/general-reasoning')
def general(body:Reason):
    raise ValueError('Internet inference is disabled by the offline policy')
@app.get('/api/source')
def source():
    return {'files':[{'name':'C++ binary gateway','path':'legacy/engineering_demo.cpp','content':(ROOT/'legacy/engineering_demo.cpp').read_text()},
                     {'name':'Released comparison routine','path':'backend/analysis.py','content':(ROOT/'backend/analysis.py').read_text().split('DRAFT =')[0]}],
            'notice':'Curated, read-only source discovery. Source visibility does not grant execution authority.'}
@app.get('/')
def index():return FileResponse(ROOT/'frontend/index.html')
app.mount('/static',StaticFiles(directory=ROOT/'frontend'),name='static')
