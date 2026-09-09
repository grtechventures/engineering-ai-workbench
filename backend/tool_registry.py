"""Tool registration metadata is not executable authority or filesystem access."""
import time,uuid
from pydantic import BaseModel,ConfigDict,Field
from typing import Literal
class ToolRegistration(BaseModel):
    model_config=ConfigDict(extra='forbid')
    name:str=Field(min_length=1,max_length=100)
    description:str=Field(min_length=1,max_length=1000)
    kind:Literal['application','module','service']='application'
    location:str=Field(default='',max_length=1000)
    source_folder:str=Field(default='',max_length=1000)

class ToolRegistryMixin:
    def init_tool_registry(self):
        self.db.execute('CREATE TABLE IF NOT EXISTS tool_registrations(id TEXT PRIMARY KEY,name TEXT,description TEXT,kind TEXT,location TEXT,source_folder TEXT,created REAL)');self.db.commit()
    def tool_registrations(self):
        with self.lock:return [dict(x) for x in self.db.execute('SELECT * FROM tool_registrations ORDER BY created')]
    def tool_register(self,config):
        c=ToolRegistration.model_validate(config);tid=uuid.uuid4().hex
        with self.lock:
            self.db.execute('INSERT INTO tool_registrations VALUES(?,?,?,?,?,?,?)',(tid,c.name,c.description,c.kind,c.location,c.source_folder,time.time()));self.db.commit()
        return {'id':tid,'status':'registered_not_executable'}
