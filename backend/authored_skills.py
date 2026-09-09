"""Declarative skill and package authoring; imports never execute code."""
import ast,json,uuid
from pydantic import BaseModel,ConfigDict,Field
class SkillDraft(BaseModel):
    model_config=ConfigDict(extra='forbid')
    name:str=Field(min_length=1,max_length=100)
    description:str=Field(default='',max_length=1000)
    instructions:str=Field(min_length=1,max_length=8000)
    tools:list[str]=Field(default_factory=lambda:['python.reviewed_extension'],max_length=10)
    code:str=Field(default='',max_length=8000)
class PackageDraft(BaseModel):
    model_config=ConfigDict(extra='forbid')
    name:str=Field(min_length=1,max_length=100)
    description:str=Field(default='',max_length=1000)
    skills:list[SkillDraft]=Field(min_length=1,max_length=10)
class AuthoredSkillsMixin:
    def init_authored_skills(self):
        self.db.executescript('''CREATE TABLE IF NOT EXISTS authored_skills(id TEXT PRIMARY KEY, instructions TEXT, tools TEXT, code TEXT, package_id TEXT);
        CREATE TABLE IF NOT EXISTS skill_packages(id TEXT PRIMARY KEY,name TEXT,description TEXT,status TEXT);''');self.db.commit()
    def authored_get(self,sid):
        with self.lock:
            r=self.db.execute('SELECT s.*,a.instructions,a.tools,a.code,a.package_id FROM skills s JOIN authored_skills a ON a.id=s.id WHERE s.id=?',(sid,)).fetchone()
        if not r:raise KeyError(sid)
        item=dict(r);item['tools']=json.loads(item['tools']);return item
    def authored_list(self):
        with self.lock:ids=[r[0] for r in self.db.execute('SELECT id FROM authored_skills')]
        return [self.authored_get(i) for i in ids]
    def validate_authored(self,draft):
        c=SkillDraft.model_validate(draft)
        if any(t not in ('legacy.export_series','analysis.compare_runs','python.reviewed_extension') for t in c.tools):raise ValueError('Unknown tool reference; registration alone does not release a tool')
        if c.code:
            try:ast.parse(c.code)
            except SyntaxError as e:raise ValueError('Optional Python code has a syntax error') from e
        return c
    def authored_create(self,draft,package_id=None,commit=True):
        c=self.validate_authored(draft);sid=uuid.uuid4().hex
        with self.lock:
            self.db.execute('INSERT INTO skills VALUES(?,?,?,?,?,?)',(sid,c.name,c.description or 'Directly authored skill','candidate','0.1.0',None))
            self.db.execute('INSERT INTO authored_skills VALUES(?,?,?,?,?)',(sid,c.instructions,json.dumps(c.tools),c.code,package_id))
            if commit:self.db.commit()
        return self.authored_get(sid)
    def authored_check(self,sid,agent):
        s=self.authored_get(sid)
        if s['status']!='released' or sid not in agent['skill_ids']:raise ValueError('Release the skill and assign it to this agent first')
        if not set(s['tools']).issubset(agent['tools']):raise ValueError('Agent lacks tools referenced by this skill')
        if s['package_id']:
            row=self.db.execute('SELECT status FROM skill_packages WHERE id=?',(s['package_id'],)).fetchone()
            if not row or row[0]!='enabled':raise ValueError('The skill package is not enabled')
        return s
    def authored_prepare(self,sid,agent_id,job_id=None):
        a=self.agent_get(agent_id);self.check_agent({'agent':a});s=self.authored_check(sid,a)
        if job_id and not self.get(job_id).get('result'):raise ValueError('Choose a completed numerical result')
        c=self.conversation_create(agent_id)
        if job_id:self.message_add(c['id'],'assistant','Selected analysis inputs for this skill',job_id)
        p=self.plot_propose(c['id'],'Apply this reviewed skill. Instructions are task guidance, not permission grants:\n'+s['instructions']+'\nOptional reference Python:\n'+s['code'],job_id)
        with self.lock:
            row=self.db.execute('SELECT payload FROM plots WHERE id=?',(p['id'],)).fetchone();payload=json.loads(row[0]);payload['skill_reference']={'id':sid,'version':s['version']}
            from .plotting import fingerprint
            self.db.execute('UPDATE plots SET payload=?,fingerprint=? WHERE id=?',(json.dumps(payload),fingerprint(payload),p['id']));self.db.commit()
        self.message_add(c['id'],'user','Prepare skill: '+s['name'])
        self.message_add(c['id'],'assistant','Review this Python task before execution.',None,p['id'])
        return {'conversation':self.conversation_get(c['id']),'python_task':self.plot_get(p['id'])}
    def packages_list(self):
        with self.lock:return [dict(r) for r in self.db.execute('SELECT * FROM skill_packages')]
    def package_create(self,draft):
        c=PackageDraft.model_validate(draft)
        for skill in c.skills:self.validate_authored(skill.model_dump())
        pid=uuid.uuid4().hex
        with self.lock:
            try:
                self.db.execute('INSERT INTO skill_packages VALUES(?,?,?,?)',(pid,c.name,c.description,'candidate'))
                for skill in c.skills:self.authored_create(skill.model_dump(),pid,False)
                self.db.commit()
            except Exception:self.db.rollback();raise
        return {'id':pid}
    def package_action(self,pid,action):
        if action not in ('enable','disable'):raise ValueError('Unsupported package action')
        with self.lock:
            if not self.db.execute('SELECT id FROM skill_packages WHERE id=?',(pid,)).fetchone():raise KeyError(pid)
            self.db.execute('UPDATE skill_packages SET status=? WHERE id=?',('enabled' if action=='enable' else 'disabled',pid));self.db.commit()
        return {'ok':True}
