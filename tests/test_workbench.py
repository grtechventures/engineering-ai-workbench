import json, math, os, subprocess
import pytest
from backend.engine import Engine, ROOT
from backend.analysis import compare
from backend.models import ModelGateway
@pytest.fixture
def eng(tmp_path):
    exe=ROOT/'legacy/build'/('engineering-demo.exe' if os.name=='nt' else 'engineering-demo')
    subprocess.run([str(exe),'seed',str(tmp_path)],check=True)
    e=Engine(tmp_path)
    yield e
    e.close()
def test_binary_reader_and_actual_numerical_result(eng):
    j=eng.create('Compare runs',background=False);job=eng.get(j)
    assert job['status']=='result_review'
    assert job['result']['metrics']['samples']==101
    expected=[.025*(math.sin(x/14)*.8+.003*x)+.035*math.exp(-((x-67)/9)**2) for x in range(101)]
    assert job['result']['metrics']['max_abs_delta']==pytest.approx(max(map(abs,expected)))
    assert job['result']['metrics']['rmse']==pytest.approx(math.sqrt(sum(x*x for x in expected)/101))
    assert job['inputs']['a']['source_hash']!=job['inputs']['b']['source_hash']
def test_result_approval_stale_and_duplicate_protection(eng):
    j=eng.create('Compare',background=False);job=eng.get(j)
    with pytest.raises(ValueError,match='Stale'):eng.act(j,'approve','stale',background=False)
    eng.act(j,'approve',job['result_fingerprint'],background=False)
    assert eng.get(j)['status']=='accepted'
    with pytest.raises(ValueError,match='not awaiting'):eng.act(j,'approve',job['result_fingerprint'],background=False)
def test_script_cannot_execute_before_approval(eng,monkeypatch):
    calls=[];monkeypatch.setattr('backend.engine.run_script',lambda *args:calls.append(args))
    j=eng.create('Moving average',extension=True,background=False);job=eng.get(j)
    assert job['status']=='code_review'
    assert job['result'] is None and not calls
    eng.act(j,'reject',job['fingerprint'],background=False)
    assert eng.get(j)['status']=='rejected' and not calls
def test_worker_missing_blocks_after_approval(eng,monkeypatch):
    monkeypatch.delenv('EWB_WORKER_IMAGE',raising=False)
    j=eng.create('Moving average',extension=True,background=False)
    eng.act(j,'approve',eng.get(j)['fingerprint'],background=False)
    job=eng.get(j);assert job['status']=='blocked'
    assert 'No host execution' in job['error']
def test_checkpoint_survives_engine_recreation(eng):
    j=eng.create('Compare',background=False);restored=Engine(eng.data);job=restored.get(j)
    assert job['status']=='result_review'
    restored.act(j,'approve',job['result_fingerprint'],background=False)
    assert restored.get(j)['status']=='accepted'
    restored.close()
def test_corrupt_binary_is_blocked_by_cpp(eng):
    (eng.data/'run-a.ewb').write_bytes(b'INVALID FILE')
    j=eng.create('Compare',background=False)
    assert eng.get(j)['status']=='blocked' and eng.get(j)['result'] is None
def test_disabled_plugin_prevents_execution(eng):
    eng.db.execute("UPDATE settings SET value='disabled' WHERE key='plugin'");eng.db.commit()
    with pytest.raises(ValueError,match='Enable'):eng.create('Compare',background=False)
def test_unit_mismatch_is_not_silently_coerced():
    a={'schema':'ewb.series/1','x_unit':'sample','y_unit':'Pa','points':[[0,1],[1,2]]}
    with pytest.raises(ValueError,match='units'):compare(a,{**a,'y_unit':'MPa'})
def test_cloud_rejects_engineering_context_before_network(monkeypatch):
    monkeypatch.delenv('EWB_LOCAL_MODEL_URL',raising=False)
    with pytest.raises(ValueError,match='Engineering context'):ModelGateway().complete('frontier','Explain',engineering_context={'secret':'engineering'})
def test_nonloopback_engineering_model_requires_explicit_approval(monkeypatch):
    monkeypatch.setenv('EWB_LOCAL_MODEL_URL','https://remote.example/v1');monkeypatch.delenv('EWB_APPROVED_ONPREM',raising=False)
    with pytest.raises(ValueError,match='explicitly'):ModelGateway()
def test_cancelled_review_cannot_resume(eng):
    j=eng.create('Compare',background=False);eng.act(j,'cancel',background=False)
    with pytest.raises(ValueError):eng.act(j,'resume',background=False)
    assert eng.get(j)['status']=='cancelled'

def test_local_model_script_is_proposed_not_executed(eng,monkeypatch):
    monkeypatch.setattr(eng.gateway,'info',lambda:{'local':{'configured':True}})
    monkeypatch.setattr(eng.gateway,'complete',lambda *a,**k:json.dumps({'script':'print("draft only")'}))
    calls=[];monkeypatch.setattr('backend.engine.run_script',lambda *a:calls.append(a))
    j=eng.create('Moving average',extension=True,background=False);job=eng.get(j)
    assert job['script']=='print("draft only")' and job['draft_source']=='Local model draft'
    assert job['status']=='code_review' and not calls

def test_worker_image_change_invalidates_approval(eng,monkeypatch):
    j=eng.create('Moving average',extension=True,background=False)
    monkeypatch.setenv('EWB_WORKER_IMAGE','sha256:changed')
    eng.act(j,'approve',eng.get(j)['fingerprint'],background=False)
    assert eng.get(j)['status']=='blocked' and 'image changed' in eng.get(j)['error']

def test_invalid_python_proposal_never_reaches_execution(eng,monkeypatch):
    monkeypatch.setattr(eng.gateway,'info',lambda:{'local':{'configured':True}})
    monkeypatch.setattr(eng.gateway,'complete',lambda *a,**k:json.dumps({'script':'Here is code: not Python'}))
    calls=[];monkeypatch.setattr('backend.engine.run_script',lambda *a:calls.append(a))
    j=eng.create('Smooth',extension=True,background=False)
    assert eng.get(j)['status']=='blocked' and not calls

def test_incorrect_generated_numerics_block_report(eng,monkeypatch):
    j=eng.create('Smooth',extension=True,background=False)
    inputs=eng.get(j)['inputs']
    bad={'extension':'Incorrect method','unit':inputs['a']['y_unit'],'points':[[p[0],0] for p in inputs['a']['points']]}
    monkeypatch.setattr('backend.engine.run_script',lambda *a:bad)
    eng.act(j,'approve',eng.get(j)['fingerprint'],background=False)
    assert eng.get(j)['status']=='blocked' and eng.get(j)['result'] is None
    assert 'independent' in eng.get(j)['error']
