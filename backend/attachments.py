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
        with self.lock:self.db.execute('DELETE FROM attachments WHERE conversation_id=?',(cid,));self.db.commit()
        return {'ok':True}
