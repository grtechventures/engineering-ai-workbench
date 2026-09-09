"""Saved, bounded agents. Models may select capabilities; server code grants authority."""
import json, re, time, uuid
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator

TOOLS={'legacy.export_series','analysis.compare_runs','python.reviewed_extension'}
CORE={'legacy.export_series','analysis.compare_runs'}
class AgentConfig(BaseModel):
    model_config=ConfigDict(extra='forbid')
    name:str=Field(min_length=1,max_length=70)
    purpose:str=Field(min_length=5,max_length=1500)
    mode:Literal['demo','local']='demo'
    project:Literal['demo-project']='demo-project'
    tools:list[Literal['legacy.export_series','analysis.compare_runs','python.reviewed_extension']]=Field(min_length=2,max_length=3)
    skill_ids:list[str]=Field(default_factory=list,max_length=20)
    plan_review:Literal[True]=True
    code_review:Literal[True]=True
    result_review:Literal[True]=True
    @field_validator('name','purpose')
    @classmethod
    def trim(cls,value):
        if not value.strip():raise ValueError('A nonempty value is required')
        return value.strip()
    @field_validator('tools')
    @classmethod
    def required_tools(cls,value):
        if len(set(value))!=len(value) or not CORE.issubset(value):raise ValueError('Agents require the exporter and released comparison tools')
        return value
class PlanChoice(BaseModel):
    model_config=ConfigDict(extra='forbid')
    workflow:Literal['compare','extension','clarify']
    reason:str=Field(min_length=1,max_length=800)
    skill_id:str|None=None

