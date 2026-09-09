"""Released, bounded workbook inspection inside the isolated Python worker."""
import tempfile
from pathlib import Path
from .worker import run_plot_script
INSPECT = """import json
from workbench_files import inspect
files=json.load(open('/inputs/data.json'))['files']
results=[]
for file in files[:10]:
 try: results.append(inspect(file))
 except Exception as exc: results.append({'name':file['name'],'error':type(exc).__name__+': '+str(exc)[:500]})
json.dump({'files':results},open('/outputs/result.json','w'))
"""

def preview_excel(engine,data,image):
    with tempfile.TemporaryDirectory(dir=engine.data) as directory:
        _,result,_=run_plot_script(INSPECT,{'files':data['files']},Path(directory)/'preview',image,mounts=engine.upload_mounts(data['files']))
        return result
