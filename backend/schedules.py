"""Single-process persistent scheduler for explicitly approved released recipes."""
import hashlib, json, threading, time, uuid
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator
from pathlib import Path

UTC=timezone.utc
GRACE_SECONDS=60

class ScheduleConfig(BaseModel):
    model_config=ConfigDict(extra='forbid')
    name:str=Field(min_length=1,max_length=80)
    source_job:str
    agent_id:str
    skill_id:str='compare-runs'
    frequency:Literal['once','daily','weekly']='once'
    timezone:str=Field(min_length=1,max_length=80)
    start_local:str=Field(min_length=16,max_length=19)
    @field_validator('start_local')
    @classmethod
    def local_time(cls,value):
        d=datetime.fromisoformat(value)
        if d.tzinfo or d.second or d.microsecond: raise ValueError('Use a local date/time with minute precision, without UTC offset')
        return d.isoformat(timespec='minutes')
    @field_validator('timezone')
    @classmethod
    def zone(cls,value):
        try:ZoneInfo(value)
        except (ZoneInfoNotFoundError,ValueError) as exc:raise ValueError('Unknown IANA timezone; provision tzdata for Windows') from exc
        return value
    @field_validator('name')
    @classmethod
    def name_text(cls,value):
        if not value.strip():raise ValueError('Name must not be blank')
        return value.strip()

def utc_occurrence(local,zone):
    # Repeated fall-back hour: first occurrence only. Missing spring hour: skip.
    aware=local.replace(tzinfo=ZoneInfo(zone),fold=0)
    timestamp=aware.timestamp()
    if datetime.fromtimestamp(timestamp,ZoneInfo(zone)).replace(tzinfo=None)!=local:return None
    return timestamp

