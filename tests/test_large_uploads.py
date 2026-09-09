import pytest
from test_workbench import eng
from test_agents import BASE

def test_chunk_offsets_snapshot_integrity_and_quota(eng,monkeypatch):
    cid=eng.conversation_create(eng.agent_save(BASE)['id'])['id']
    monkeypatch.setenv('EWB_UPLOAD_QUOTA_BYTES','20')
    uid=eng.upload_start(cid,dict(name='sample.csv',size=4))['id']
    with pytest.raises(ValueError):eng.upload_chunk(uid,1,b'ab')
    eng.upload_chunk(uid,0,b'1\n2\n');eng.upload_finish(uid)
    items=eng.upload_list(cid);assert items[0]['size']==4
    assert 'readonly' in eng.upload_mounts(items)[1]
    eng.attachment_clear(cid);assert eng.upload_list(cid)==[]
    assert eng.upload_mounts(items)
    (eng.data/'uploads'/uid).write_text('oops')
    with pytest.raises(ValueError,match='changed'):eng.upload_mounts(items)
    with pytest.raises(ValueError):eng.upload_start(cid,dict(name='too-large',size=21))
