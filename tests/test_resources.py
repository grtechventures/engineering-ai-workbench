import json
import pytest
from test_workbench import eng

def add(eng,p,category='source',format='code'):
    return eng.resource_add(dict(name='Example',category=category,format=format,location=str(p)))['id']

def test_registration_does_not_authorize_read(eng,tmp_path):
    p=tmp_path/'code.py';p.write_text('print(1)')
    rid=add(eng,p)
    with pytest.raises(ValueError,match='approved'):eng.resource_inspect(rid)

def test_source_inspection_and_revocation(eng,tmp_path,monkeypatch):
    p=tmp_path/'code.py';p.write_text('print(1)')
    monkeypatch.setenv('EWB_RESOURCE_ROOTS',json.dumps([str(tmp_path)]))
    rid=add(eng,p);assert eng.resource_inspect(rid)['files'][0]['content']=='print(1)'
    monkeypatch.setenv('EWB_RESOURCE_ROOTS','[]')
    with pytest.raises(ValueError):eng.resource_inspect(rid)

def test_symlink_denied(eng,tmp_path,monkeypatch):
    p=tmp_path/'code.py';p.symlink_to('/etc/passwd')
    monkeypatch.setenv('EWB_RESOURCE_ROOTS',json.dumps([str(tmp_path)]))
    with pytest.raises(ValueError):eng.resource_inspect(add(eng,p))

def test_csv_preview_and_non_csv_no_access(eng,tmp_path,monkeypatch):
    p=tmp_path/'sample.csv';p.write_text('time,value\n0,3\n1,4\n')
    monkeypatch.setenv('EWB_RESOURCE_ROOTS',json.dumps([str(tmp_path)]))
    result=eng.resource_inspect(add(eng,p,'data','csv'))['files'][0]
    assert result['columns']==['time','value'] and result['row_count']==2
    assert 'no connection' in eng.resource_inspect(add(eng,'https://example.invalid','data','sql'))['notice']

def test_large_source_skipped_and_remove(eng,tmp_path,monkeypatch):
    p=tmp_path/'large.py';p.write_text('x'*65537)
    monkeypatch.setenv('EWB_RESOURCE_ROOTS',json.dumps([str(tmp_path)]))
    rid=add(eng,p);assert eng.resource_inspect(rid)['files']==[]
    eng.resource_remove(rid);assert eng.resources_list()==[]
