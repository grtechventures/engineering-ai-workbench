import json
import pytest
from test_workbench import eng
from test_api import client
from backend.agents import AgentConfig

BASE={'name':'Analysis Agent','purpose':'Compare synthetic runs and explain the results.','mode':'demo','project':'demo-project','tools':['legacy.export_series','analysis.compare_runs','python.reviewed_extension'],'skill_ids':['compare-runs'],'plan_review':True,'code_review':True,'result_review':True}

def test_agent_persistence_and_revision(eng):
    a=eng.agent_save(BASE)
    assert eng.agent_get(a['id'])['revision']==1
    b=eng.agent_save({**BASE,'name':'Updated'},a['id'],1)
    assert b['revision']==2
    with pytest.raises(ValueError,match='changed'):eng.agent_save(BASE,a['id'],1)

def test_agent_requires_plan_approval_before_export(eng):
    a=eng.agent_save(BASE);j=eng.create('Compare the runs',agent=a,background=False);job=eng.get(j)
    assert job['status']=='plan_review' and job['inputs'] is None
    assert job['plan']['skill_id']=='compare-runs'
    with pytest.raises(ValueError):eng.act(j,'approve','stale',background=False)
    eng.act(j,'approve',job['plan_fingerprint'],background=False)
    assert eng.get(j)['status']=='result_review'

def test_rejected_plan_does_not_read_data(eng):
    a=eng.agent_save(BASE);j=eng.create('Compare',agent=a,background=False)
    eng.act(j,'reject',eng.get(j)['plan_fingerprint'],background=False)
    assert eng.get(j)['status']=='rejected' and eng.get(j)['inputs'] is None

def test_agent_tool_scope_prevents_extension(eng):
    a=eng.agent_save({**BASE,'tools':BASE['tools'][:2]})
    j=eng.create('Smooth the difference',agent=a,background=False)
    assert eng.get(j)['status']=='needs_input' and eng.get(j)['inputs'] is None

def test_unsupported_task_does_not_run(eng):
    a=eng.agent_save(BASE);j=eng.create('Perform a Fourier analysis',agent=a,background=False)
    assert eng.get(j)['status']=='needs_input'

def test_agent_disable_and_reenable_invalidates_old_authority(eng):
    a=eng.agent_save(BASE);j=eng.create('Compare',agent=a,background=False)
    eng.agent_switch(a['id'],False);eng.agent_switch(a['id'],True)
    eng.act(j,'approve',eng.get(j)['plan_fingerprint'],background=False)
    assert eng.get(j)['status']=='blocked' and eng.get(j)['inputs'] is None

def test_agent_edit_invalidates_existing_plan(eng):
    a=eng.agent_save(BASE);j=eng.create('Compare',agent=a,background=False)
    eng.agent_save({**BASE,'purpose':'New purpose'},a['id'],1)
    eng.act(j,'approve',eng.get(j)['plan_fingerprint'],background=False)
    assert eng.get(j)['status']=='blocked'

def test_retired_assigned_skill_blocks_plan_execution(eng):
    a=eng.agent_save(BASE);j=eng.create('Compare',agent=a,background=False)
    eng.db.execute("UPDATE skills SET status='retired' WHERE id='compare-runs'");eng.db.commit()
    eng.act(j,'approve',eng.get(j)['plan_fingerprint'],background=False)
    assert eng.get(j)['status']=='blocked'

def test_review_and_project_cannot_be_weakened():
    with pytest.raises(ValueError):AgentConfig.model_validate({**BASE,'code_review':False})
    with pytest.raises(ValueError):AgentConfig.model_validate({**BASE,'project':'someone-else'})
    with pytest.raises(ValueError):AgentConfig.model_validate({**BASE,'tools':['shell']})

def test_local_agent_does_not_silently_fallback(eng):
    a=eng.agent_save({**BASE,'mode':'local'})
    with pytest.raises(ValueError,match='No local'):eng.create('Compare',agent=a,background=False)

