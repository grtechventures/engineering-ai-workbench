import pytest
from backend.network_policy import validate_model_url
from backend.models import ModelGateway
from backend.worker import local_docker_command
from backend.engine import Engine
from test_workbench import eng

@pytest.mark.parametrize('url',['https://8.8.8.8/v1','http://169.254.169.254/v1','https://example.com/v1','http://127.0.0.1@8.8.8.8/v1','file:///tmp/model','http://127.0.0.1/v1?redirect=1'])
def test_unapproved_network_destinations_rejected(url,monkeypatch):
    monkeypatch.setenv('EWB_APPROVED_ONPREM','1')
    monkeypatch.setenv('EWB_APPROVED_MODEL_IPS','8.8.8.8,169.254.169.254')
    with pytest.raises(ValueError):validate_model_url(url)

def test_loopback_and_exact_lan_approval(monkeypatch):
    assert validate_model_url('http://localhost:11434/v1')=='http://127.0.0.1:11434/v1'
    monkeypatch.setenv('EWB_APPROVED_ONPREM','1');monkeypatch.setenv('EWB_APPROVED_MODEL_IPS','10.1.2.3')
    assert validate_model_url('https://10.1.2.3/v1')=='https://10.1.2.3/v1'
    with pytest.raises(ValueError):validate_model_url('https://10.1.2.4/v1')

def test_frontier_config_cannot_override_offline_policy(monkeypatch):
    monkeypatch.delenv('EWB_LOCAL_MODEL_URL',raising=False)
    monkeypatch.setenv('EWB_FRONTIER_URL','https://example.com/v1')
    monkeypatch.setenv('EWB_FRONTIER_MODEL','anything')
    g=ModelGateway()
    assert not g.info()['frontier']['configured']
    with pytest.raises(ValueError,match='disabled'):g.complete('frontier','public question')

@pytest.mark.parametrize('host',['tcp://10.1.2.3:2375','ssh://server','npipe:////server/pipe/docker_engine'])
def test_remote_docker_rejected(host,monkeypatch):
    monkeypatch.setenv('DOCKER_HOST',host)
    with pytest.raises(RuntimeError,match='local Docker'):local_docker_command()

def test_external_artifact_directory_requires_explicit_root(tmp_path,monkeypatch):
    external=tmp_path/'shared';monkeypatch.setenv('EWB_ARTIFACT_DIR',str(external))
    monkeypatch.delenv('EWB_APPROVED_FILE_ROOTS',raising=False)
    with pytest.raises(ValueError,match='approval'):Engine(tmp_path/'state')
    assert not external.exists()
    monkeypatch.setenv('EWB_APPROVED_FILE_ROOTS',str(external))
    e=Engine(tmp_path/'state')
    try:assert e.artifacts.root==external
    finally:e.close()

def test_input_symlink_rejected(eng,tmp_path):
    original=eng.data/'run-a.ewb';outside=eng.data.parent/(eng.data.name+'-outside.ewb')
    outside.write_bytes(original.read_bytes());original.unlink()
    original.symlink_to(outside)
    j=eng.create('Compare',background=False)
    assert eng.get(j)['status']=='blocked' and 'escapes' in eng.get(j)['error']
