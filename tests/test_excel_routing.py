from test_workbench import eng
from test_agents import BASE

def test_uploaded_calculation_routes_to_reviewed_python(eng,monkeypatch):
    a=eng.agent_save({**BASE,'mode':'local'});cid=eng.conversation_create(a['id'])['id']
    uid=eng.upload_start(cid,{'name':'book.xlsx','size':0})['id'];eng.upload_finish(uid)
    monkeypatch.setattr(eng.gateway,'info',lambda:{'local':{'configured':True}})
    calls=[]
    def propose(*args):
        calls.append(args);return {'id':'draft','job_id':None}
    monkeypatch.setattr(eng,'plot_propose',propose)
    result=eng.conversation_send(cid,'What is the total sales and tax amount?')
    assert calls and result['python_task']['id']=='draft'
    assert eng.upload_list(cid)[0]['id']==uid
