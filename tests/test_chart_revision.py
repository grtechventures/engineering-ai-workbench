"""Runtime Python replaces the earlier hardcoded axis shortcut."""
import json
import pytest
from test_workbench import eng
from test_agents import BASE

@pytest.fixture
def runtime(eng,monkeypatch):
    a=eng.agent_save({**BASE,'mode':'local'});c=eng.conversation_create(a['id'])
    j=eng.create('Compare',background=False);eng.message_add(c['id'],'assistant','Comparison ready',j)
    monkeypatch.setenv('EWB_PLOT_IMAGE','sha256:test')
    monkeypatch.setattr(eng.gateway,'info',lambda:{'local':{'configured':True}})
    monkeypatch.setattr(eng.gateway,'complete',lambda *args,**kw:json.dumps({'title':'Statistics','summary':'Compute mean','code':"import json\njson.dump({'mean': 1},open('/outputs/result.json','w'))"}))
    return eng,c,j

def test_python_draft_does_not_execute_and_preserves_result(runtime):
    e,c,j=runtime;before=e.get(j)
    r=e.conversation_send(c['id'],'Add axes and mean lines',selected_job=j)
    p=r['python_task'];assert p['status']=='code_review'
    assert e.get(j)['result']==before['result']
    assert e.get(j)['status']=='result_review'

def test_selected_clarification_falls_back_to_result(runtime):
    e,c,j=runtime
    other=e.create('Compare',agent=e.agent_get(c['agent_id']),background=False)
    e.message_add(c['id'],'assistant','Pending task',other)
    p=e.plot_propose(c['id'],'Plot data',other)
    assert p['job_id']==j

def test_parent_revision_retains_snapshot_and_script(runtime):
    e,c,j=runtime;p=e.plot_propose(c['id'],'Calculate mean',j)
    q=e.plot_propose(c['id'],'Add standard deviation',parent_id=p['id'])
    assert q['parent_id']==p['id'] and q['data']==p['data']
    assert q['id']!=p['id'] and q['status']=='code_review'

def test_stale_approval_and_revoked_agent(runtime):
    e,c,j=runtime;p=e.plot_propose(c['id'],'Calculate mean',j)
    with pytest.raises(ValueError,match='stale'):e.plot_action(p['id'],'approve','wrong',False)
    a=e.agent_get(c['agent_id']);e.agent_save({**BASE,'mode':'local','purpose':'Changed purpose'},a['id'],a['revision'])
    with pytest.raises(ValueError):e.plot_action(p['id'],'approve',p['fingerprint'],False)

def test_runtime_results_and_no_duplicate_execution(runtime,monkeypatch):
    e,c,j=runtime;p=e.plot_propose(c['id'],'Calculate mean',j);calls=[]
    def worker(*args,**kwargs):calls.append(args);return None,{'mean':1},{'runtime':'Docker'}
    monkeypatch.setattr('backend.plotting.run_plot_script',worker)
    out=e.plot_action(p['id'],'approve',p['fingerprint'],False)
    assert out['status']=='result_review' and out['output']=={'mean':1}
    with pytest.raises(ValueError):e.plot_action(p['id'],'approve',p['fingerprint'],False)
    assert len(calls)==1
    assert e.plot_action(p['id'],'accept',p['fingerprint'])['status']=='accepted'

def test_cross_conversation_result_and_parent_denied(runtime):
    e,c,j=runtime;p=e.plot_propose(c['id'],'Calculate',j);other=e.conversation_create(c['agent_id'])
    with pytest.raises(ValueError):e.plot_propose(other['id'],'Calculate',j)
    with pytest.raises(ValueError):e.plot_propose(other['id'],'Calculate',parent_id=p['id'])

def test_invalid_python_is_not_a_proposal(runtime,monkeypatch):
    e,c,j=runtime
    monkeypatch.setattr(e.gateway,'complete',lambda *a,**k:json.dumps({'title':'Bad','summary':'Bad','code':'not valid python !'}))
    with pytest.raises(ValueError,match='valid Python'):e.plot_propose(c['id'],'Calculate',j)
    assert e.plot_list(c['id'])==[]

def test_worker_failure_is_visible_and_can_be_revised(runtime,monkeypatch):
    e,c,j=runtime;p=e.plot_propose(c['id'],'Calculate',j)
    def fail(*a,**kwargs):raise RuntimeError('Missing output')
    monkeypatch.setattr('backend.plotting.run_plot_script',fail)
    r=e.plot_action(p['id'],'approve',p['fingerprint'],False)
    assert r['status']=='failed' and 'Missing output' in r['error']
    q=e.plot_propose(c['id'],'Fix output',parent_id=p['id'])
    assert q['status']=='code_review'

def test_tool_registration_does_not_access_path(eng,tmp_path):
    path=tmp_path/'does-not-exist'
    eng.tool_register({'name':'Application','description':'Reference only','source_folder':str(path)})
    assert not path.exists() and eng.tool_registrations()[0]['source_folder']==str(path)

def test_task_without_existing_result_can_use_user_supplied_numbers(runtime):
    e,c,j=runtime;fresh=e.conversation_create(c['agent_id'])
    p=e.plot_propose(fresh['id'],'Calculate mean of 2, 4 and 6')
    assert p['job_id'] is None and p['data']=={} and p['status']=='code_review'
