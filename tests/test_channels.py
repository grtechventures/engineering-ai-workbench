import json
import pytest
from test_workbench import eng

def test_defaults_and_multiple_profiles(eng):
    assert not eng.channels_get()['live_available']
    eng.channel_save({'name':'Slack draft','provider':'Slack'})
    c=eng.channel_save({'name':'Teams draft'})
    rows=eng.channels_get()['profiles']
    assert [r['provider'] for r in rows]==['Microsoft Teams','Slack']
    assert rows[0]['notifications'] and not rows[0]['requests'] and not rows[0]['results']
    eng.channel_save({'name':'Updated Teams','provider':'Microsoft Teams','requests':True},c['id'])
    assert len(eng.channels_get()['profiles'])==2
    assert not eng.channels_get()['live_available']
    assert json.loads(eng.db.execute("SELECT value FROM settings WHERE key='channels_config'").fetchone()[0])

def test_preview_never_transmits(eng,monkeypatch):
    import socket
    monkeypatch.setattr(socket.socket,'connect',lambda *a:pytest.fail('Network attempted'))
    c=eng.channel_save({'name':'Team','requests':True,'results':True})
    preview=eng.channel_preview(c['id'])
    assert preview['sent'] is False and 'sample job' in preview['preview']
    eng.channel_save({'name':'Team','notifications':False},c['id'])
    assert 'disabled' in eng.channel_preview(c['id'])['preview']

@pytest.mark.parametrize('extra',[{'enabled':True},{'webhook_url':'https://example.com'},{'token':'secret'}])
def test_no_transport_or_secret_fields(eng,extra):
    with pytest.raises(ValueError):eng.channel_save({'name':'Team',**extra})

def test_invalid_update_and_preview(eng):
    with pytest.raises(ValueError):eng.channel_save({'name':'Team'},'missing')
    with pytest.raises(ValueError):eng.channel_preview('missing')
    with pytest.raises(ValueError):eng.channel_save({'name':'   '})
