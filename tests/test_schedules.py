from datetime import datetime,timezone
import pytest
from backend.schedules import ScheduleConfig,next_due,utc_occurrence
from backend.engine import Engine
from test_workbench import eng
from test_agents import BASE
from test_api import client

NOW=datetime(2030,1,1,tzinfo=timezone.utc).timestamp()

def setup_schedule(eng,frequency='daily',start='2030-01-01T00:01'):
    agent=eng.agent_save(BASE)
    j=eng.create('Compare',background=False)
    eng.act(j,'approve',eng.get(j)['result_fingerprint'],background=False)
    config={'name':'Daily comparison','source_job':j,'agent_id':agent['id'],'skill_id':'compare-runs',
            'frequency':frequency,'timezone':'UTC','start_local':start}
    return eng.schedule_create(config,now=NOW)

def activate(eng,s):return eng.schedule_action(s['id'],'approve',s['fingerprint'],now=NOW)

def test_proposal_and_stale_approval(eng):
    s=setup_schedule(eng)
    assert eng.scheduler_tick(NOW+60,background=False)==[]
    with pytest.raises(ValueError,match='Stale'):eng.schedule_action(s['id'],'approve','wrong')
    activate(eng,s)
    assert len(eng.scheduler_tick(NOW+60,background=False))==1
    assert eng.scheduler_tick(NOW+60,background=False)==[]

def test_fixed_recipe_runs_without_model_and_keeps_result_review(eng,monkeypatch):
    s=setup_schedule(eng);activate(eng,s)
    monkeypatch.setattr(eng.gateway,'complete',lambda *a,**k:pytest.fail('No model should replan the scheduled recipe'))
    jid=eng.scheduler_tick(NOW+60,background=False)[0]
    job=eng.get(jid)
    assert job['status']=='result_review' and job['result']['metrics']['samples']==101
    assert eng.schedule_get(s['id'])['runs'][0]['job_status']=='result_review'

def test_waiting_review_prevents_overlap(eng):
    s=setup_schedule(eng);activate(eng,s)
    jid=eng.scheduler_tick(NOW+60,background=False)[0]
    assert eng.scheduler_tick(NOW+86460,background=False)==[]
    assert eng.schedule_get(s['id'])['runs'][0]['outcome']=='skipped_overlap'
    eng.act(jid,'approve',eng.get(jid)['result_fingerprint'],background=False)
    assert len(eng.scheduler_tick(NOW+2*86400+60,background=False))==1

def test_missed_once_does_not_catch_up(eng):
    s=setup_schedule(eng,'once');activate(eng,s)
    assert eng.scheduler_tick(NOW+1000,background=False)==[]
    s=eng.schedule_get(s['id'])
    assert s['status']=='complete' and s['runs'][0]['outcome']=='missed'

def test_pause_resume_cancel(eng):
    s=setup_schedule(eng);activate(eng,s)
    eng.schedule_action(s['id'],'pause',s['fingerprint'])
    assert eng.scheduler_tick(NOW+60,background=False)==[]
    eng.schedule_action(s['id'],'resume',s['fingerprint'])
    eng.scheduler_tick(NOW+1000,background=False)
    assert eng.schedule_get(s['id'])['runs'][0]['outcome']=='missed'
    eng.schedule_action(s['id'],'cancel',s['fingerprint'])
    assert eng.scheduler_tick(NOW+86460,background=False)==[]

def test_changed_agent_pauses_for_new_approval(eng):
    s=setup_schedule(eng);activate(eng,s)
    a=s['approval']['agent'];eng.agent_save({**BASE,'purpose':'A revised purpose'},a['id'],a['revision'])
    assert eng.scheduler_tick(NOW+60,background=False)==[]
    assert eng.schedule_get(s['id'])['status']=='needs_review'

def test_retired_skill_and_plugin_disable(eng):
    s=setup_schedule(eng);activate(eng,s)
    eng.db.execute("UPDATE skills SET status='retired' WHERE id='compare-runs'");eng.db.commit()
    assert eng.scheduler_tick(NOW+60,background=False)==[]
    assert eng.schedule_get(s['id'])['status']=='needs_review'

def test_restart_recovers_schedule_without_duplicate(eng):
    s=setup_schedule(eng);activate(eng,s)
    restored=Engine(eng.data)
    try:
        ids=restored.scheduler_tick(NOW+60,background=False)
        assert len(ids)==1
        assert restored.scheduler_tick(NOW+60,background=False)==[]
    finally:restored.close()

def test_crash_after_atomic_dispatch_keeps_single_job(eng,monkeypatch):
    s=setup_schedule(eng);activate(eng,s)
    monkeypatch.setattr(eng,'drive',lambda *a:None)
    jid=eng.scheduler_tick(NOW+60,background=False)[0]
    restored=Engine(eng.data)
    try:
        assert restored.get(jid)['status']=='interrupted'
        assert restored.scheduler_tick(NOW+60,background=False)==[]
        restored.act(jid,'resume',background=False)
        assert restored.get(jid)['status']=='result_review'
    finally:restored.close()

