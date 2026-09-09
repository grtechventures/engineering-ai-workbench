"""Only Docker executes newly drafted Python. Never falls back to host execution."""
import json, os, shutil, subprocess, uuid, time, hashlib
from pathlib import Path

def worker_status():
    image=os.getenv('EWB_WORKER_IMAGE','')
    return {'docker_installed':bool(shutil.which('docker')),'image_configured':bool(image),
            'ready':bool(shutil.which('docker') and image),'image':image or 'Not configured'}

def run_script(code, inputs, directory):
    status=worker_status()
    if not status['ready']: raise RuntimeError('Docker worker unavailable. Install Docker and configure EWB_WORKER_IMAGE. No host execution was attempted.')
    image=status['image']
    if not image.startswith('sha256:'): raise RuntimeError('Worker image must be pinned to a local sha256 image ID')
    name='ewb-'+uuid.uuid4().hex
    base=Path(directory)/name; ins=base/'inputs'; outs=base/'outputs'
    ins.mkdir(parents=True,exist_ok=True);outs.mkdir(exist_ok=True)
    (ins/'script.py').write_text(code);(ins/'data.json').write_text(json.dumps(inputs))
    # Output workspace is isolated to this job; inputs are mounted read-only.
    outs.chmod(0o777)
    started=time.time()
    command=['docker','run','--rm','--pull=never','--name',name,'--network=none','--read-only',
             '--user','65534:65534','--cap-drop=ALL','--security-opt=no-new-privileges',
             '--pids-limit=64','--cpus=1','--memory=256m','--memory-swap=256m',
             '--ulimit','fsize=1048576:1048576', '--log-driver=none',
             '--tmpfs','/tmp:rw,noexec,nosuid,size=16m',
             '--mount',f'type=bind,src={ins.resolve()},dst=/inputs,readonly',
             '--mount',f'type=bind,src={outs.resolve()},dst=/outputs',
             image,'python','-I','/inputs/script.py']
    try:
        result=subprocess.run(command,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=30)
        if result.returncode: raise RuntimeError('Container execution failed. Review the script and worker setup.')
    except subprocess.TimeoutExpired:
        subprocess.run(['docker','rm','-f',name],capture_output=True,timeout=10)
        raise RuntimeError('Worker exceeded its 30 second execution limit')
    target=outs/'result.json'
    if target.is_symlink() or not target.is_file() or target.stat().st_size>1024*1024:
        raise RuntimeError('Worker did not produce a valid bounded result artifact')
    payload=json.loads(target.read_text())
    receipt={'runtime':'Docker','container_name':name,'image_id':image,'exit_code':result.returncode,
             'started_at':started,'finished_at':time.time(),'container_removed':True,
             'network':'none','user':'65534:65534','memory_mb':256,'timeout_seconds':30,
             'script_sha256':hashlib.sha256(code.encode()).hexdigest(),
             'output_sha256':hashlib.sha256(target.read_bytes()).hexdigest()}
    (Path(directory)/'execution.json').write_text(json.dumps(receipt,indent=2))
    payload['execution']=receipt
    return payload