class AgentsMixin:
    def init_agents(self):
        self.db.execute('CREATE TABLE IF NOT EXISTS agents(id TEXT PRIMARY KEY, config TEXT, revision INTEGER, enabled INTEGER, created REAL, updated REAL)')
        columns={x[1] for x in self.db.execute('PRAGMA table_info(jobs)')}
        for name in ['agent_json','initial_state']:
            if name not in columns:self.db.execute(f'ALTER TABLE jobs ADD COLUMN {name} TEXT')
        self.db.commit()
    def list_agents(self):
        with self.lock:
            return [self.agent_dict(r) for r in self.db.execute('SELECT * FROM agents ORDER BY created')]
    def agent_dict(self,r):
        return {**json.loads(r['config']),'id':r['id'],'revision':r['revision'],'enabled':bool(r['enabled']),'created':r['created'],'updated':r['updated']}
    def agent_get(self,aid):
        with self.lock:row=self.db.execute('SELECT * FROM agents WHERE id=?',(aid,)).fetchone()
        if not row:raise KeyError(aid)
        return self.agent_dict(row)
    def agent_save(self,values,aid=None,revision=None):
        config=AgentConfig.model_validate(values).model_dump()
        with self.lock:
            for sid in config['skill_ids']:
                row=self.db.execute('SELECT status FROM skills WHERE id=?',(sid,)).fetchone()
                if not row or row[0]!='released':raise ValueError('Assign only currently released skills')
            now=time.time()
            if aid:
                current=self.agent_get(aid)
                if revision!=current['revision']:raise ValueError('Agent changed since editing; reload before saving')
                self.db.execute('UPDATE agents SET config=?,revision=revision+1,updated=? WHERE id=?',(json.dumps(config),now,aid))
            else:
                aid=uuid.uuid4().hex
                self.db.execute('INSERT INTO agents VALUES(?,?,1,1,?,?)',(aid,json.dumps(config),now,now))
            self.db.commit()
        return self.agent_get(aid)
    def agent_switch(self,aid,enabled):
        with self.lock:
            self.agent_get(aid)
            # Change the revision so disabling and re-enabling cannot restore stale authority.
            self.db.execute('UPDATE agents SET enabled=?,revision=revision+1,updated=? WHERE id=?',(int(enabled),time.time(),aid));self.db.commit()
        return self.agent_get(aid)
    def check_agent(self,s,workflow=None):
        a=s.get('agent')
        if not a:return
        current=self.agent_get(a['id'])
        if not current['enabled']:raise ValueError('This agent is disabled; no further execution is allowed')
        if current['revision']!=a['revision']:raise ValueError('Agent configuration changed. Start a new task with the current revision.')
        if a['project']!='demo-project':raise ValueError('Project is outside the allowed scope')
        needed=CORE|({'python.reviewed_extension'} if workflow=='extension' else set())
        if not needed.issubset(a['tools']):raise ValueError('The requested method is outside this agent’s allowed tools')
        skill=s.get('plan',{}).get('skill_id')
        if skill:
            if skill not in a['skill_ids']:raise ValueError('Plan selected an unassigned skill')
            row=self.db.execute('SELECT status,version FROM skills WHERE id=?',(skill,)).fetchone()
            if not row or row['status']!='released':raise ValueError('The selected skill is no longer released')
            if s.get('plan',{}).get('skill_version')!=row['version']:raise ValueError('Skill version changed; start a new task')
    def make_plan(self,s):
        a=s['agent'];self.check_agent(s)
        task=s['request']
        if a['mode']=='local':
            if not self.gateway.info()['local']['configured']:raise ValueError('Configure a local model before running this agent, or use demo mode')
            prompt=('Select exactly one supported operation for a synthetic run comparison. Return a JSON object with '
                    'workflow (compare, extension, or clarify), reason (short string), and optional skill_id. '
                    'compare compares Run A and Run B. extension additionally applies a centered five-sample moving-average to B minus A. '
                    'For any other operation or unclear request choose clarify. Do not invent capabilities. '
                    'Set skill_id to null: the server will select a compatible assigned skill after checking its method and release status. '
                    'Allowed tools: '+json.dumps(a['tools'])+'. '
                    'Agent purpose: '+a['purpose']+'. User task: '+task)
            text=self.gateway.complete('local',prompt,schema=PlanChoice.model_json_schema())
            if text.strip().startswith('```'):text='\n'.join(text.strip().splitlines()[1:-1])
            try:choice=PlanChoice.model_validate(json.loads(text))
            except Exception as exc:raise ValueError('Local model returned an invalid plan. No tools were executed; retry or use demo mode.') from exc
            planner='Configured local model'
        else:
            lower=task.lower()
            unsupported=re.search(r'\b(delete|remove|upload|email|send|download|stress|mesh|fft|fourier|frequency|regression|optimi[sz]e)\b',lower)
            if unsupported:workflow='clarify'
            elif re.search(r'\b(smooth|smoothing|moving.average)\b',lower):workflow='extension'
            elif re.search(r'\b(compare|comparison|difference|rmse|report)\b',lower):workflow='compare'
            else:workflow='clarify'
            reason={'compare':'Use the released run comparison for the two selected synthetic datasets.',
                    'extension':'Compare the runs, then propose a five-sample moving-average extension for code review.',
                    'clarify':'This demo supports run comparison and a five-sample moving-average difference. Please choose one of those tasks.'}[workflow]
            choice=PlanChoice(workflow=workflow,reason=reason)
            planner='Deterministic demo planner (no LLM)'
        if choice.workflow=='extension' and 'python.reviewed_extension' not in a['tools']:
            choice=PlanChoice(workflow='clarify',reason='This agent cannot propose Python extensions. Ask for a released comparison, or edit its allowed tools and start a new task.')
        plan=choice.model_dump();plan.update({'planner':planner,'agent_revision':a['revision'],'data_scope':'demo-project/read-only'})
        # Reuse an assigned compatible recipe, without granting it additional authority.
        if choice.workflow!='clarify':
            candidates=[choice.skill_id] if choice.skill_id else a['skill_ids']
            for sid in candidates:
                row=self.db.execute('SELECT * FROM skills WHERE id=?',(sid,)).fetchone()
                if sid not in a['skill_ids'] or not row or row['status']!='released':
                    if choice.skill_id:raise ValueError('Model selected an unassigned or unreleased skill')
                    continue
                extension=bool(self.get(row['job_id'])['extension']) if row['job_id'] else False
                if extension!=(choice.workflow=='extension'):
                    if choice.skill_id:raise ValueError('Selected skill is incompatible with the proposed method')
                    continue
                plan.update(skill_id=sid,skill_version=row['version'],skill_name=row['name']);break
            self.check_agent({**s,'plan':plan},choice.workflow)
        plan['steps']=['Export Run A and Run B through the C++ gateway','Run the released numerical comparison'] if choice.workflow!='clarify' else []
        if choice.workflow=='extension':plan['steps']+=['Draft Python and wait for exact-code approval','Execute in a pinned Docker container and validate against a reference']
        if plan['steps']:plan['steps']+=['Present the report for engineering acceptance']
        return plan
