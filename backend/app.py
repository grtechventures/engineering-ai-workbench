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
class AgentTask(Payload):
    request:str=Field(min_length=1,max_length=2000)
    job_id:str|None=None
    parent_id:str|None=None
    dynamic:bool=False
class PythonDecision(Payload):
    action:Literal['approve','reject','accept','retry']
    fingerprint:str
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
        if int(request.headers.get('content-length','0'))>(1024**2 if request.url.path.endswith('/chunk') else 20000):
            return JSONResponse({'detail':'Request is too large'},status_code=413)
    response=await call_next(request)
    response.headers['Cache-Control']='no-store'
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
    if request.url.path == "/static/viewer3d.html":
        response.headers['Content-Security-Policy']=response.headers['Content-Security-Policy'].replace("frame-ancestors 'none'", "frame-ancestors 'self'")
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
def message(cid:str,body:AgentTask):return engine.conversation_send(cid,body.request,selected_job=body.job_id,parent_id=body.parent_id,dynamic=body.dynamic)

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
    if engine.db.execute('SELECT id FROM authored_skills WHERE id=?',(sid,)).fetchone():raise ValueError('Prepare authored skills using an assigned agent')
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

@app.get('/api/python-tasks/{pid}')
def python_task(pid:str):return engine.plot_get(pid)
@app.post('/api/python-tasks/{pid}/action')
def python_action(pid:str,body:PythonDecision):return engine.plot_action(pid,body.action,body.fingerprint)
@app.get('/api/python-tasks/{pid}/image')
def python_image(pid:str):return FileResponse(engine.plot_image(pid),media_type='image/png')

from .tool_registry import ToolRegistration
@app.get('/api/tools')
def registered_tools():return {'registered':engine.tool_registrations(),'released':engine.catalog()['plugin']}
@app.post('/api/tools')
def register_tool(body:ToolRegistration):return engine.tool_register(body.model_dump())

from .authored_skills import SkillDraft,PackageDraft
class PrepareSkill(Payload):
    agent_id:str
    job_id:str|None=None
class PackageAction(Payload):action:Literal['enable','disable']
@app.get('/api/authored-skills')
def authored_skills():return engine.authored_list()
@app.post('/api/authored-skills')
def create_authored_skill(body:SkillDraft):return engine.authored_create(body.model_dump())
@app.post('/api/authored-skills/{sid}/prepare')
def prepare_authored_skill(sid:str,body:PrepareSkill):return engine.authored_prepare(sid,body.agent_id,body.job_id)
@app.get('/api/skill-packages')
def packages():return engine.packages_list()
@app.post('/api/skill-packages')
def create_package(body:PackageDraft):return engine.package_create(body.model_dump())
@app.post('/api/skill-packages/{pid}/action')
def package_action(pid:str,body:PackageAction):return engine.package_action(pid,body.action)

from .resources import ResourceDraft
@app.get('/api/resources')
def resources():return engine.resources_list()
@app.post('/api/resources')
def resource_add(body:ResourceDraft):return engine.resource_add(body.model_dump())
@app.post('/api/resources/{rid}/inspect')
def resource_inspect(rid:str):return engine.resource_inspect(rid)
@app.post('/api/resources/{rid}/remove')
def resource_remove(rid:str):return engine.resource_remove(rid)

from .configuration import Connection,Runtime
class ConnectionAction(Payload):action:Literal['test','activate']
@app.get('/api/configuration')
def configuration():return engine.configuration()
@app.post('/api/connections')
def connection_save(body:Connection):return engine.connection_save(body.model_dump())
@app.post('/api/connections/{cid}')
def connection_edit(cid:str,body:Connection):return engine.connection_save(body.model_dump(),cid)
@app.post('/api/connections/{cid}/action')
def connection_action(cid:str,body:ConnectionAction):return engine.connection_action(cid,body.action)
@app.post('/api/runtime')
def runtime_save(body:Runtime):return engine.runtime_save(body.model_dump())
@app.post('/api/runtime/test')
def runtime_test():return engine.runtime_test()
@app.post('/api/security/disable-discovery')
def disable_discovery():return engine.discovery_disable()

from .attachments import Attachment
@app.post('/api/conversations/{cid}/attachments')
def attachment_add(cid:str,body:Attachment):return engine.attachment_add(cid,body.model_dump())
@app.post('/api/conversations/{cid}/attachments/clear')
def attachment_clear(cid:str):return engine.attachment_clear(cid)

from .attachments import UploadStart
@app.post('/api/conversations/{cid}/uploads')
def upload_start(cid:str,body:UploadStart):return engine.upload_start(cid,body.model_dump())
@app.post('/api/uploads/{uid}/chunk')
async def upload_chunk(uid:str,request:Request,offset:int):
    data=bytearray()
    async for chunk in request.stream():
        data.extend(chunk)
        if len(data)>1024**2:raise ValueError('Chunk exceeds 1 MB')
    return engine.upload_chunk(uid,offset,bytes(data))
@app.post('/api/uploads/{uid}/finish')
def upload_finish(uid:str):return engine.upload_finish(uid)

from .configuration import MatlabConfig
@app.get('/api/runtime/matlab')
def matlab_get():return engine.matlab_get()
@app.post('/api/runtime/matlab')
def matlab_save(body:MatlabConfig):return engine.matlab_save(body.model_dump())

from .channels import ChannelConfig
@app.get('/api/channels')
def channels_get(): return engine.channels_get()
@app.post('/api/channels')
def channel_save(body: ChannelConfig): return engine.channel_save(body.model_dump())
@app.post('/api/channels/{cid}')
def channel_update(cid: str, body: ChannelConfig): return engine.channel_save(body.model_dump(), cid)
@app.post('/api/channels/{cid}/preview')
def channel_preview(cid: str, body: Payload): return engine.channel_preview(cid)

@app.get('/api/python-tasks/{pid}/scene')
def python_scene(pid: str):
    from .scenes import validate_scene
    p=engine.plot_get(pid)
    if p['status'] not in ('result_review','accepted') or 'scene3d' not in p.get('output',{}):
        raise ValueError('3D scene is not ready')
    return validate_scene(p['output']['scene3d'])
