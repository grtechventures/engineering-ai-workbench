import json
import pytest
from test_workbench import eng
from test_api import client
from test_agents import BASE
from backend.workspace import FileArtifacts
from backend.engine import Engine
from backend.analysis import smoothing_study


def accepted(eng):
    j=eng.create('Compare runs',background=False)
    eng.act(j,'approve',eng.get(j)['result_fingerprint'],background=False)
    return j


def test_only_approved_memory_retrieved_with_provenance(eng):
    mid=eng.knowledge_propose('RMSE uses arbitrary units',source='Method handbook')['id']
    assert eng.knowledge_search('RMSE')==[]
    eng.knowledge_decide(mid,'approve',1)
    assert eng.knowledge_search('RMSE')[0]['source']=='Method handbook'
    assert eng.knowledge_search('unrelated')==[]
    with pytest.raises(ValueError):eng.knowledge_decide(mid,'retire',1)
    eng.knowledge_decide(mid,'retire',2)
    assert eng.knowledge_search('RMSE')==[]
    with pytest.raises(ValueError):eng.knowledge_decide(mid,'approve',3)


def test_retrieval_is_local_and_survives_restart(eng,monkeypatch):
    mid=eng.knowledge_propose('RMSE reference convention',source='Accepted method')['id'];eng.knowledge_decide(mid,'approve')
    agent=eng.agent_save({**BASE,'mode':'local'});c=eng.conversation_create(agent['id']);calls=[]
    monkeypatch.setattr(eng.gateway,'info',lambda:{'local':{'configured':True}})
    def complete(route,prompt,**kw):
        calls.append((route,prompt));return json.dumps({'action':'reply','response':'See the reviewed convention.'})
    monkeypatch.setattr(eng.gateway,'complete',complete)
    eng.conversation_send(c['id'],'Explain the RMSE convention')
    assert calls[0][0]=='local' and 'Accepted method' in calls[0][1]
    restored=Engine(eng.data)
    try:assert restored.conversation_get(c['id'])['references'][0]['refs'][0]['id']==mid
    finally:restored.close()


def test_snapshot_replay_survives_missing_original(eng):
    j=accepted(eng);old=eng.get(j)['result']
    (eng.data/'run-a.ewb').unlink()
    child=eng.replay(j,background=False)['id']
    assert eng.get(child)['status']=='result_review' and eng.get(child)['result']==old
    assert eng.evidence(child)['lineage']['parent_id']==j
    current=eng.replay(j,mode='current',background=False)['id']
    assert eng.get(current)['status']=='blocked'


def test_replay_agent_requires_new_plan_and_current_permissions(eng):
    a=eng.agent_save(BASE);j=eng.create('Compare',agent=a,background=False)
    eng.act(j,'approve',eng.get(j)['plan_fingerprint'],background=False)
    child=eng.replay(j,background=False)['id']
    assert eng.get(child)['status']=='plan_review' and eng.get(child)['inputs'] is None
    eng.agent_switch(a['id'],False)
    eng.act(child,'approve',eng.get(child)['plan_fingerprint'],background=False)
    assert eng.get(child)['status']=='blocked'


def test_artifact_hash_path_and_tamper_checks(tmp_path):
    store=FileArtifacts(tmp_path);key=store.put({'value':42})
    assert store.get(key)=={'value':42} and store.put({'value':42})==key
    with pytest.raises(ValueError):store.get('../credentials')
    (tmp_path/(key+'.json')).write_text('{}')
    with pytest.raises(ValueError):store.get(key)


def test_evidence_persisted_without_download(eng):
    j=accepted(eng)
    rows=eng.db.execute('SELECT artifact_id FROM evidence_objects WHERE job_id=?',(j,)).fetchall()
    assert len(rows)==2 # pending review and accepted snapshots
    assert any(eng.artifacts.get(r[0])['status']=='accepted' for r in rows)


def test_study_approval_bounds_reference_and_restart(eng):
    j=accepted(eng)
    for windows in [[2],[1,1],[23],list(range(1,19,2))]:
        with pytest.raises(ValueError):eng.study_create(j,windows,5)
    s=eng.study_create(j,[1,3,5],5)
    assert s['status']=='plan_review' and s['result'] is None
    with pytest.raises(ValueError):eng.study_act(s['id'],'approve','stale')
    restored=Engine(eng.data)
    try:
        out=restored.study_act(s['id'],'approve',s['fingerprint'])
        assert out['status']=='result_review' and out['result']['stop_reason']=='completed'
        assert out['result']['trials'][0]['distortion_rmse']==0
        assert all(t['reference_passed'] for t in out['result']['trials'])
        with pytest.raises(ValueError):restored.study_act(s['id'],'approve',s['fingerprint'])
        assert restored.study_act(s['id'],'approve',out['fingerprint'])['status']=='accepted'
        with pytest.raises(ValueError):restored.study_act(s['id'],'approve',out['fingerprint'])
    finally:restored.close()


def test_study_cancellation_and_plugin_revocation(eng):
    j=accepted(eng);s=eng.study_create(j,[1,5],5)
    assert eng.study_act(s['id'],'cancel',s['fingerprint'])['result'] is None
    s=eng.study_create(j,[1,5],5)
    eng.db.execute("UPDATE settings SET value='disabled' WHERE key='plugin'");eng.db.commit()
    with pytest.raises(ValueError):eng.study_act(s['id'],'approve',s['fingerprint'])


def test_study_budget_is_a_stop_condition(eng,monkeypatch):
    j=accepted(eng);ticks=iter([0,0,100,101])
    monkeypatch.setattr('time.monotonic',lambda:next(ticks))
    result=smoothing_study(eng.get(j)['inputs'],[1,3,5],1)
    assert len(result['trials'])==1 and result['stop_reason']=='time_budget'


def test_new_api_paths_and_storage(client):
    c,m=client;j=accepted(m.engine)
    note=c.post('/api/knowledge',json={'text':'RMSE method','source':'Accepted run','job_id':j}).json()['id']
    assert c.post('/api/knowledge/'+note+'/decision',json={'action':'approve','revision':1}).status_code==200
    assert c.get('/api/knowledge/search?q=RMSE').json()[0]['id']==note
    assert c.get('/api/bootstrap').json()['storage']['provider']=='filesystem'
    s=c.post('/api/studies',json={'job_id':j,'windows':[1,5],'budget_seconds':5}).json()
    assert c.post('/api/studies/'+s['id']+'/action',json={'action':'approve','fingerprint':s['fingerprint']}).status_code==200
    assert c.get('/api/studies/'+s['id']+'/report').json()['result']['trials'][0]['window']==1
    assert len(c.get('/api/studies').json())==1
