'use strict';
// Additional capabilities stay behind project knowledge and result actions.
const originalKnowledge=pages.knowledge;
pages.knowledge=()=>originalKnowledge()+`<section class="panel panel-body" style="margin-top:20px"><h3>Search approved knowledge</h3><p class="subtitle">Matching notes are retrieved into local conversations. Proposed and retired notes are excluded.</p><input id="knowledge-query" class="text-input" aria-label="Search project knowledge" placeholder="Search method conventions…"><button class="btn" data-workspace="search">Search</button><div id="knowledge-matches"></div></section>`;
const previousEvidence=evidence;
evidence=function(j){return `<div class="row" style="margin-bottom:18px"><button class="btn" data-workspace="replay-snapshot">Replay saved inputs</button><button class="btn" data-workspace="replay-current">Run with current inputs</button>${j.status==='accepted'&&!j.extension?'<button class="btn" data-workspace="study-open">Explore smoothing parameters</button>':''}</div><p class="tiny muted">Replay creates a linked job with fresh reviews and the current method. The original remains available.</p>`+previousEvidence(j)};
const previousConversation=pages.workbench;
pages.workbench=()=>previousConversation()+referencePanel()+studyPanel();
const previousGuided=pages.workflows;
pages.workflows=()=>previousGuided()+studyPanel();
function referencePanel(){
 const refs=state.conversation?.references?.[0]?.refs||[];
 return refs.length?`<details class="panel panel-body" style="margin-top:18px"><summary>Retrieved ${refs.length} reviewed reference(s)</summary>${refs.map(r=>`<p>[${e(r.id.slice(0,8))}] ${e(r.text)}<br><small>${e(r.source)} · revision ${r.revision}</small></p>`).join('')}<p class="tiny muted">References retrieved for the latest request; inclusion does not prove that model prose used them correctly.</p></details>`:'';
}
function studyPanel(){
 if(!state.studyForm&&!state.study)return '';
 const s=state.study;
 if(state.studyForm)return `<section class="panel panel-body" style="margin-top:20px"><h3>Explore smoothing parameters</h3><p>Run a bounded study using released code. Compare distortion and roughness; lower roughness is not proof of better engineering accuracy.</p><label class="form-label" for="study-windows">Odd window sizes (up to 8, between 1 and 21)</label><input id="study-windows" class="text-input" value="1,3,5,9"><label class="form-label" for="study-budget">Maximum run time in seconds (1–10)</label><input id="study-budget" class="text-input" type="number" min="1" max="10" value="5"><div class="row"><button class="btn primary" data-workspace="study-propose">Propose study</button><button class="btn" data-workspace="study-close">Close</button></div></section>`;
 return `<section class="panel panel-body" style="margin-top:20px"><div class="row"><h3>Smoothing sensitivity study</h3>${statusBadge(s.status)}</div><p>${e(s.payload.objective)}</p><p class="tiny muted">${s.payload.trials} trials · ${s.payload.budget_seconds} second budget · windows ${e(s.payload.windows.join(', '))}</p>${s.result?`<table class="table"><thead><tr><th>Window</th><th>Distortion RMSE</th><th>Roughness RMS</th><th>Reference</th></tr></thead><tbody>${s.result.trials.map(t=>`<tr><td>${t.window}</td><td>${t.distortion_rmse.toFixed(6)}</td><td>${t.roughness_rms.toFixed(6)}</td><td>${t.reference_passed?'Passed':'Failed'}</td></tr>`).join('')}</tbody></table><p>${e(s.result.interpretation)}</p><p class="tiny muted">Stop reason: ${e(s.result.stop_reason)} · units: ${e(s.result.units.y)}</p><a class="btn" href="/api/studies/${s.id}/report" download>Download study evidence</a>`:''}<div class="row" style="margin-top:12px">${['plan_review','interrupted','result_review'].includes(s.status)?`<button class="btn primary" data-workspace="study-approve">${s.status==='result_review'?'Accept study results':'Approve bounded execution'}</button><button class="btn" data-workspace="study-cancel">Cancel study</button>`:''}<button class="btn" data-workspace="study-close">Close</button></div></section>`;
}
const previousJobs=pages.jobs;
pages.jobs=()=>previousJobs()+`<section class="panel panel-body" style="margin-top:20px"><h3>Parameter studies</h3><button class="btn" data-workspace="studies-load">Load saved studies</button>${(state.studies||[]).map(s=>`<div class="row" style="margin-top:12px">${statusBadge(s.status)}<span>${s.payload.trials} trials · ${new Date(s.created*1000).toLocaleString()}</span><button class="btn" data-study-id="${s.id}">Open study</button></div>`).join('')}</section>`;
document.addEventListener('click',async ev=>{
 const b=ev.target.closest('button');if(!b)return;
 const action=b.dataset.workspace;
 if(!action&&!b.dataset.studyId)return;
 b.disabled=true;
 try{
  if(b.dataset.studyId){state.study=state.studies.find(s=>s.id===b.dataset.studyId);state.studyForm=false;state.page='workbench';render();return}
  if(action==='search'){
   const matches=await api('/knowledge/search?q='+encodeURIComponent(document.querySelector('#knowledge-query').value));
   document.querySelector('#knowledge-matches').innerHTML=matches.map(r=>`<p>${e(r.text)}<br><small>${e(r.source)} · revision ${r.revision}</small></p>`).join('')||'<p>No approved matches.</p>';
  }
  if(action.startsWith('replay-')){const r=await api('/jobs/'+state.job.id+'/replay',{mode:action==='replay-snapshot'?'snapshot':'current'});await openJob(r.id);toast('Created a linked analysis. Fresh reviews are required.')}
  if(action==='study-open'){state.study=null;state.studyForm=true;render()}
  if(action==='study-close'){state.study=null;state.studyForm=false;render()}
  if(action==='study-propose'){
   state.study=await api('/studies',{job_id:state.job.id,windows:document.querySelector('#study-windows').value.split(',').map(x=>Number(x.trim())),budget_seconds:Number(document.querySelector('#study-budget').value)});
   state.studyForm=false;render();
  }
  if(action==='study-approve'||action==='study-cancel'){
   state.study=await api('/studies/'+state.study.id+'/action',{action:action==='study-approve'?'approve':'cancel',fingerprint:state.study.fingerprint});render();
  }
  if(action==='studies-load'){state.studies=await api('/studies');render()}
 }catch(error){toast(error.message)}finally{b.disabled=false}
});
