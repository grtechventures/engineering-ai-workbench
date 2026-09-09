"""Explicit, bounded, read-only resource discovery. Never executes source code."""
import csv
import hashlib
import io
import json
import os
import time
import uuid
from pathlib import Path
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

class ResourceDraft(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: str = Field(min_length=1, max_length=100)
    category: Literal['source','data']
    location: str = Field(min_length=1, max_length=1000)
    format: Literal['code','csv','binary','hdf5','sql','other']
    description: str = Field(default='', max_length=1000)
    units: str = Field(default='', max_length=300)
    reader: str = Field(default='', max_length=300)

CODE = {'.py','.cpp','.h','.hpp','.c','.cs','.java','.rs','.f90','.m','.md'}

def approved_path(location):
    # Configuration is independent of registration. No request can approve a root.
    roots = json.loads(os.getenv('EWB_RESOURCE_ROOTS','[]'))
    if not isinstance(roots,list) or not all(isinstance(x,str) for x in roots):
        raise ValueError('Resource roots must be a JSON list of paths')
    p = Path(location)
    if not p.is_absolute() or '..' in p.parts:
        raise ValueError('Use an absolute path without parent traversal')
    # Lexical check before filesystem access, including network locations.
    candidates = [Path(r) for r in roots if Path(r).is_absolute() and (p == Path(r) or Path(r) in p.parents)]
    if not candidates:
        raise ValueError('Location is not within an administrator-approved resource root')
    for part in [p,*p.parents]:
        if part.is_symlink():
            raise ValueError('Symbolic links are not permitted for resource access')
    resolved=p.resolve(strict=True)
    if not any(resolved == r.resolve() or r.resolve() in resolved.parents for r in candidates):
        raise ValueError('Resource escapes its approved root')
    return resolved

class ResourcesMixin:
    def init_resources(self):
        self.db.execute('CREATE TABLE IF NOT EXISTS resources(id TEXT PRIMARY KEY, payload TEXT, created REAL)')
        self.db.commit()
    def resources_list(self):
        with self.lock:
            return [dict(id=r['id'],**json.loads(r['payload'])) for r in self.db.execute('SELECT * FROM resources ORDER BY created')]
    def resource_add(self, value):
        d=ResourceDraft.model_validate(value)
        if (d.category=='source') != (d.format=='code'):
            raise ValueError('Source locations use code format; data locations use a data format')
        rid=uuid.uuid4().hex
        with self.lock:
            self.db.execute('INSERT INTO resources VALUES(?,?,?)',(rid,d.model_dump_json(),time.time()));self.db.commit()
        return {'id':rid,**d.model_dump()}
    def resource_remove(self,rid):
        with self.lock:
            self.db.execute('DELETE FROM resources WHERE id=?',(rid,));self.db.commit()
        return {'ok':True}
    def resource_inspect(self,rid):
        with self.lock:
            row=self.db.execute('SELECT payload FROM resources WHERE id=?',(rid,)).fetchone()
        if not row:raise ValueError('Resource not found')
        d=json.loads(row['payload'])
        if d['category']=='data' and d['format']!='csv':
            return {'notice':'Registered only. This format requires an approved reader integration; no connection or read was attempted.'}
        p=approved_path(d['location'])
        files=[]
        if d['category']=='source' and p.is_dir():
            visited=0
            for root,dirs,names in os.walk(p,followlinks=False):
                dirs[:]=sorted(x for x in dirs if not x.startswith('.') and x not in {'node_modules','venv','__pycache__','build','data'} and not (Path(root)/x).is_symlink())
                for name in sorted(names):
                    visited+=1
                    if visited>1000:break
                    f=Path(root)/name
                    if f.suffix.lower() in CODE and not f.is_symlink():files.append(f)
                    if len(files)>=20:break
                if visited>1000 or len(files)>=20:break
        else:files=[p]
        outputs=[];total=0
        for f in files:
            f=approved_path(str(f))
            if not f.is_file():raise ValueError('Select a regular file or source folder')
            if d['category']=='source' and f.suffix.lower() not in CODE:raise ValueError('Unsupported source file type')
            with f.open('rb') as stream:raw=stream.read(65537)
            if len(raw)>65536:continue
            total+=len(raw)
            if total>262144:break
            content=raw.decode('utf-8')
            item={'name':f.name,'sha256':hashlib.sha256(raw).hexdigest()}
            if d['category']=='data':
                rows=list(csv.reader(io.StringIO(content)))
                if not rows:raise ValueError('CSV is empty')
                item.update(columns=rows[0],preview=rows[1:11],row_count=len(rows)-1,units=d['units'])
            else:item['content']=content
            outputs.append(item)
        return {'files':outputs,'notice':'Read-only preview; at most 20 files, 64 KB per file, 256 KB total. Large files are skipped. This does not authorize execution or attach data to an analysis.'}
