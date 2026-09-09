import ast, hashlib, json, math, os, sqlite3, subprocess, threading, time, uuid
from pathlib import Path
from typing import TypedDict
from pydantic import BaseModel, ConfigDict, Field
# Disable remote tracing even if inherited from the developer environment.
os.environ['LANGSMITH_TRACING']='false'
os.environ['LANGCHAIN_TRACING_V2']='false'
from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt, Command
from langgraph.checkpoint.sqlite import SqliteSaver
from .analysis import compare, DRAFT
from .models import ModelGateway
from .worker import run_script, worker_status
from .agents import AgentsMixin
from .conversations import ConversationsMixin

ROOT=Path(__file__).resolve().parents[1]
class ScriptDraft(BaseModel):
    model_config=ConfigDict(extra='forbid')
    script:str=Field(min_length=1,max_length=16000)
def digest(value):
    return hashlib.sha256((value if isinstance(value,bytes) else json.dumps(value,sort_keys=True).encode())).hexdigest()
class State(TypedDict,total=False):
    job_id:str; request:str; extension:bool; inputs:dict; result:dict; script:str
    agent:dict; plan:dict; plan_fingerprint:str; plan_approved:bool; needs_input:bool
    fingerprint:str; draft_source:str; approved:bool; approved_fingerprint:str; accepted:bool; image:str; narrative:str

