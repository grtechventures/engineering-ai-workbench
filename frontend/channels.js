state.channels=null;
state.channelEdit=null;
const channelProviders=['Microsoft Teams','Slack','Other enterprise platform','Local test'];
pages.channels=function(){
 const c=state.channels,d=state.channelEdit||{provider:'Microsoft Teams',notifications:true};
 return head('SETTINGS','Channels','Configure enterprise communication entry points, starting with Microsoft Teams.')+
 `<div class="callout"><strong>Offline setup only</strong><p>Save a draft and preview a sample notification locally. Live delivery, incoming requests and result sharing are not connected. No internet access is enabled.</p></div>`+
 (!c?`<div class="panel panel-body"><p>${e(state.channelsError||'Loading channel settings…')}</p><button class="btn" data-channel-reload>Reload settings</button></div>`:
 `<section class="panel panel-body"><h3>${d.id?'Edit':'Add'} channel</h3>
 <label class="form-label" for="channel-provider">Platform</label><select class="select" id="channel-provider">${channelProviders.map(x=>`<option ${x===d.provider?'selected':''}>${e(x)}</option>`).join('')}</select>
 <label class="form-label" for="channel-name">Configuration name</label><input class="text-input" id="channel-name" maxlength="100" value="${e(d.name||'')}" placeholder="Engineering team notifications">
 <label class="form-label" for="channel-org">Tenant or workspace reference</label><input class="text-input" id="channel-org" maxlength="200" value="${e(d.organization||'')}" placeholder="Reference only; no credentials">
 <label class="form-label" for="channel-destination">Team and channel reference</label><input class="text-input" id="channel-destination" maxlength="200" value="${e(d.destination||'')}" placeholder="Team / channel name or identifier">
 <label class="form-label" for="channel-identities">Intended allowed users or groups</label><textarea class="text-input" id="channel-identities" maxlength="1000">${e(d.allowed_identities||'')}</textarea>
 <p class="tiny muted">Planning references only. Identity mapping and access enforcement require a live adapter. Do not enter passwords, tokens, or webhook URLs.</p>
 <h4>Requested capabilities for future connection</h4>${[['notifications','Job-status notifications'],['requests','Incoming analysis requests'],['results','Result sharing']].map(([k,l])=>`<label class="form-label"><input type="checkbox" id="channel-${k}" ${d[k]?'checked':''}> ${l}</label>`).join('')}
 <p>These choices record intent; they do not activate a transport or grant access. Script and result reviews remain in the Workbench.</p>
 <button class="btn primary" data-channel-save>Save draft configuration</button><button class="btn" data-channel-new>Clear form</button></section>
 <h3>Saved channels</h3>${c.profiles.length?c.profiles.map(x=>`<section class="card"><h3>${e(x.name)}</h3><p>${e(x.provider)} · ${badge('Not connected','amber')}</p><p>${e(x.organization)}${x.destination?' / '+e(x.destination):''}</p><button class="btn" data-channel-edit="${e(x.id)}">Edit</button><button class="btn" data-channel-preview="${e(x.id)}">Preview locally</button></section>`).join(''):'<p>No channel configurations saved yet.</p>'}`)+
 (state.channelPreview?`<section class="panel panel-body" role="status"><h3>Local test preview</h3><p>${e(state.channelPreview.message)}</p><blockquote>${e(state.channelPreview.preview)}</blockquote><p>${e(state.channelPreview.requests)}</p><p>${e(state.channelPreview.results)}</p></section>`:'');
};
async function loadChannels(){try{state.channels=await api('/channels');state.channelsError=''}catch(err){state.channels=null;state.channelsError='Channel setup is unavailable. If this service predates the update, restart Workbench and reload.'}render()}
document.addEventListener('click',async ev=>{const b=ev.target.closest('button');if(!b)return;try{
 if(b.dataset.page==='channels'||b.hasAttribute('data-channel-reload'))await loadChannels();
 if(b.hasAttribute('data-channel-new')){state.channelEdit=null;state.channelPreview=null;render()}
 if(b.dataset.channelEdit){state.channelEdit=state.channels.profiles.find(x=>x.id===b.dataset.channelEdit);state.channelPreview=null;render()}
 if(b.hasAttribute('data-channel-save')){b.disabled=true;const value={};for(const [k,id] of [['name','name'],['provider','provider'],['organization','org'],['destination','destination'],['allowed_identities','identities']])value[k]=document.querySelector('#channel-'+id).value;for(const k of ['notifications','requests','results'])value[k]=document.querySelector('#channel-'+k).checked;await api('/channels'+(state.channelEdit?.id?'/'+state.channelEdit.id:''),value);state.channelEdit=null;state.channelPreview=null;await loadChannels();toast('Draft saved. No external connection enabled.')}
 if(b.dataset.channelPreview){state.channelPreview=await api('/channels/'+b.dataset.channelPreview+'/preview',{});render();document.querySelector('[role="status"]')?.scrollIntoView({block:'nearest'})}
}catch(err){toast(err.message);b.disabled=false}});
