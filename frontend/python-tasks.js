/* Versioned runtime Python proposals and artifacts. */
state.pythonTask=null;
const taskPanelBase=rightPanel;
rightPanel=function(job){
 const p=state.pythonTask;if(!p)return taskPanelBase(job);
 const controls=p.status==='code_review'?'<button class="btn" data-python-action="reject">Reject script</button><button class="btn primary" data-python-action="approve">Approve and run in Docker</button>':p.status==='result_review'&&!p.scene_error?'<button class="btn primary" data-python-action="accept">Accept output</button>':['failed','interrupted'].includes(p.status)?'<button class="btn" data-python-action="retry">Retry approved script</button>':'';
 return `<div class="panel-body"><div class="row">${badge(p.status.replaceAll('_',' '),'amber')}<button class="btn" data-python-back>Back to analysis</button></div><h3>${e(p.title)}</h3><p>${e(p.summary)}</p><p class="tiny muted">Version created ${new Date(p.created*1000).toLocaleString()} · ${p.parent_id?'Revision of a previous script':'New Python task'}</p>${p.error?`<div class="callout amber">${e(p.error)} Revise the request below to generate a new script.</div>`:''}${p.has_plot?`<img style="width:100%;height:auto" src="/api/python-tasks/${p.id}/image" alt="Generated Python plot awaiting engineering review">`:''}${p.scene_error?`<div class="callout amber">3D visualization could not be displayed: ${e(p.scene_error)}</div>`:''}${!p.scene_error&&p.output?.scene3d?`<iframe title="Interactive 3D result" src="/static/viewer3d.html?task=${encodeURIComponent(p.id)}" style="width:100%;height:450px;border:0"></iframe>`:''}${p.output?`<h3>Calculated output</h3>${p.output.summary?`<p>${e(p.output.summary)}</p>`:''}<details><summary>View structured output</summary><pre class="source-code">${e(JSON.stringify(p.output,null,2))}</pre></details><div class="callout">${p.scene_error?'Geometry validation failed. Revise the script before accepting this result.':'Docker execution completed. Output format was checked; engineering correctness requires your review.'}</div>`:''}<details ${p.status==='code_review'?'open':''}><summary>Python script and execution scope</summary><pre class="source-code">${e(p.code)}</pre><p class="tiny muted">Authorized analysis snapshot · no network · pinned image · 512 MB · 60 seconds · no host execution</p><p class="tiny muted">Image: ${e(p.image)}</p></details>${p.status==='running'?'<p>Running approved Python in Docker…</p>':''}<div class="row" style="margin-top:14px">${controls}${p.scene_error||p.error?'<button class="btn" data-python-revise>Revise failed output</button>':''}</div><div class="callout">Send a follow-up in the conversation to revise this script. Every new version requires approval.</div></div>`;
};
const taskConversationBase=conversationWorkbench;
pages.workbench=function(){
 let html=taskConversationBase();const items=state.conversation?.python_tasks||[];
 if(items.length)html+=`<div class="card"><h3>Python task versions</h3><div class="row">${items.map((p,i)=>`<button class="btn" data-python-open="${p.id}">${i+1}. ${e(p.title)} · ${e(p.status.replaceAll('_',' '))}</button>`).join('')}</div></div>`;
 return html;
};
const taskSendBase=sendMessage;
sendMessage=async function(){
 const text=state.draft.trim();if(!text)return;state.chatBusy=true;render();
 try{
  if(!state.conversation){state.conversation=await api('/conversations',{agent_id:state.activeAgent});location.hash='conversation='+state.conversation.id}
  const r=await api('/conversations/'+state.conversation.id+'/messages',{request:text,job_id:state.job?.id||null,parent_id:state.pythonTask?.id||null});
  state.conversation=r.conversation;state.draft='';state.revisionPrompt=false;
  if(r.job_id){state.job=await api('/jobs/'+r.job_id);state.tab='results'}
  if(r.python_task)state.pythonTask=r.python_task;
  await refresh();
 }finally{state.chatBusy=false;render()}
};
document.addEventListener('click',async ev=>{const b=ev.target.closest('button');if(!b)return;try{
 if(b.hasAttribute('data-python-revise')){state.draft='Revise this Python task to fix its validation or execution errors. Preserve my original requirements and use consistent units.';render();document.querySelector('#request')?.focus();return}
 if(b.dataset.pythonOpen){state.pythonTask=await api('/python-tasks/'+b.dataset.pythonOpen);render()}
 if(b.hasAttribute('data-python-back')){state.pythonTask=null;render()}
 if(b.dataset.pythonAction){b.disabled=true;state.pythonTask=await api('/python-tasks/'+state.pythonTask.id+'/action',{action:b.dataset.pythonAction,fingerprint:state.pythonTask.fingerprint});await refresh()}
 if(b.dataset.conversation||b.dataset.agentChat||b.dataset.chatJob||b.dataset.action==='new'){state.pythonTask=null;render()}
}catch(err){toast(err.message);b.disabled=false}});
setInterval(async()=>{if(state.pythonTask?.status==='running'){try{state.pythonTask=await api('/python-tasks/'+state.pythonTask.id);await refresh()}catch(e){toast('Unable to refresh task; its state is saved')}}},1200);

pages.tools=function(){return head('ENGINEERING CAPABILITIES','Tools','Register applications and modules for reviewed integration.')+`<div class="card"><h3>Register a capability</h3><label class="form-label">Name</label><input id="tool-name" class="text-input"><label class="form-label">What does it do?</label><textarea id="tool-description" class="text-input"></textarea><label class="form-label">Application or module location</label><input id="tool-location" class="text-input" placeholder="Local application path or service reference"><label class="form-label">Source folder reference (optional)</label><input id="tool-source" class="text-input" placeholder="Path to source for a future approved integration"><button class="btn primary" data-register-tool>Register tool</button><div class="callout">Registration stores references only. It does not read the folder or execute the application. A reviewed adapter and explicit access configuration are required before an agent can use it.</div></div><div class="card"><h3>Registered tools</h3>${(state.tools?.registered||[]).map(t=>`<h4>${e(t.name)}</h4><p>${e(t.description)}</p><p class="tiny muted">${e(t.location)}<br>Source: ${e(t.source_folder||'Not supplied')} · Awaiting adapter integration</p>`).join('')||'<p>No additional tools registered.</p>'}<h4>Bundled engineering adapter</h4><p>The synthetic data reader and released comparison remain available through the existing plugin and agent permissions.</p></div>`};
document.addEventListener('click',async ev=>{const b=ev.target.closest('button');if(!b)return;try{
 if(b.dataset.page==='tools'){state.tools=await api('/tools');render()}
 if(b.hasAttribute('data-register-tool')){await api('/tools',{name:document.querySelector('#tool-name').value,description:document.querySelector('#tool-description').value,location:document.querySelector('#tool-location').value,source_folder:document.querySelector('#tool-source').value});state.tools=await api('/tools');render();toast('Tool registered; adapter integration is still required')}
}catch(e){toast(e.message)}});