def test_spring_gap_skipped_fall_fold_once():
    zone='America/Chicago'
    assert utc_occurrence(datetime(2030,3,10,2,30),zone) is None
    config={'start_local':'2030-03-09T02:30','timezone':zone,'frequency':'daily'}
    after=utc_occurrence(datetime(2030,3,9,2,30),zone)
    assert next_due(config,after)==utc_occurrence(datetime(2030,3,11,2,30),zone)
    config={'start_local':'2030-11-02T01:30','timezone':zone,'frequency':'daily'}
    first=utc_occurrence(datetime(2030,11,3,1,30),zone)
    assert next_due(config,first)==utc_occurrence(datetime(2030,11,4,1,30),zone)

def test_weekly_maintains_local_time():
    config={'start_local':'2030-03-03T09:00','timezone':'America/Chicago','frequency':'weekly'}
    first=utc_occurrence(datetime(2030,3,3,9),config['timezone'])
    second=next_due(config,first)
    assert second-first==7*86400-3600

def test_invalid_timezone_and_start(eng):
    s=setup_schedule(eng)
    with pytest.raises(ValueError):ScheduleConfig.model_validate({**s['config'],'timezone':'Not/AZone'})
    with pytest.raises(ValueError):eng.schedule_create({**s['config'],'start_local':'2020-01-01T00:00'},now=NOW)

def test_api_requires_explicit_schedule_review(client):
    c,m=client;s=setup_schedule(m.engine)
    assert c.get('/api/schedules').json()[0]['status']=='proposed'
    assert c.post('/api/schedules/'+s['id']+'/action',json={'action':'approve','fingerprint':'wrong'}).status_code==409
    # No actual activation here: fixture clock differs from the scheduler's live clock.
    assert c.post('/api/schedules/'+s['id']+'/action',json={'action':'cancel','fingerprint':s['fingerprint']}).json()['status']=='cancelled'

def test_timezone_package_fallback_for_windows():
    import zoneinfo
    previous=zoneinfo.TZPATH
    try:
        zoneinfo.reset_tzpath([]);zoneinfo.ZoneInfo.clear_cache()
        assert utc_occurrence(datetime(2030,1,1,9),'America/Chicago') is not None
    finally:
        zoneinfo.reset_tzpath(previous);zoneinfo.ZoneInfo.clear_cache()

def test_schedule_cannot_bypass_changed_permission_after_queue(eng,monkeypatch):
    s=setup_schedule(eng);activate(eng,s)
    original=eng.drive
    queued=[]
    monkeypatch.setattr(eng,'drive',lambda j,v:queued.append((j,v)))
    jid=eng.scheduler_tick(NOW+60,background=False)[0]
    eng.agent_switch(s['approval']['agent']['id'],False)
    original(*queued[0])
    assert eng.get(jid)['status']=='blocked' and eng.get(jid)['inputs'] is None

def test_unassigned_skill_schedule_rejected(eng):
    s=setup_schedule(eng)
    a=eng.agent_save({**BASE,'skill_ids':[]})
    with pytest.raises(ValueError,match='assigned'):eng.schedule_create({**s['config'],'agent_id':a['id']},now=NOW)

def test_extension_recipe_cannot_be_scheduled(eng):
    s=setup_schedule(eng)
    # A candidate derived from an extension is not an eligible scheduled method.
    j=eng.create('Smooth',extension=True,background=False)
    eng.db.execute("INSERT INTO skills VALUES('extension-skill','Extension','Example','released','1.0',?)",(j,));eng.db.commit()
    a=eng.agent_save({**BASE,'skill_ids':['extension-skill']})
    with pytest.raises(ValueError,match='without generated'):eng.schedule_create({**s['config'],'agent_id':a['id'],'skill_id':'extension-skill'},now=NOW)

def test_failed_enqueue_rolls_back_occurrence_and_next_due(eng):
    import sqlite3
    s=setup_schedule(eng);activate(eng,s)
    eng.db.execute("CREATE TRIGGER reject_enqueue BEFORE INSERT ON jobs BEGIN SELECT RAISE(ABORT,'simulated storage failure'); END");eng.db.commit()
    with pytest.raises(sqlite3.IntegrityError):eng.scheduler_tick(NOW+60,background=False)
    assert eng.schedule_get(s['id'])['runs']==[]
    assert eng.schedule_get(s['id'])['next_due']==NOW+60
    eng.db.execute('DROP TRIGGER reject_enqueue');eng.db.commit()
    assert len(eng.scheduler_tick(NOW+60,background=False))==1

def test_method_change_requires_replacement_schedule(eng,monkeypatch):
    s=setup_schedule(eng);activate(eng,s)
    original=eng.recipe
    def changed(config):
        recipe=original(config);recipe['code_hashes']['analysis.py']='new release';return recipe
    monkeypatch.setattr(eng,'recipe',changed)
    assert eng.scheduler_tick(NOW+60,background=False)==[]
    assert eng.schedule_get(s['id'])['status']=='needs_review'
