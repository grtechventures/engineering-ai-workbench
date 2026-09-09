import importlib, json, os, subprocess
import pytest
from fastapi.testclient import TestClient
from backend.engine import Engine, ROOT

@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setenv('EWB_DATA_DIR',str(tmp_path))
    import backend.app as module
    previous=module.engine
    module.engine=Engine(tmp_path)
    subprocess.run([str(ROOT/'legacy/build'/('engineering-demo.exe' if os.name=='nt' else 'engineering-demo')),'seed',str(tmp_path)],check=True)
    with TestClient(module.app) as c:
        token=c.get('/api/bootstrap').json()['token']
        c.headers.update({'X-Workbench-Token':token})
        yield c,module
    module.engine.close();module.engine=previous

def test_request_boundary_and_unknown_fields(client):
    c,m=client
    assert c.post('/api/knowledge',json={'text':'note'},headers={'X-Workbench-Token':'wrong'}).status_code==403
    assert c.post('/api/knowledge',json={'text':'note'},headers={'Origin':'https://untrusted.example'}).status_code==403
    assert c.get('/api/bootstrap',headers={'Host':'untrusted.example'}).status_code==403
    assert c.post('/api/general-reasoning',json={'topic':'rmse','engineering_data':'private'}).status_code==422

def test_frontier_disabled_before_any_model_call(client,monkeypatch):
    c,m=client;calls=[]
    def complete(*args,**kwargs):calls.append((args,kwargs));return 'Public explanation'
    monkeypatch.setattr(m.engine.gateway,'complete',complete)
    r=c.post('/api/general-reasoning',json={'topic':'rmse'})
    assert r.status_code==409 and calls==[]

def test_skill_release_and_knowledge_lifecycle(client):
    c,m=client;j=m.engine.create('Comparison',background=False)
    assert c.post('/api/skills',json={'job_id':j,'name':'Team review'}).status_code==409
    m.engine.act(j,'approve',m.engine.get(j)['result_fingerprint'],background=False)
    sid=c.post('/api/skills',json={'job_id':j,'name':'Team review'}).json()['id']
    assert c.post('/api/skills/'+sid+'/run',json={}).status_code==409
    assert c.post('/api/skills/'+sid+'/decision',json={'action':'approve'}).status_code==200
    assert c.post('/api/skills/'+sid+'/decision',json={'action':'retire'}).status_code==200
    assert c.post('/api/skills/'+sid+'/run',json={}).status_code==409
    mid=c.post('/api/knowledge',json={'text':'Report both metrics','scope':'project'}).json()['id']
    assert c.post('/api/knowledge/'+mid+'/decision',json={'action':'approve'}).status_code==200
    assert c.get('/api/bootstrap').json()['catalog']['knowledge'][0]['status']=='approved'
    assert c.post('/api/knowledge/'+mid+'/decision',json={'action':'retire'}).status_code==200

def test_report_contains_real_provenance(client):
    c,m=client;j=m.engine.create('Compare',background=False)
    r=c.get('/api/jobs/'+j+'/report')
    assert r.status_code==200
    p=r.json();assert p['status']=='result_review' and p['inputs']['a']['source_hash']
    assert p['result']['metrics']['samples']==101

def test_source_is_fixed_read_only_catalog(client):
    c,m=client
    assert len(c.get('/api/source').json()['files'])==2
    assert c.get('/api/source/../../.env').status_code==404
