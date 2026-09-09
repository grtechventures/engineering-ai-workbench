"""Local configuration UI; endpoint policies remain independent and enforced."""
import json, os, re, subprocess, uuid
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from .network_policy import validate_model_url
from .models import ModelGateway
from .worker import local_docker_command
class Connection(BaseModel):
    model_config=ConfigDict(extra='forbid')
    name:str=Field(min_length=1,max_length=100)
    provider:Literal['Ollama','LM Studio','OpenAI-compatible']='Ollama'
    url:str=Field(min_length=1,max_length=1000)
    model:str=Field(min_length=1,max_length=150)
class Runtime(BaseModel):
    model_config=ConfigDict(extra='forbid')
    comparison_image:str
    python_image:str
class ConfigurationMixin:
    def init_configuration(self):
        self.db.execute('CREATE TABLE IF NOT EXISTS connections(id TEXT PRIMARY KEY,payload TEXT)')
        row=self.db.execute("SELECT value FROM settings WHERE key='runtime_config'").fetchone()
        if row:
            d=json.loads(row[0]);os.environ['EWB_WORKER_IMAGE']=d['comparison_image'];os.environ['EWB_PLOT_IMAGE']=d['python_image']
        row=self.db.execute("SELECT value FROM settings WHERE key='active_connection'").fetchone()
        if row:
            p=self.db.execute('SELECT payload FROM connections WHERE id=?',(row[0],)).fetchone()
            if p:
                d=json.loads(p[0]);self.gateway.local_url=validate_model_url(d['url']);self.gateway.local_model=d['model']
        self.db.commit()
    def configuration(self):
        with self.lock:
            active=self.db.execute("SELECT value FROM settings WHERE key='active_connection'").fetchone()
            return {'connections':[dict(id=r['id'],**json.loads(r['payload'])) for r in self.db.execute('SELECT * FROM connections')], 'active':active[0] if active else None,'current_url':self.gateway.local_url,'current_model':self.gateway.local_model,'comparison_image':os.getenv('EWB_WORKER_IMAGE',''),'python_image':os.getenv('EWB_PLOT_IMAGE',''),'resource_roots':json.loads(os.getenv('EWB_RESOURCE_ROOTS','[]')),'approved_model_ips':os.getenv('EWB_APPROVED_MODEL_IPS',''),'discovery_disabled':self.db.execute("SELECT value FROM settings WHERE key='discovery_disabled'").fetchone() is not None}
    def connection_save(self,d,cid=None):
        c=Connection.model_validate(d);c.url=validate_model_url(c.url)
        with self.lock:
            if cid and not self.db.execute('SELECT 1 FROM connections WHERE id=?',(cid,)).fetchone():raise ValueError('Connection not found')
            cid=cid or uuid.uuid4().hex
            self.db.execute('INSERT OR REPLACE INTO connections VALUES(?,?)',(cid,c.model_dump_json()));self.db.commit()
        return {'id':cid}
    def connection_action(self,cid,action):
        with self.lock:
            row=self.db.execute('SELECT payload FROM connections WHERE id=?',(cid,)).fetchone()
            if not row:raise ValueError('Connection not found')
            d=json.loads(row[0]);url=validate_model_url(d['url'])
            if action=='activate':
                gateway=ModelGateway();gateway.local_url=url;gateway.local_model=d['model'];self.gateway=gateway
                self.db.execute("INSERT OR REPLACE INTO settings VALUES('active_connection',?)",(cid,));self.db.commit();return {'message':'Active model changed for subsequent requests. All local-mode agents use this connection.'}
        gateway=ModelGateway();gateway.local_url=url;gateway.local_model=d['model']
        gateway.complete('local','Reply with OK. This is a connection test; no engineering data is included.',max_tokens=20)
        return {'message':'Model returned a response successfully.'}
    def runtime_save(self,d):
        c=Runtime.model_validate(d)
        for image in (c.comparison_image,c.python_image):
            if not re.fullmatch(r'sha256:[0-9a-f]{64}',image):raise ValueError('Use a full pinned local image ID')
        command,env=local_docker_command()
        for image in (c.comparison_image,c.python_image):
            subprocess.run(command+['image','inspect',image],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True,timeout=10)
        with self.lock:
            self.db.execute("INSERT OR REPLACE INTO settings VALUES('runtime_config',?)",(c.model_dump_json(),));self.db.commit()
            os.environ['EWB_WORKER_IMAGE']=c.comparison_image;os.environ['EWB_PLOT_IMAGE']=c.python_image
        return {'message':'Pinned local images saved. Existing script approvals may require renewal.'}
    def runtime_test(self):
        command,env=local_docker_command()
        subprocess.run(command+['info'],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True,timeout=10)
        return {'message':'Local Docker daemon responded. Save images to verify their availability; this test does not execute analysis code.'}
    def discovery_disable(self):
        with self.lock:
            self.db.execute("INSERT OR REPLACE INTO settings VALUES('discovery_disabled','1')");self.db.commit()
        return {'message':'Resource inspection disabled. Administrator intervention is required to restore access.'}
