import pytest
from test_workbench import eng
from test_agents import BASE

def test_upload_persist_bound_and_clear(eng):
    a=eng.agent_save(BASE);c=eng.conversation_create(a['id'])['id']
    eng.attachment_add(c,{'name':'folder/example.csv','content':'x,y\n1,2'})
    assert eng.conversation_get(c)['attachments'][0]['content']=='x,y\n1,2'
    with pytest.raises(ValueError):eng.attachment_add(c,{'name':'../secret.txt','content':'x'})
    with pytest.raises(ValueError):eng.attachment_add(c,{'name':'binary.txt','content':'\x00'})
    with pytest.raises(ValueError):eng.attachment_add(c,{'name':'large.txt','content':'x'*8001})
    eng.attachment_clear(c);assert eng.conversation_get(c)['attachments']==[]