class Engine(AgentsMixin,ConversationsMixin):
    def __init__(self,data=None):
        self.data=Path(data or os.getenv('EWB_DATA_DIR',ROOT/'data'));self.data.mkdir(parents=True,exist_ok=True)
        self.lock=threading.RLock();self.run_lock=threading.Lock()
        self.db=sqlite3.connect(self.data/'workbench.sqlite',check_same_thread=False)
        self.db.row_factory=sqlite3.Row
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY, request TEXT, status TEXT, created REAL, updated REAL, error TEXT, extension INTEGER);
        CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY AUTOINCREMENT, job_id TEXT, at REAL, stage TEXT, detail TEXT);
        CREATE TABLE IF NOT EXISTS skills(id TEXT PRIMARY KEY, name TEXT, description TEXT, status TEXT, version TEXT, job_id TEXT);
        CREATE TABLE IF NOT EXISTS knowledge(id TEXT PRIMARY KEY, text TEXT, status TEXT, scope TEXT, job_id TEXT);
        CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT);
        ''')
        self.init_agents()
        self.init_conversations()
        self.db.execute("INSERT OR IGNORE INTO settings VALUES('plugin','enabled')")
        self.db.execute("INSERT OR IGNORE INTO skills VALUES('compare-runs','Compare analysis runs','Compare two exported response curves with units, alignment, and provenance checks.','released','1.0.0',NULL)")
        self.db.execute("UPDATE jobs SET status='interrupted', error='Service restarted. Resume from the persisted checkpoint.' WHERE status IN ('running','queued')")
        self.db.commit()
        self.cpconn=sqlite3.connect(self.data/'checkpoints.sqlite',check_same_thread=False)
        self.checkpointer=SqliteSaver(self.cpconn)
        self.gateway=ModelGateway()
        graph=StateGraph(State)
        for name,node in [('agent_plan',self.agent_plan),('plan_review',self.plan_review),('export',self.export),('prepare',self.prepare),('code_review',self.code_review),('execute',self.execute),('result_review',self.result_review)]:
            graph.add_node(name,node)
        graph.add_conditional_edges(START,lambda s:'agent_plan' if s.get('agent') else 'export')
        graph.add_conditional_edges('agent_plan',lambda s:END if s.get('needs_input') else 'plan_review')
        graph.add_conditional_edges('plan_review',lambda s:'export' if s.get('plan_approved') else END)
        graph.add_edge('export','prepare')
        graph.add_conditional_edges('prepare',lambda s:'code_review' if s['extension'] else 'execute')
        graph.add_conditional_edges('code_review',lambda s:'execute' if s['approved'] else END)
        graph.add_edge('execute','result_review');graph.add_edge('result_review',END)
        self.graph=graph.compile(checkpointer=self.checkpointer)

    def agent_plan(self,s):
        plan=self.make_plan(s)
        self.event(s['job_id'],'agent_plan',plan['planner']+': '+plan['reason'])
        with self.lock:
            self.db.execute('UPDATE jobs SET extension=? WHERE id=?',(int(plan['workflow']=='extension'),s['job_id']));self.db.commit()
        return {'plan':plan,'extension':plan['workflow']=='extension','needs_input':plan['workflow']=='clarify','plan_fingerprint':digest({'plan':plan,'request':s['request'],'agent':s['agent']})}
    def plan_review(self,s):
        answer=interrupt({'kind':'plan_review','fingerprint':s['plan_fingerprint']})
        if answer.get('fingerprint')!=s['plan_fingerprint']:raise ValueError('The plan approval is stale')
        self.check_agent(s,'extension' if s['extension'] else 'compare')
        self.event(s['job_id'],'plan_review','Plan approved by local demo reviewer' if answer.get('approve') else 'Plan rejected by local demo reviewer')
        return {'plan_approved':bool(answer.get('approve'))}
    def event(self,j,stage,detail):
        with self.lock:
            # Retry-safe recording of node milestones.
            last=self.db.execute('SELECT detail FROM events WHERE job_id=? AND stage=? ORDER BY id DESC LIMIT 1',(j,stage)).fetchone()
            if not last or last['detail']!=detail:
                self.db.execute('INSERT INTO events(job_id,at,stage,detail) VALUES(?,?,?,?)',(j,time.time(),stage,detail));self.db.commit()
    def status(self,j,value,error=None):
        with self.lock:
            self.db.execute('UPDATE jobs SET status=?,updated=?,error=? WHERE id=?',(value,time.time(),error,j));self.db.commit()
    def enabled(self):
        return self.db.execute("SELECT value FROM settings WHERE key='plugin'").fetchone()[0]=='enabled'
    def cfg(self,j): return {'configurable':{'thread_id':j},'recursion_limit':20}
    def fingerprint(self,state): return digest({'script':state['script'],'inputs':state['inputs'],'image':state['image'],'scope':'demo-project/read-only'})
    def export(self,s):
        self.check_agent(s,'extension' if s['extension'] else 'compare')
        if not self.enabled(): raise ValueError('Run Comparison plugin is disabled')
        self.event(s['job_id'],'export','Reading synthetic binary files through the C++ application')
        exe=ROOT/'legacy'/'build'/('engineering-demo.exe' if os.name=='nt' else 'engineering-demo')
        inputs={}
        for key in ['a','b']:
            path=self.data/f'run-{key}.ewb'
            raw=subprocess.run([str(exe),'export',str(path)],capture_output=True,text=True,timeout=10,check=True)
            record=json.loads(raw.stdout)
            record['source_hash']=digest(path.read_bytes());record['source_name']=path.name
            inputs[key]=record
        compare(inputs['a'],inputs['b']) # Validate before proposing any method.
        self.event(s['job_id'],'inputs','Both exports passed schema, unit, and sample alignment checks')
        return {'inputs':inputs}
    def prepare(self,s):
        self.check_agent(s,'extension' if s['extension'] else 'compare')
        self.event(s['job_id'],'plan','Reuse released comparison; draft a moving-average extension for review' if s['extension'] else 'Reuse the released comparison routine')
        update={'script':DRAFT if s['extension'] else '', 'image':worker_status()['image'],'draft_source':'Bundled example draft'}
        if s['extension'] and self.gateway.info()['local']['configured'] and (not s.get('agent') or s['agent']['mode']=='local'):
            prompt=('Return JSON with a script field containing valid Python source, no Markdown or explanatory prose. '
                    'Draft a centered five-sample moving average of B minus A. Read /inputs/data.json. '
                    'Input schema example: {"a":{"points":[[0,1.0],[1,2.0]],"y_unit":"a.u."},'
                    '"b":{"points":[[0,1.1],[1,2.2]],"y_unit":"a.u."}}. '
                    'Access arrays as data["a"]["points"] and data["b"]["points"]. '
                    'First compute delta[i] = b_points[i][1] - a_points[i][1]. '
                    'For each i, average delta[max(0,i-2):min(n,i+3)]; divide by the actual slice length, including at edges. '
                    'Use these exact window statements: window = delta[max(0, i-2):min(n, i+3)]; average = sum(window) / len(window). '
                    'Do not separately calculate the divisor. At i=0 the divisor is 3, at i=1 it is 4, at i=n-1 it is 3. '
                    'Output points must contain [a_points[i][0], average] for EVERY input sample. '
                    'Write /outputs/result.json with extension="Centered five-sample moving average", points, and unit=data["a"]["y_unit"]. '
                    'Use only json and Python built-ins. No network, binary parser, subprocess, package installs or additional files. '
                    'This proposal will require code review before execution.')
            raw=self.gateway.complete('local',prompt,schema=ScriptDraft.model_json_schema())
            try:
                code=ScriptDraft.model_validate(json.loads(raw)).script
                ast.parse(code)
            except Exception as exc:raise ValueError('Local model did not return a valid Python script proposal. No generated code executed; retry the draft.') from exc
            update['script']=code;update['draft_source']='Local model draft'
            self.event(s['job_id'],'draft','Local model proposed a script; execution remains paused for review')
        merged={**s,**update};update['fingerprint']=self.fingerprint(merged)
        return update
    def code_review(self,s):
        answer=interrupt({'kind':'code_review','fingerprint':s['fingerprint']})
        if answer.get('fingerprint')!=self.fingerprint(s): raise ValueError('Approval does not match the current code, inputs, or image')
        self.event(s['job_id'],'code_review','Exact script approved by local demo reviewer' if answer.get('approve') else 'Script rejected by local demo reviewer')
        return {'approved':bool(answer.get('approve')),'approved_fingerprint':answer.get('fingerprint','')}
    def execute(self,s):
        self.check_agent(s,'extension' if s['extension'] else 'compare')
        if not self.enabled(): raise ValueError('Plugin disabled before execution')
        self.event(s['job_id'],'execute','Executing the released numerical comparison')
        result=compare(s['inputs']['a'],s['inputs']['b'])
        if s['extension']:
            if not s.get('approved') or s.get('approved_fingerprint')!=self.fingerprint(s): raise ValueError('Exact code approval is required')
            if s['image']!=worker_status()['image']: raise ValueError('Worker image changed; create a new request for fresh approval')
            extra=run_script(s['script'],s['inputs'],self.data/'jobs'/s['job_id'])
            if extra.get('unit')!=s['inputs']['a']['y_unit'] or not isinstance(extra.get('extension'),str):
                raise ValueError('Extension unit or label is invalid')
            points=extra.get('points',[])
            if len(points)!=len(result['delta']) or any(len(p)!=2 or not all(isinstance(v,(int,float)) and math.isfinite(v) for v in p) for p in points):
                raise ValueError('Extension output validation failed')
            # Independent reference validation for the supported prototype extension.
            ds=[p[1] for p in result['delta']]
            expected=[[result['delta'][i][0],sum(ds[max(0,i-2):min(len(ds),i+3)])/len(ds[max(0,i-2):min(len(ds),i+3)])] for i in range(len(ds))]
            if any(abs(p[0]-q[0])>1e-10 or abs(p[1]-q[1])>1e-10 for p,q in zip(points,expected)):
                raise ValueError('Extension differs from its independent moving-average reference')
            result['extension']=extra
            if extra.get('execution'):
                self.event(s['job_id'],'docker','Docker completed successfully; container removed; execution receipt retained')
            result['checks'].append({'name':'Extension reference comparison','passed':True})
        m=result['metrics']
        narrative=f"Compared {m['samples']} aligned samples. The maximum absolute difference is {m['max_abs_delta']:.5f} a.u. at sample {m['peak_sample']:g}; RMSE is {m['rmse']:.5f} a.u. These synthetic results do not imply an engineering acceptance limit."
        self.event(s['job_id'],'validate','Numerical results validated; engineering acceptance is still required')
        return {'result':result,'narrative':narrative}
    def result_review(self,s):
        answer=interrupt({'kind':'result_review','fingerprint':digest(s['result'])})
        if answer.get('fingerprint')!=digest(s['result']): raise ValueError('Result changed since review')
        self.event(s['job_id'],'review','Report accepted by local demo reviewer' if answer.get('approve') else 'Changes requested by local demo reviewer')
        return {'accepted':bool(answer.get('approve'))}
    def create(self,request,extension=False,background=True,agent=None):
        if not self.enabled(): raise ValueError('Enable the Run Comparison plugin first')
        if agent:
            self.check_agent({'agent':agent})
            if agent['mode']=='local' and not self.gateway.info()['local']['configured']:raise ValueError('No local model is configured. Select demo mode or configure an endpoint first.')
        j=uuid.uuid4().hex;now=time.time()
        value={'job_id':j,'request':request,'extension':extension}
        if agent:value['agent']=agent
        with self.lock:
            self.db.execute('INSERT INTO jobs(id,request,status,created,updated,error,extension,agent_json,initial_state) VALUES(?,?,?,?,?,?,?,?,?)',(j,request,'queued',now,now,None,int(extension),json.dumps(agent) if agent else None,json.dumps(value)));self.db.commit()
        self.event(j,'request',request)
        if background: threading.Thread(target=self.drive,args=(j,value),daemon=True).start()
        else:self.drive(j,value)
        return j
    def drive(self,j,value):
        with self.run_lock:
            with self.lock:
                row=self.db.execute('SELECT status FROM jobs WHERE id=?',(j,)).fetchone()
                if not row or row[0]=='cancelled':return
            self.status(j,'running')
            try:
                self.graph.invoke(value,self.cfg(j))
                snap=self.graph.get_state(self.cfg(j))
                if snap.next:
                    kind='plan_review' if 'plan_review' in snap.next else 'code_review' if 'code_review' in snap.next else 'result_review'
                    self.status(j,kind)
                else:
                    self.status(j,'needs_input' if snap.values.get('needs_input') else 'accepted' if snap.values.get('accepted') else 'changes_requested' if 'accepted' in snap.values else 'rejected')
            except Exception as e:
                self.status(j,'blocked',str(e)[:500]);self.event(j,'blocked',str(e)[:500])
    def get(self,j):
        with self.lock:
            row=self.db.execute('SELECT * FROM jobs WHERE id=?',(j,)).fetchone()
            if not row: raise KeyError(j)
            item=dict(row);item['events']=[dict(x) for x in self.db.execute('SELECT * FROM events WHERE job_id=? ORDER BY id',(j,))]
        snap=self.graph.get_state(self.cfg(j));s=dict(snap.values)
        item.update({k:s.get(k) for k in ['result','script','inputs','fingerprint','image','narrative','approved','draft_source','agent','plan','plan_fingerprint','needs_input']})
        if not item.get('agent') and item.get('agent_json'):item['agent']=json.loads(item['agent_json'])
        item.pop('initial_state',None);item.pop('agent_json',None)
        if s.get('result'):item['result_fingerprint']=digest(s['result'])
        return item
    def act(self,j,action,fingerprint='',background=True):
        with self.lock:
            job=self.get(j)
            if action=='cancel':
                if job['status'] in ['running']:raise ValueError('This short running job cannot be cancelled safely; wait for its next checkpoint')
                if job['status'] in ['accepted','cancelled','rejected','changes_requested']:raise ValueError('Job is already terminal')
                self.status(j,'cancelled');self.event(j,'cancel','Cancelled before further execution');return
            if action=='resume':
                if job['status'] not in ['blocked','interrupted']:raise ValueError('Only blocked or interrupted jobs can resume')
                row=self.db.execute('SELECT initial_state FROM jobs WHERE id=?',(j,)).fetchone()
                value=None if self.graph.get_state(self.cfg(j)).values else json.loads(row[0]) if row[0] else {'job_id':j,'request':job['request'],'extension':bool(job['extension'])}
            else:
                if job['status'] not in ['plan_review','code_review','result_review']:raise ValueError('Job is not awaiting review')
                expected=job['plan_fingerprint'] if job['status']=='plan_review' else job['fingerprint'] if job['status']=='code_review' else job['result_fingerprint']
                if fingerprint!=expected:raise ValueError('Stale approval; reload the current artifact')
                value=Command(resume={'approve':action=='approve','fingerprint':fingerprint})
            self.status(j,'queued')
        if background:threading.Thread(target=self.drive,args=(j,value),daemon=True).start()
        else:self.drive(j,value)
    def catalog(self):
        with self.lock:
            return {'skills':[dict(x) for x in self.db.execute('SELECT * FROM skills')],
                    'knowledge':[dict(x) for x in self.db.execute('SELECT * FROM knowledge')],
                    'plugin':{**json.loads((ROOT/'plugins/run-comparison.json').read_text()),'enabled':self.enabled()}}
    def close(self):self.db.close();self.cpconn.close()
