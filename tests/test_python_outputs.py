import struct
from pathlib import Path
from types import SimpleNamespace
import pytest
from backend.worker import run_plot_script

def test_plot_only_output_is_accepted(tmp_path,monkeypatch):
    monkeypatch.setattr('backend.worker.local_docker_command',lambda:(['docker'],{}))
    def run(cmd,**kw):
        mount=next(x for x in cmd if x.startswith('type=bind,src=') and x.endswith('dst=/outputs'))
        out=Path(mount.split('src=')[1].split(',dst=')[0]);(out/'plot.png').write_bytes(b'\x89PNG\r\n\x1a\n'+b'\0'*8+struct.pack('>II',800,600))
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr('backend.worker.subprocess.run',run)
    png,result,receipt=run_plot_script('pass',{},tmp_path,'sha256:test')
    assert png and result['output_kind']=='plot_only' and receipt['result_sha256'] is None

def test_no_output_is_still_rejected(tmp_path,monkeypatch):
    monkeypatch.setattr('backend.worker.local_docker_command',lambda:(['docker'],{}))
    monkeypatch.setattr('backend.worker.subprocess.run',lambda *a,**kw:SimpleNamespace(returncode=0))
    with pytest.raises(RuntimeError,match='neither'):run_plot_script('pass',{},tmp_path,'sha256:test')
