"""Compile the demo legacy app and seed synthetic binary inputs. Run after installing requirements."""
from pathlib import Path
import os, shutil, subprocess, hashlib
ROOT=Path(__file__).resolve().parents[1]
build=ROOT/'legacy/build';build.mkdir(exist_ok=True)
data=Path(os.getenv('EWB_DATA_DIR',ROOT/'data'));data.mkdir(parents=True,exist_ok=True)
exe=build/('engineering-demo.exe' if os.name=='nt' else 'engineering-demo')
stamp=build/'source-build.sha256'
source_hash=hashlib.sha256((ROOT/'legacy/engineering_demo.cpp').read_bytes()+Path(__file__).read_bytes()).hexdigest()
if not exe.exists() or not stamp.exists() or stamp.read_text()!=source_hash:
    compiler=shutil.which('clang++') or shutil.which('g++')
    if compiler:
        flags=[]
        if os.sys.platform=='darwin':
            sdk=subprocess.check_output(['xcrun','--show-sdk-path'],text=True).strip()
            headers=Path(sdk)/'usr/include/c++/v1'
            if not headers.exists():
                candidates=sorted(Path('/Library/Developer/CommandLineTools/SDKs').glob('MacOSX*.sdk/usr/include/c++/v1'))
                if candidates: headers=candidates[-1];sdk=str(headers.parents[3])
            flags=['-isysroot',sdk,'-isystem',str(headers)]
        subprocess.run([compiler,'-std=c++17','-O2',*flags,str(ROOT/'legacy/engineering_demo.cpp'),'-o',str(exe)],check=True)
    elif os.name=='nt' and shutil.which('cl'):
        subprocess.run(['cl','/EHsc','/std:c++17',str(ROOT/'legacy/engineering_demo.cpp'),'/Fe:'+str(exe)],cwd=build,check=True)
    else:raise SystemExit('Install a C++ compiler. On Windows use a Visual Studio Developer Command Prompt.')
    stamp.write_text(source_hash)
if not (data/'run-a.ewb').exists() or not (data/'run-b.ewb').exists():
    subprocess.run([str(exe),'seed',str(data)],check=True)
print('Demo application ready. Run: python -m uvicorn backend.app:app --host 127.0.0.1 --port 8765')
