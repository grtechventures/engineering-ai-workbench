"""Explicit browser uploads; no server path access or execution."""
import hashlib,json
from pathlib import PurePosixPath
from pydantic import BaseModel,ConfigDict,Field
class Attachment(BaseModel):
    model_config=ConfigDict(extra='forbid')
    name:str=Field(min_length=1,max_length=250)
    content:str=Field(max_length=8000)
class AttachmentsMixin:
    def init_attachments(self):
        self.db.execute('CREATE TABLE IF NOT EXISTS attachments(conversation_id TEXT,name TEXT,content TEXT,sha256 TEXT,PRIMARY KEY(conversation_id,name))');self.db.commit()
    def attachment_list(self,cid):
        with self.lock:return [dict(x) for x in self.db.execute('SELECT name,content,sha256 FROM attachments WHERE conversation_id=? ORDER BY name',(cid,))]
    def attachment_add(self,cid,d):
        self.conversation_get(cid);a=Attachment.model_validate(d);p=PurePosixPath(a.name)
        if p.is_absolute() or '..' in p.parts or '\\' in a.name or p.suffix.lower() not in {'.txt','.csv','.md','.json','.py','.cpp','.h','.cs'}:raise ValueError('Use text, CSV, JSON or supported source files with relative names')
        if '\x00' in a.content:raise ValueError('Binary files are unsupported')
        raw=a.content.encode('utf-8')
        if len(raw)>8000:raise ValueError('Each file must be at most 8 KB')
        with self.lock:
            existing=[x for x in self.attachment_list(cid) if x['name']!=a.name]
            if len(existing)>=10 or sum(len(x['content'].encode()) for x in existing)+len(raw)>32000:raise ValueError('Conversation limit: 10 files and 32 KB total')
            self.db.execute('INSERT OR REPLACE INTO attachments VALUES(?,?,?,?)',(cid,a.name,a.content,hashlib.sha256(raw).hexdigest()));self.db.commit()
        return {'ok':True}
    def attachment_clear(self,cid):
        with self.lock:
            self.db.execute('DELETE FROM attachments WHERE conversation_id=?',(cid,))
            self.db.execute("UPDATE uploads SET status='detached' WHERE cid=? AND status='ready'",(cid,));self.db.commit()
        return {'ok':True}

# Large files are stored separately from model context and the workspace database.
import os,shutil,uuid
class UploadStart(BaseModel):
    model_config=ConfigDict(extra='forbid')
    name:str=Field(min_length=1,max_length=250)
    size:int=Field(ge=0)

def init_uploads(self):
    self.db.execute('CREATE TABLE IF NOT EXISTS uploads(id TEXT PRIMARY KEY,cid TEXT,name TEXT,size INTEGER,offset INTEGER,status TEXT,sha TEXT,preview TEXT)');self.db.commit()
    (self.data/'uploads').mkdir(exist_ok=True)
def upload_start(self,cid,d):
    self.conversation_get(cid);a=UploadStart.model_validate(d);p=PurePosixPath(a.name)
    if p.is_absolute() or '..' in p.parts or '\\' in a.name:raise ValueError('Use a relative display name')
    with self.lock:
        used=self.db.execute('SELECT coalesce(sum(size),0) FROM uploads').fetchone()[0]
        quota=int(os.getenv('EWB_UPLOAD_QUOTA_BYTES',str(10*1024**3)))
        if used+a.size>quota or a.size+128*1024**2>shutil.disk_usage(self.data).free:raise ValueError('Upload exceeds available workspace storage; adjust the administrator storage quota or free disk space')
        uid=uuid.uuid4().hex;(self.data/'uploads'/uid).touch(exist_ok=False)
        self.db.execute('INSERT INTO uploads VALUES(?,?,?,?,?,?,?,?)',(uid,cid,a.name,a.size,0,'uploading','',''));self.db.commit()
    return {'id':uid}
def upload_chunk(self,uid,offset,chunk):
    if len(chunk)>1024**2:raise ValueError('Chunk exceeds 1 MB')
    with self.lock:
        r=self.db.execute('SELECT * FROM uploads WHERE id=?',(uid,)).fetchone()
        if not r or r['status']!='uploading' or offset!=r['offset'] or offset+len(chunk)>r['size']:raise ValueError('Invalid upload offset or state')
        p=self.data/'uploads'/uid
        if p.is_symlink():raise ValueError('Invalid upload file')
        with p.open('r+b') as f:f.seek(offset);f.write(chunk);f.truncate(offset+len(chunk))
        self.db.execute('UPDATE uploads SET offset=? WHERE id=?',(offset+len(chunk),uid));self.db.commit()
    return {'offset':offset+len(chunk)}
def upload_finish(self,uid):
    with self.lock:
        r=self.db.execute('SELECT * FROM uploads WHERE id=?',(uid,)).fetchone()
        if not r or r['status']!='uploading' or r['offset']!=r['size']:raise ValueError('Upload incomplete')
        p=self.data/'uploads'/uid
        if p.is_symlink():raise ValueError('Invalid upload file')
        h=hashlib.sha256()
        with p.open('rb') as f:
            first=f.read(4096);h.update(first)
            for chunk in iter(lambda:f.read(1024**2),b''):h.update(chunk)
        preview=first.decode('utf-8',errors='replace') if b'\x00' not in first else '[Binary data: approved reader required]'
        self.db.execute("UPDATE uploads SET status='ready',sha=?,preview=? WHERE id=?",(h.hexdigest(),preview,uid));self.db.commit()
    return {'ok':True}
def upload_list(self,cid):
    with self.lock:return [{'id':r['id'],'name':r['name'],'size':r['size'],'sha256':r['sha'],'preview':r['preview'],'path':'/datasets/'+r['id']} for r in self.db.execute("SELECT * FROM uploads WHERE cid=? AND status='ready'",(cid,))]
def upload_mounts(self,items):
    mounts=[]
    for item in items:
        with self.lock:r=self.db.execute("SELECT * FROM uploads WHERE id=? AND status IN ('ready','detached')",(item['id'],)).fetchone()
        if not r or r['sha']!=item['sha256']:raise ValueError('Input snapshot is unavailable')
        p=self.data/'uploads'/r['id']
        if p.is_symlink() or not p.is_file():raise ValueError('Invalid input snapshot')
        h=hashlib.sha256()
        with p.open('rb') as f:
            for chunk in iter(lambda:f.read(1024**2),b''):h.update(chunk)
        if h.hexdigest()!=r['sha']:raise ValueError('Input file changed since approval')
        mounts+=['--mount',f'type=bind,src={p.resolve()},dst=/datasets/{r["id"]},readonly']
    return mounts
AttachmentsMixin.init_uploads=init_uploads
AttachmentsMixin.upload_start=upload_start
AttachmentsMixin.upload_chunk=upload_chunk
AttachmentsMixin.upload_finish=upload_finish
AttachmentsMixin.upload_list=upload_list
AttachmentsMixin.upload_mounts=upload_mounts
