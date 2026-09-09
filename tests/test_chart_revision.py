from test_workbench import eng
from test_agents import BASE

def test_axis_revision_preserves_result_and_review(eng,monkeypatch):
    a=eng.agent_save(BASE);c=eng.conversation_create(a['id'])
    j=eng.create('Compare',background=False)
    eng.message_add(c['id'],'assistant','Comparison ready',j)
    before=eng.get(j)
    monkeypatch.setattr(eng.gateway,'complete',lambda *a,**k: (_ for _ in ()).throw(AssertionError('No model needed')))
    r=eng.conversation_send(c['id'],'Can you add X and Y axis lines to the plot?')
    after=eng.get(j)
    assert r['job_id']==j
    assert after['result']==before['result']
    assert after['result_fingerprint']==before['result_fingerprint']
    assert after['status']=='result_review'
    assert any(e['stage']=='chart_axes' for e in after['events'])
    assert 'Added X and Y' in r['conversation']['messages'][-1]['content']

def test_axis_request_without_result_creates_no_artifact(eng):
    a=eng.agent_save(BASE);c=eng.conversation_create(a['id'])
    r=eng.conversation_send(c['id'],'Add X and Y axis lines')
    assert r['job_id'] is None
    assert 'No chart was changed' in r['conversation']['messages'][-1]['content']
