"""Only Docker executes newly drafted Python. Never falls back to host execution."""
import json, os, shutil, subprocess, uuid, time, hashlib
from pathlib import Path

def worker_status():
    image=os.getenv('EWB_WORKER_IMAGE','')
    return {'docker_installed':bool(shutil.which('docker')),'image_configured':bool(image),
            'ready':bool(shutil.which('docker') and image),'image':image or 'Not configured'}

def local_docker_command():
    # Inspect local CLI configuration, then pin a local socket explicitly.
    # Never honor a remote DOCKER_HOST or SSH/TCP context for engineering inputs.
    host=os.getenv('DOCKER_HOST','')
    if not host:
        result=subprocess.run(['docker','context','inspect','--format','{{json .Endpoints.docker.Host}}'],capture_output=True,text=True,timeout=10,check=True)
        host=json.loads(result.stdout)
    if not isinstance(host,str) or not (host.startswith('unix:///') or host.startswith('npipe:////./pipe/')):
        raise RuntimeError('Only a local Docker socket is allowed; remote Docker endpoints are blocked')
    env={k:v for k,v in os.environ.items() if k not in ('DOCKER_HOST','DOCKER_CONTEXT','DOCKER_TLS_VERIFY','DOCKER_CERT_PATH')}
    return ['docker','--host',host],env

def run_script(code, inputs, directory):
    status=worker_status()
    if not status['ready']: raise RuntimeError('Docker worker unavailable. Install Docker and configure EWB_WORKER_IMAGE. No host execution was attempted.')
    image=status['image']
    if not image.startswith('sha256:'): raise RuntimeError('Worker image must be pinned to a local sha256 image ID')
    docker_command,docker_env=local_docker_command()
    name='ewb-'+uuid.uuid4().hex
    base=Path(directory)/name; ins=base/'inputs'; outs=base/'outputs'
    ins.mkdir(parents=True,exist_ok=True);outs.mkdir(exist_ok=True)
    (ins/'script.py').write_text(code);(ins/'data.json').write_text(json.dumps(inputs))
    # Output workspace is isolated to this job; inputs are mounted read-only.
    outs.chmod(0o777)
    started=time.time()
    command=docker_command+['run','--rm','--pull=never','--name',name,'--network=none','--read-only',
             '--user','65534:65534','--cap-drop=ALL','--security-opt=no-new-privileges',
             '--pids-limit=64','--cpus=1','--memory=256m','--memory-swap=256m',
             '--ulimit','fsize=1048576:1048576', '--log-driver=none',
             '--tmpfs','/tmp:rw,noexec,nosuid,size=16m',
             '--mount',f'type=bind,src={ins.resolve()},dst=/inputs,readonly',
             '--mount',f'type=bind,src={outs.resolve()},dst=/outputs',
             image,'python','-I','/inputs/script.py']
    try:
        result=subprocess.run(command,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=30,env=docker_env)
        if result.returncode: raise RuntimeError('Container execution failed. Review the script and worker setup.')
    except subprocess.TimeoutExpired:
        subprocess.run(docker_command+['rm','-f',name],capture_output=True,timeout=10,env=docker_env)
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

def run_plot_script(code, inputs, directory, image, mounts=None):
    """Execute a reviewed general Python task; collect bounded JSON and optional PNG."""
    if not image.startswith('sha256:'):raise ValueError('Pin a local Docker image ID')
    command,env=local_docker_command();name='ewb-task-'+uuid.uuid4().hex
    root=Path(directory)/name;ins=root/'inputs';outs=root/'outputs'
    ins.mkdir(parents=True);outs.mkdir();outs.chmod(0o777)
    (ins/'script.py').write_text(code);(ins/'data.json').write_text(json.dumps(inputs))
    started=time.time()
    try:
        result=subprocess.run(command+['run','--rm','--pull=never','--name',name,'--network=none','--read-only',
            '--user','65534:65534','--cap-drop=ALL','--security-opt=no-new-privileges','--pids-limit=64',
            '--cpus=1','--memory=512m','--memory-swap=512m','--ulimit','fsize=4194304:4194304','--log-driver=none',
            '--tmpfs','/tmp:rw,noexec,nosuid,size=64m','--env','MPLCONFIGDIR=/tmp/mpl','--env','MPLBACKEND=Agg',
            '--mount',f'type=bind,src={ins.resolve()},dst=/inputs,readonly',
            '--mount',f'type=bind,src={outs.resolve()},dst=/outputs',*(mounts or []),image,'python','-I','/inputs/script.py'],
            stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=60,env=env)
        if result.returncode:raise RuntimeError('Python task failed in Docker. Revise the script or check its dependencies.')
    except subprocess.TimeoutExpired:
        subprocess.run(command+['rm','-f',name],capture_output=True,timeout=10,env=env)
        raise RuntimeError('Python task exceeded its 60 second limit')
    target=outs/'result.json'
    payload=None
    if target.exists() or target.is_symlink():
        if target.is_symlink() or not target.is_file() or target.stat().st_size>1024*1024:raise RuntimeError('Task result.json is invalid or too large')
        payload=json.loads(target.read_text(),parse_constant=lambda x: (_ for _ in ()).throw(ValueError('Nonfinite JSON output')))
        if not isinstance(payload,dict):raise RuntimeError('Task result must be a JSON object')
    png=None;picture=outs/'plot.png'
    if picture.exists() or picture.is_symlink():
        if picture.is_symlink() or not picture.is_file() or picture.stat().st_size>4*1024*1024:raise RuntimeError('Invalid PNG artifact')
        png=picture.read_bytes()
        if len(png)<24 or png[:8]!=b'\x89PNG\r\n\x1a\n':raise RuntimeError('Expected a PNG image')
        import struct
        w,h=struct.unpack('>II',png[16:24])
        if not 0<w<=2000 or not 0<h<=1600:raise RuntimeError('PNG dimensions exceed display limits')
    if payload is None:
        if png is None:raise RuntimeError('Task produced neither result.json nor a valid plot.png')
        payload={'summary':'Plot-only output; no structured calculations were supplied by the script.','output_kind':'plot_only'}
    receipt={'runtime':'Docker','image_id':image,'container_name':name,'exit_code':0,'network':'none','container_removed':True,
             'started_at':started,'finished_at':time.time(),'script_sha256':hashlib.sha256(code.encode()).hexdigest(),
             'result_sha256':hashlib.sha256(target.read_bytes()).hexdigest() if target.is_file() else None,'plot_sha256':hashlib.sha256(png).hexdigest() if png else None}
    return png,payload,receipt
