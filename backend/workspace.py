"""Local memory, content-addressed evidence and bounded experiments. No Git dependency."""
import hashlib, json, os, re, time, uuid
from pathlib import Path

def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()

class FileArtifacts:
    """Provider boundary: put/get/info. Keep the SQLite database on local disk."""
    def __init__(self, root):
        self.root=Path(root).resolve(); self.root.mkdir(parents=True,exist_ok=True)
    def put(self,value):
        raw=json.dumps(value,sort_keys=True,indent=2).encode()
        key=hashlib.sha256(raw).hexdigest(); target=self.root/(key+'.json')
        if target.exists():
            self.get(key); return key
        temporary=self.root/(uuid.uuid4().hex+'.tmp')
        try:
            with temporary.open('xb') as stream:
                stream.write(raw); stream.flush(); os.fsync(stream.fileno())
            os.replace(temporary,target)
        finally: temporary.unlink(missing_ok=True)
        return key
    def get(self,key):
        if not re.fullmatch(r'[a-f0-9]{64}',key): raise ValueError('Invalid artifact identifier')
        target=self.root/(key+'.json')
        if target.is_symlink(): raise ValueError('Symlinked artifact rejected')
        raw=target.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=key: raise ValueError('Artifact integrity check failed')
        return json.loads(raw)
    def info(self):
        return {'provider':'filesystem','database':'local SQLite','shared_service':False,'cloud_connectors':False}

