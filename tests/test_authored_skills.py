import json
import pytest
from test_workbench import eng
from test_api import client
from test_agents import BASE
DRAFT={'name':'Statistics','instructions':'Calculate mean of 2, 4, 6','tools':['python.reviewed_extension']}

def release(e,sid):
    e.db.execute("UPDATE skills SET status='released' WHERE id=?",(sid,));e.db.commit()

def test_create_without_prior_job(eng):
    s=eng.authored_create(DRAFT)
    assert s['status']=='candidate' and s['job_id'] is None
    assert eng.db.execute('select count(*) from jobs').fetchone()[0]==0

def test_import_cannot_grant_unknown_tools_or_run_code(eng):
    with pytest.raises(ValueError):eng.authored_create({**DRAFT,'tools':['shell.execute']})
    with pytest.raises(ValueError):eng.authored_create({**DRAFT,'code':'invalid python !'})
    assert eng.authored_list()==[]

def test_package_validates_atomically_and_supports_multiple_skills(eng):
    with pytest.raises(ValueError):eng.package_create({'name':'Bad','skills':[DRAFT,{**DRAFT,'tools':['bad']}]})
    assert eng.packages_list()==[] and eng.authored_list()==[]
    eng.package_create({'name':'Methods','skills':[DRAFT,{**DRAFT,'name':'Another'}]})
    assert len(eng.authored_list())==2

def test_release_assignment_and_package_are_required(eng):
    p=eng.package_create({'name':'Methods','skills':[DRAFT]});s=eng.authored_list()[0];release(eng,s['id'])
    a=eng.agent_save({**BASE,'skill_ids':[s['id']]})
    with pytest.raises(ValueError,match='package'):eng.authored_check(s['id'],a)
    eng.package_action(p['id'],'enable');assert eng.authored_check(s['id'],a)
    eng.package_action(p['id'],'disable')
    with pytest.raises(ValueError):eng.authored_check(s['id'],a)

def test_prepared_skill_revocation_blocks_code_approval(eng,monkeypatch):
    s=eng.authored_create(DRAFT);release(eng,s['id'])
    a=eng.agent_save({**BASE,'mode':'local','skill_ids':[s['id']]})
    monkeypatch.setenv('EWB_PLOT_IMAGE','sha256:test')
    monkeypatch.setattr(eng.gateway,'complete',lambda *args,**kwargs:json.dumps({'title':'Mean','summary':'Calculate mean','code':'import json\nprint(4)'}))
    r=eng.authored_prepare(s['id'],a['id']);p=r['python_task']
    assert p['status']=='code_review' and p['skill_reference']['id']==s['id']
    eng.db.execute("UPDATE skills SET status='retired' WHERE id=?",(s['id'],));eng.db.commit()
    with pytest.raises(ValueError):eng.plot_action(p['id'],'approve',p['fingerprint'],False)

def test_authored_skill_cannot_silently_run_comparison(client):
    c,m=client;s=c.post('/api/authored-skills',json=DRAFT).json()
    assert c.post('/api/skills/'+s['id']+'/decision',json={'action':'approve'}).status_code==200
    assert c.post('/api/skills/'+s['id']+'/run',json={}).status_code==409

def test_tools_accept_multiple_registrations(eng):
    for n in ('One','Two','Three'):eng.tool_register({'name':n,'description':'Reference'})
    assert len(eng.tool_registrations())==3
