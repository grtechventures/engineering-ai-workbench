import pytest
from test_workbench import eng
from backend.configuration import Connection

def test_public_provider_denied(eng):
    with pytest.raises(ValueError):eng.connection_save(dict(name='Cloud',provider='OpenAI-compatible',url='https://example.com/v1',model='test'))

def test_profiles_switch_and_edit(eng):
    d=dict(name='Local',provider='Ollama',url='http://127.0.0.1:11434/v1',model='first')
    cid=eng.connection_save(d)['id'];eng.connection_action(cid,'activate')
    assert eng.gateway.local_model=='first'
    eng.connection_save({**d,'model':'second'},cid)
    assert eng.gateway.local_model=='first'
    eng.connection_action(cid,'activate');assert eng.gateway.local_model=='second'
    assert len(eng.configuration()['connections'])==1

def test_runtime_rejects_unpinned_images(eng):
    with pytest.raises(ValueError):eng.runtime_save(dict(comparison_image='python:latest',python_image='python:latest'))

def test_security_disable(eng):
    eng.discovery_disable()
    assert eng.configuration()['discovery_disabled']
    with pytest.raises(ValueError,match='disabled'):eng.resource_inspect('anything')

def test_matlab_configuration_is_not_execution_authority(eng):
    assert eng.matlab_get()['config']['license_status']=='unknown'
    r=eng.matlab_save({'location':'enterprise_server','server_reference':'engineering-server','license_status':'confirmed_by_admin','toolboxes':'Simulink'})
    assert not r['execution_available']
    assert eng.matlab_get()['config']['toolboxes']=='Simulink'
