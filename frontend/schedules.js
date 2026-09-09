'use strict';
state.schedules=[];state.scheduleForm=null;state.scheduleHistory=new Set();state.scheduleNotified=new Set();
const beforeScheduleEvidence=evidence;
evidence=function(j){return beforeScheduleEvidence(j)+(j.status==='accepted'&&!j.extension?'<div style="margin-top:16px"><button class="btn" data-schedule-action="new">Schedule this workflow</button></div>':'')};
pages.schedules=function(){
 const f=state.scheduleForm,agents=state.data.agents.filter(a=>a.enabled);
 return head('RECURRING ANALYSIS','Schedules','Run an approved recipe at a specified time. Results still require review.')+
 `<div class="callout">${state.data.scheduler?.running?'Scheduler is running while this service is open.':'Scheduler is not running.'} Missed runs are skipped. A prior run awaiting review blocks the next occurrence. ${state.data.scheduler?.error?e(state.data.scheduler.error):''}</div>`+
 (f?`<section class="panel panel-body" style="margin:20px 0"><h3>Schedule an accepted comparison</h3><p>Current Run A and Run B will be read at each occurrence. No model re-planning or generated Python. Approve the fixed recipe separately after saving.</p><div class="grid2"><div><label class="form-label" for="schedule-name">Schedule name</label><input id="schedule-name" class="text-input" maxlength="80" value="Recurring run comparison"><label class="form-label" for="schedule-agent">Agent</label><select id="schedule-agent" class="select">${agents.map(a=>`<option value="${a.id}" ${a.id===f.agent_id?'selected':''}>${e(a.name)}</option>`).join('')}</select><label class="form-label" for="schedule-skill">Released recipe</label><select id="schedule-skill" class="select">${state.data.catalog.skills.filter(s=>s.status==='released').map(s=>`<option value="${s.id}">${e(s.name)}</option>`).join('')}</select></div><div><label class="form-label" for="schedule-frequency">Frequency</label><select id="schedule-frequency" class="select"><option value="once">Once</option><option value="daily">Daily</option><option value="weekly">Weekly</option></select><label class="form-label" for="schedule-timezone">Timezone (IANA name)</label><input id="schedule-timezone" class="text-input" value="UTC" placeholder="America/Chicago"><label class="form-label" for="schedule-start">First local date and time</label><input id="schedule-start" class="text-input" type="datetime-local" value="${new Date(Date.now()+300000).toISOString().slice(0,16)}"><p class="tiny muted">Time is interpreted in the timezone above. Weekly repeats on the selected weekday. Daylight-saving gaps are skipped; repeated times run once.</p></div></div><div class="row" style="margin-top:18px"><button class="btn primary" data-schedule-action="save">Save proposal</button><button class="btn" data-schedule-action="close">Cancel</button></div></section>`:'')+
 `<button class="btn" style="margin:18px 0" data-schedule-action="refresh">Refresh schedules</button><div class="stack">${state.schedules.map(s=>`<section class="panel panel-body"><div class="row"><h3>${e(s.config.name)}</h3>${badge(s.status,s.status==='active'?'green':'neutral')}</div><p>${e(s.config.frequency)} · ${e(s.config.timezone)} · starts ${e(s.config.start_local.replace('T',' '))}</p><p>Agent: ${e(s.approval.agent.name)} · Recipe: ${e(s.approval.plan.skill_name)} · Current workspace inputs</p><p class="tiny muted">Next occurrence: ${s.next_due?e(new Date(s.next_due*1000).toLocaleString('en-US',{timeZone:s.config.timezone}))+' ('+e(s.config.timezone)+')':'None'} · ${e(s.detail)}</p><p class="tiny muted">One active run · no automatic whole-job retries · final result review required. Agent, recipe, code or storage changes require a replacement schedule.</p><div class="row">${s.status==='proposed'?`<button class="btn primary" data-schedule-id="${s.id}" data-schedule-action="approve">Approve schedule and recipe</button>`:''}${s.status==='active'?`<button class="btn" data-schedule-id="${s.id}" data-schedule-action="pause">Pause</button>`:''}${s.status==='paused'?`<button class="btn" data-schedule-id="${s.id}" data-schedule-action="resume">Resume</button>`:''}${!['complete','cancelled'].includes(s.status)?`<button class="btn" data-schedule-id="${s.id}" data-schedule-action="cancel">Cancel schedule</button>`:''}</div><details data-schedule-history="${s.id}" ${state.scheduleHistory.has(s.id)?'open':''} style="margin-top:15px"><summary>Run history (${s.runs.length}, latest 50)</summary><table class="table"><thead><tr><th>Due (UTC)</th><th>Outcome</th><th>Analysis</th></tr></thead><tbody>${s.runs.map(r=>`<tr><td>${e(new Date(r.due*1000).toISOString())}</td><td>${e(r.job_status||r.outcome)}<small class="muted"> · ${e(r.detail)}</small></td><td>${r.job_id?`<button class="btn" data-job="${r.job_id}">Open result</button>`:'—'}</td></tr>`).join('')}</tbody></table></details></section>`).join('')||'<div class="panel panel-body">No schedules yet. Open an accepted comparison, then choose Evidence → Schedule this workflow.</div>'}</div>`;
};
document.addEventListener('click',async ev=>{
 const b=ev.target.closest('button');if(!b)return;
 if(b.dataset.page==='schedules'){try{state.schedules=await api('/schedules');render()}catch(err){toast(err.message)}return}
 const action=b.dataset.scheduleAction;if(!action)return;b.disabled=true;
 try{
  if(action==='new'){state.scheduleForm={source_job:state.job.id,agent_id:state.job.agent?.id};state.page='schedules';state.schedules=await api('/schedules');render();return}
  if(action==='close'){state.scheduleForm=null;render();return}
  if(action==='save'){
   await api('/schedules',{source_job:state.scheduleForm.source_job,name:document.querySelector('#schedule-name').value,agent_id:document.querySelector('#schedule-agent').value,skill_id:document.querySelector('#schedule-skill').value,frequency:document.querySelector('#schedule-frequency').value,timezone:document.querySelector('#schedule-timezone').value,start_local:document.querySelector('#schedule-start').value});
   state.scheduleForm=null;toast('Proposal saved. Approve its recipe and timing to activate it.');
  }
  if(b.dataset.scheduleId){const s=state.schedules.find(s=>s.id===b.dataset.scheduleId);await api('/schedules/'+s.id+'/action',{action,fingerprint:s.fingerprint})}
  state.schedules=await api('/schedules');await refresh();
 }catch(err){toast(err.message)}finally{b.disabled=false}
});
document.addEventListener('toggle',ev=>{
 const id=ev.target.dataset?.scheduleHistory;if(!id)return;
 if(ev.target.open)state.scheduleHistory.add(id);else state.scheduleHistory.delete(id);
},true);
setInterval(async()=>{
 if(!state.data||state.scheduleForm)return;
 try{
  state.schedules=await api('/schedules');
  for(const s of state.schedules)for(const r of s.runs){
   const key=r.job_id+':'+r.job_status;
   if(['result_review','blocked','interrupted'].includes(r.job_status)&&!state.scheduleNotified.has(key)){
    state.scheduleNotified.add(key);toast('A scheduled analysis needs attention. Open Schedules to review its result or error.');
   }
  }
  if(state.page==='schedules')await refresh();
 }catch(err){if(state.page==='schedules')toast('Scheduler connection interrupted; reload when the service is available.')}
},10000);