def test_local_plan_output_checked_against_capabilities(eng,monkeypatch):
    a=eng.agent_save({**BASE,'mode':'local','tools':BASE['tools'][:2]})
    monkeypatch.setattr(eng.gateway,'info',lambda:{'local':{'configured':True}})
    monkeypatch.setattr(eng.gateway,'complete',lambda *a,**k:json.dumps({'workflow':'extension','reason':'Smooth'}))
    j=eng.create('Smooth',agent=a,background=False)
    assert eng.get(j)['status']=='needs_input'

def test_conversation_greeting_is_not_an_action(eng):
    a=eng.agent_save(BASE);c=eng.conversation_create(a['id']);r=eng.conversation_send(c['id'],'Hello')
    assert r['job_id'] is None and len(r['conversation']['messages'])==2
    assert eng.db.execute('SELECT count(*) FROM jobs').fetchone()[0]==0

def test_conversation_followup_explains_existing_result(eng,monkeypatch):
    a=eng.agent_save(BASE);c=eng.conversation_create(a['id'])
    j=eng.create('Compare',agent=a,background=False)
    eng.act(j,'approve',eng.get(j)['plan_fingerprint'],background=False)
    eng.message_add(c['id'],'assistant','Comparison prepared',j)
    r=eng.conversation_send(c['id'],'What does RMSE mean?')
    assert r['job_id'] is None and 'RMSE' in r['conversation']['messages'][-1]['content']

def test_local_conversation_sends_only_to_local_gateway(eng,monkeypatch):
    a=eng.agent_save({**BASE,'mode':'local'});c=eng.conversation_create(a['id']);calls=[]
    monkeypatch.setattr(eng.gateway,'info',lambda:{'local':{'configured':True}})
    def complete(*args,**kwargs):calls.append((args,kwargs));return '{"action":"reply","response":"Hello"}'
    monkeypatch.setattr(eng.gateway,'complete',complete)
    r=eng.conversation_send(c['id'],'Explain comparison methods')
    assert r['job_id'] is None and calls[0][0][0]=='local'

def test_agent_api_create_update_and_disable(client):
    c,m=client;r=c.post('/api/agents',json={'config':BASE});assert r.status_code==200
    a=r.json();assert c.get('/api/bootstrap').json()['agents'][0]['id']==a['id']
    assert c.post('/api/agents/'+a['id'],json={'config':{**BASE,'name':'Revised'},'revision':1}).status_code==200
    assert c.post('/api/agents/'+a['id'],json={'config':BASE,'revision':1}).status_code==409
    assert c.post('/api/agents/'+a['id']+'/enabled',json={'enabled':False}).status_code==200
    assert c.post('/api/agents/'+a['id']+'/run',json={'request':'Compare'}).status_code==409

def test_conversation_api_persistence(client):
    c,m=client;a=c.post('/api/agents',json={'config':BASE}).json()
    chat=c.post('/api/conversations',json={'agent_id':a['id']}).json()
    r=c.post('/api/conversations/'+chat['id']+'/messages',json={'request':'Hello'})
    assert r.status_code==200 and len(r.json()['conversation']['messages'])==2
    assert c.get('/api/conversations/'+chat['id']).json()['title']=='Hello'

def test_invalid_model_conversation_dispatches_nothing(eng,monkeypatch):
    a=eng.agent_save({**BASE,'mode':'local'});c=eng.conversation_create(a['id'])
    monkeypatch.setattr(eng.gateway,'info',lambda:{'local':{'configured':True}})
    monkeypatch.setattr(eng.gateway,'complete',lambda *a,**k:'{"action":"shell","response":"Executing"}')
    with pytest.raises(ValueError,match='invalid response'):eng.conversation_send(c['id'],'Compare')
    assert eng.db.execute('SELECT count(*) FROM jobs').fetchone()[0]==0

def test_agent_plan_review_survives_restart(eng):
    from backend.engine import Engine
    a=eng.agent_save(BASE);c=eng.conversation_create(a['id'])
    eng.message_add(c['id'],'user','Compare')
    j=eng.create('Compare',agent=a,background=False)
    restored=Engine(eng.data)
    try:
        assert restored.conversation_get(c['id'])['messages'][0]['content']=='Compare'
        restored.act(j,'approve',restored.get(j)['plan_fingerprint'],background=False)
        assert restored.get(j)['status']=='result_review'
    finally:restored.close()