def next_due(config,after):
    start=datetime.fromisoformat(config['start_local'])
    if config['frequency']=='once':
        stamp=utc_occurrence(start,config['timezone'])
        return stamp if stamp is not None and stamp>after else None
    days=1 if config['frequency']=='daily' else 7
    today=datetime.fromtimestamp(after,ZoneInfo(config['timezone'])).date()
    count=max(0,(today-start.date()).days//days)
    for offset in range(count,count+370):
        stamp=utc_occurrence(start+timedelta(days=offset*days),config['timezone'])
        if stamp is not None and stamp>after:return stamp
    raise ValueError('Cannot find a valid future occurrence')

def signature(payload):
    return hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()

class SchedulesMixin:
    def init_schedules(self):
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS schedules(id TEXT PRIMARY KEY,config TEXT,approval TEXT,fingerprint TEXT,status TEXT,next_due REAL,created REAL,detail TEXT);
        CREATE TABLE IF NOT EXISTS schedule_runs(id INTEGER PRIMARY KEY,schedule_id TEXT,due REAL,job_id TEXT,outcome TEXT,detail TEXT,created REAL,UNIQUE(schedule_id,due));
        CREATE TABLE IF NOT EXISTS schedule_events(id INTEGER PRIMARY KEY,schedule_id TEXT,action TEXT,at REAL);
        ''');self.db.commit()
        self.scheduler_stop=threading.Event();self.scheduler_thread=None
        self.scheduler_error=None

    def recipe(self,config):
        a=self.agent_get(config['agent_id'])
        row=self.db.execute('SELECT * FROM skills WHERE id=?',(config['skill_id'],)).fetchone()
        if not row or row['status']!='released' or row['id'] not in a['skill_ids']:
            raise ValueError('Select a released skill assigned to this agent')
        if self.db.execute('SELECT id FROM authored_skills WHERE id=?',(row['id'],)).fetchone():raise ValueError('Authored Python skills require interactive review and cannot be scheduled')
        if row['job_id'] and self.get(row['job_id'])['extension']:
            raise ValueError('Scheduling currently supports released comparisons without generated Python')
        plan={'workflow':'compare','skill_id':row['id'],'skill_version':row['version'],'skill_name':row['name']}
        self.check_agent({'agent':a,'plan':plan},'compare')
        if not self.enabled():raise ValueError('Comparison plugin is disabled')
        root=Path(__file__).resolve().parents[1]
        import os
        files=[root/'backend/analysis.py',root/'backend/engine.py',root/'backend/schedules.py',root/'legacy/build'/('engineering-demo.exe' if os.name=='nt' else 'engineering-demo')]
        return {'agent':a,'plan':plan,'code_hashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
                'input_scope':'Current run-a.ewb and run-b.ewb through the C++ gateway',
                'data_root':str(self.data.resolve()),'evidence_root':str(self.artifacts.root),
                'max_active_runs':1,'automatic_job_retries':0,'export_timeout_seconds':10,
                'missed_run_policy':'skip','grace_seconds':GRACE_SECONDS,'result_review':True}

    def schedule_get(self,sid):
        with self.lock:
            row=self.db.execute('SELECT * FROM schedules WHERE id=?',(sid,)).fetchone()
            if not row:raise KeyError(sid)
            item=dict(row);item['config']=json.loads(row['config']);item['approval']=json.loads(row['approval'])
            item['runs']=[dict(r) for r in self.db.execute('SELECT r.*,j.status AS job_status FROM schedule_runs r LEFT JOIN jobs j ON j.id=r.job_id WHERE schedule_id=? ORDER BY due DESC LIMIT 50',(sid,))]
            item['events']=[dict(r) for r in self.db.execute('SELECT action,at FROM schedule_events WHERE schedule_id=? ORDER BY id',(sid,))]
            return item

    def schedule_list(self):
        with self.lock:return [self.schedule_get(r[0]) for r in self.db.execute('SELECT id FROM schedules ORDER BY created DESC')]

    def schedule_create(self,config,now=None):
        config=ScheduleConfig.model_validate(config).model_dump();now=time.time() if now is None else now
        source=self.get(config['source_job'])
        if source['status']!='accepted' or source['extension']:raise ValueError('Start from an accepted released comparison')
        start=utc_occurrence(datetime.fromisoformat(config['start_local']),config['timezone'])
        if start is None or start<=now:raise ValueError('Choose a future, valid local start time')
        with self.lock:
            if self.db.execute("SELECT COUNT(*) FROM schedules WHERE status NOT IN ('cancelled','complete')").fetchone()[0]>=100:
                raise ValueError('Local prototype supports at most 100 pending/active schedules')
            approval=self.recipe(config);sid=uuid.uuid4().hex
            fingerprint=signature({'config':config,'recipe':approval})
            self.db.execute('INSERT INTO schedules VALUES(?,?,?,?,?,?,?,?)',(sid,json.dumps(config),json.dumps(approval),fingerprint,'proposed',start,now,'Awaiting explicit recipe and schedule approval'));self.db.commit()
        return self.schedule_get(sid)

    def schedule_check(self,item):
        if self.recipe(item['config'])!=item['approval']:
            raise ValueError('Agent, skill, code or storage changed; create and approve a replacement schedule')

    def schedule_action(self,sid,action,fingerprint,now=None):
        now=time.time() if now is None else now
        with self.lock:
            s=self.schedule_get(sid)
            if fingerprint!=s['fingerprint']:raise ValueError('Stale schedule approval')
            if s['status'] in ('complete','cancelled'):raise ValueError('Schedule is already terminal')
            if action=='approve':
                if s['status']!='proposed':raise ValueError('Only a proposed schedule can be approved')
                self.schedule_check(s);status='active'
            elif action=='pause':
                if s['status']!='active':raise ValueError('Only an active schedule can be paused')
                status='paused'
            elif action=='resume':
                if s['status']!='paused':raise ValueError('Only a paused schedule can resume')
                self.schedule_check(s);status='active'
            elif action=='cancel':status='cancelled'
            else:raise ValueError('Unknown schedule action')
            self.db.execute('UPDATE schedules SET status=?,detail=? WHERE id=?',(status,action,sid))
            self.db.execute('INSERT INTO schedule_events(schedule_id,action,at) VALUES(?,?,?)',(sid,action,now));self.db.commit()
        return self.schedule_get(sid)

    def check_scheduled_job(self,state):
        if not state.get('schedule_id'):return
        with self.lock:
            s=self.schedule_get(state['schedule_id'])
            if s['status'] in ('cancelled','needs_review'):raise ValueError('Schedule cancelled or authorization invalidated')
            if state.get('schedule_fingerprint')!=s['fingerprint']:raise ValueError('Scheduled job authorization changed')
            self.schedule_check(s)

    def scheduler_tick(self,now=None,background=True):
        now=time.time() if now is None else now
        dispatch=[]
        with self.lock:
            due=list(self.db.execute("SELECT id FROM schedules WHERE status='active' AND next_due<=? ORDER BY next_due",(now,)))
            for row in due:
                s=self.schedule_get(row[0]);sid=s['id'];stamp=s['next_due']
                try:self.schedule_check(s)
                except (ValueError,KeyError,OSError) as exc:
                    self.db.execute("UPDATE schedules SET status='needs_review',detail=? WHERE id=?",(str(exc),sid));self.db.commit();continue
                following=next_due(s['config'],now)
                outcome='dispatched';detail='Approved released recipe; final result review required';jid=None
                active=self.db.execute("SELECT 1 FROM schedule_runs r JOIN jobs j ON j.id=r.job_id WHERE r.schedule_id=? AND j.status NOT IN ('accepted','rejected','changes_requested','cancelled') LIMIT 1",(sid,)).fetchone()
                if now-stamp>GRACE_SECONDS:outcome='missed';detail='Missed occurrence(s) skipped; no catch-up batch'
                elif active:outcome='skipped_overlap';detail='Prior run still executing, blocked, or awaiting review'
                else:jid=uuid.uuid4().hex
                value={'job_id':jid,'request':'Scheduled: '+s['config']['name'],'extension':False,
                       'agent':s['approval']['agent'],'plan':s['approval']['plan'],'plan_approved':True,
                       'schedule_id':sid,'schedule_fingerprint':s['fingerprint']}
                # Occurrence claim, initial job state and next due commit atomically.
                with self.db:
                    cursor=self.db.execute('INSERT OR IGNORE INTO schedule_runs(schedule_id,due,job_id,outcome,detail,created) VALUES(?,?,?,?,?,?)',(sid,stamp,jid,outcome,detail,now))
                    if cursor.rowcount and jid:
                        self.db.execute('INSERT INTO jobs(id,request,status,created,updated,error,extension,agent_json,initial_state) VALUES(?,?,?,?,?,?,?,?,?)',(jid,value['request'],'queued',now,now,None,0,json.dumps(value['agent']),json.dumps(value)))
                        self.db.execute('INSERT INTO events(job_id,at,stage,detail) VALUES(?,?,?,?)',(jid,now,'schedule','Executed under explicitly approved schedule '+sid))
                        dispatch.append((jid,value))
                    self.db.execute('UPDATE schedules SET next_due=?,status=?,detail=? WHERE id=?',(following,'active' if following is not None else 'complete',detail,sid))
        for jid,value in dispatch:
            if background:threading.Thread(target=self.drive,args=(jid,value),daemon=True).start()
            else:self.drive(jid,value)
        return [jid for jid,_ in dispatch]

    def start_scheduler(self):
        if self.scheduler_thread and self.scheduler_thread.is_alive():return
        self.scheduler_stop.clear()
        def loop():
            while not self.scheduler_stop.is_set():
                try:self.scheduler_tick();self.scheduler_error=None
                except Exception as exc:self.scheduler_error=str(exc)[:300]
                self.scheduler_stop.wait(1)
        self.scheduler_thread=threading.Thread(target=loop,daemon=True,name='workbench-scheduler');self.scheduler_thread.start()

    def stop_scheduler(self):
        self.scheduler_stop.set()
        if self.scheduler_thread:self.scheduler_thread.join(timeout=5)