class WorkspaceMixin:
    def init_workspace(self):
        artifact_root=Path(os.getenv('EWB_ARTIFACT_DIR',str(self.data/'artifacts'))).resolve()
        approved={str(Path(x).resolve()) for x in os.getenv('EWB_APPROVED_FILE_ROOTS','').split(os.pathsep) if x}
        if not artifact_root.is_relative_to(self.data.resolve()) and str(artifact_root) not in approved:
            raise ValueError('External evidence directory requires exact EWB_APPROVED_FILE_ROOTS approval')
        self.artifacts=FileArtifacts(artifact_root)
        columns={x[1] for x in self.db.execute('PRAGMA table_info(knowledge)')}
        for name,decl in [('source',"TEXT DEFAULT 'User-authored note'"),('revision','INTEGER DEFAULT 1'),('created','REAL DEFAULT 0')]:
            if name not in columns: self.db.execute(f'ALTER TABLE knowledge ADD COLUMN {name} {decl}')
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS memory_audit(id INTEGER PRIMARY KEY,note_id TEXT,revision INTEGER,action TEXT,at REAL);
        CREATE TABLE IF NOT EXISTS retrievals(id INTEGER PRIMARY KEY,conversation_id TEXT,query TEXT,refs TEXT,at REAL);
        CREATE TABLE IF NOT EXISTS lineage(job_id TEXT PRIMARY KEY,parent_id TEXT,mode TEXT);
        CREATE TABLE IF NOT EXISTS evidence_objects(job_id TEXT,artifact_id TEXT,at REAL,PRIMARY KEY(job_id,artifact_id));
        CREATE TABLE IF NOT EXISTS studies(id TEXT PRIMARY KEY,payload TEXT,status TEXT,fingerprint TEXT,result TEXT,created REAL);
        """)
        self.db.execute("UPDATE studies SET status='interrupted' WHERE status='running'"); self.db.commit()
    def knowledge_propose(self,text,scope='project',source='User-authored note',job_id=None):
        if not text.strip() or not source.strip(): raise ValueError('Text and source must not be empty')
        if job_id and self.get(job_id)['status']!='accepted': raise ValueError('Source job must be accepted first')
        mid=uuid.uuid4().hex
        with self.lock:
            self.db.execute('INSERT INTO knowledge(id,text,status,scope,job_id,source,revision,created) VALUES(?,?,?,?,?,?,?,?)',
                            (mid,text.strip(),'proposed',scope,job_id,source.strip(),1,time.time())); self.db.commit()
        return {'id':mid}
    def knowledge_decide(self,mid,action,revision=None):
        with self.lock:
            row=self.db.execute('SELECT * FROM knowledge WHERE id=?',(mid,)).fetchone()
            if not row: raise KeyError(mid)
            if revision is not None and row['revision']!=revision: raise ValueError('Note changed; reload before reviewing')
            if action=='approve' and row['status']!='proposed': raise ValueError('Only proposed notes can be approved')
            if row['status']=='retired': raise ValueError('Propose a replacement for a retired note')
            self.db.execute('UPDATE knowledge SET status=?,revision=revision+1 WHERE id=?',('approved' if action=='approve' else 'retired',mid))
            self.db.execute('INSERT INTO memory_audit(note_id,revision,action,at) VALUES(?,?,?,?)',(mid,row['revision'],action,time.time())); self.db.commit()
    def knowledge_search(self,query,limit=5):
        terms=set(re.findall(r'\w{3,}',query.lower()))-{'the','and','what','does','with','this','that'}
        with self.lock: rows=[dict(x) for x in self.db.execute("SELECT * FROM knowledge WHERE status='approved'")]
        matches=[]
        for row in rows:
            score=len(terms & set(re.findall(r'\w{3,}',(row['text']+' '+row['source']).lower())))
            if score: matches.append((score,row))
        matches.sort(key=lambda x:(-x[0],x[1]['id']))
        return [r for _,r in matches[:limit]]
    def record_retrieval(self,cid,query,refs):
        with self.lock:
            self.db.execute('INSERT INTO retrievals(conversation_id,query,refs,at) VALUES(?,?,?,?)',(cid,query,json.dumps(refs),time.time())); self.db.commit()
    def evidence(self,jid):
        item=self.get(jid)
        if not item.get('result'): raise ValueError('No result is available')
        with self.lock: row=self.db.execute('SELECT * FROM lineage WHERE job_id=?',(jid,)).fetchone()
        payload={k:item.get(k) for k in ['id','request','status','inputs','result','script','image','agent','plan','events','narrative','draft_source']}
        payload.update(schema='ewb.evidence/1',lineage=dict(row) if row else None,result_hash=fingerprint(item['result']),
                       notice='Synthetic example. Local single-user review; no engineering acceptance tolerance is defined.')
        key=self.artifacts.put(payload)
        with self.lock:
            self.db.execute('INSERT OR IGNORE INTO evidence_objects VALUES(?,?,?)',(jid,key,time.time())); self.db.commit()
        return {**payload,'artifact_id':key}
    def replay(self,jid,mode='snapshot',background=True):
        parent=self.get(jid)
        if not parent.get('inputs') or parent['status'] not in ('accepted','result_review','changes_requested'):
            raise ValueError('Replay requires a completed numerical result')
        agent=self.agent_get(parent['agent']['id']) if parent.get('agent') else None
        child=self.create(parent['request'],bool(parent['extension']),background=background,agent=agent,
                          snapshot=parent['inputs'] if mode=='snapshot' else None,parent_id=jid,replay_mode=mode)
        return {'id':child}
    def study_create(self,jid,windows,budget):
        job=self.get(jid)
        if job['status']!='accepted': raise ValueError('Accept the source comparison before proposing a study')
        if job['extension']: raise ValueError('Use a released comparison without generated code as the study source')
        self.check_agent(job,'compare')
        if not self.enabled(): raise ValueError('Comparison plugin is disabled')
        if not windows or len(windows)>8 or len(set(windows))!=len(windows) or any(type(w) is not int or w<1 or w>21 or w%2==0 for w in windows):
            raise ValueError('Choose up to eight unique odd windows between 1 and 21')
        if budget<1 or budget>10: raise ValueError('Study budget must be 1–10 seconds')
        p={'source_job':jid,'inputs':job['inputs'],'agent':job.get('agent'),'windows':windows,'budget_seconds':budget,
           'method':'analysis.smoothing_sensitivity@1.0.0','trials':len(windows),
           'objective':'Measure distortion and roughness; no automatic winner or engineering acceptance.'}
        sid=uuid.uuid4().hex
        with self.lock:
            self.db.execute('INSERT INTO studies VALUES(?,?,?,?,?,?)',(sid,json.dumps(p),'plan_review',fingerprint(p),None,time.time())); self.db.commit()
        return self.study_get(sid)
    def study_get(self,sid):
        with self.lock: row=self.db.execute('SELECT * FROM studies WHERE id=?',(sid,)).fetchone()
        if not row: raise KeyError(sid)
        return {**dict(row),'payload':json.loads(row['payload']),'result':json.loads(row['result']) if row['result'] else None}
    def study_list(self):
        with self.lock: return [self.study_get(r[0]) for r in self.db.execute('SELECT id FROM studies ORDER BY created DESC')]
    def study_act(self,sid,action,expected):
        with self.lock:
            study=self.study_get(sid)
            if expected!=study['fingerprint']: raise ValueError('Stale study approval')
            status=study['status']
            if status not in ('plan_review','result_review','interrupted'): raise ValueError('Study is not awaiting a decision')
            if action in ('cancel','reject'):
                self.db.execute("UPDATE studies SET status='cancelled' WHERE id=?",(sid,)); self.db.commit()
                return self.study_get(sid)
            if action!='approve': raise ValueError('Choose approve or cancel')
            if status=='result_review':
                self.db.execute("UPDATE studies SET status='accepted' WHERE id=?",(sid,)); self.db.commit()
                return self.study_get(sid)
            self.check_agent(study['payload'],'compare')
            if not self.enabled(): raise ValueError('Comparison plugin is disabled')
            self.db.execute("UPDATE studies SET status='running' WHERE id=?",(sid,)); self.db.commit()
        try:
            from .analysis import smoothing_study
            p=study['payload']; result=smoothing_study(p['inputs'],p['windows'],p['budget_seconds'])
            result['artifact_id']=self.artifacts.put({'schema':'ewb.study/1','plan':p,'result':result})
            with self.lock:
                self.db.execute("UPDATE studies SET status='result_review',result=?,fingerprint=? WHERE id=?",(json.dumps(result),fingerprint(result),sid)); self.db.commit()
        except Exception:
            with self.lock:
                self.db.execute("UPDATE studies SET status='interrupted' WHERE id=?",(sid,)); self.db.commit()
            raise
        return self.study_get(sid)
