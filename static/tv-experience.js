'use strict';
(()=>{
 const read=(key,fallback)=>{try{return JSON.parse(localStorage.getItem(key))??fallback;}catch{return fallback;}};
 const write=(key,value)=>{try{localStorage.setItem(key,JSON.stringify(value));}catch{}};
 const key=name=>'mediaTV:'+ (me.user?.id||'guest')+':'+profile+':'+name;
 const prefs=()=>read(key('preferences'),{resume:true,volume:0.7,muted:false,fit:'contain',captions:false});
 let current=null,previous=null,sleepTimer=null,sleepAt=0,tuneRequest=0;
 const status=text=>{const modal=document.querySelector('#modal[open]');if(!modal){note(text);return;}let message=modal.querySelector('.tv-viewing-status');if(!message){message=document.createElement('p');message.className='tv-viewing-status';message.setAttribute('role','status');modal.append(message);}message.textContent=text;};
 function stop(){document.querySelectorAll('video').forEach(v=>v.pause());}
 async function tune(id){const request=++tuneRequest;try{const g=await api('guide');if(request!==tuneRequest)return;const c=g.channels.find(c=>c.id===id);if(c)watch({...c,title:c.name},true);else status('This channel is no longer available. Open the guide to choose another.');}catch(e){status(e.message);}}
 async function info(){if(!current)return;try{const g=await api('guide'),now=Date.now()/1000,programs=g.programs.filter(p=>p.channel_id===current.id).sort((a,b)=>a.start-b.start),on=programs.find(p=>p.start<=now&&p.end>now),next=programs.find(p=>p.start>now);status(current.title+' · Now: '+(on?.title||'Schedule unavailable')+' · Next: '+(next?.title||'Schedule unavailable'));}catch(e){status(e.message);}}
 const beforeWatch=watch;
 watch=function(item,live=false){
  if(current?.live&&live&&current.id!==item.id)previous=current.id;
  current={id:item.id,live,title:item.title||item.name};beforeWatch(item,live);
  const video=document.querySelector('#modal video');if(!video)return;
  const owner=key('last'),settings=prefs();video.volume=Math.max(0,Math.min(1,Number(settings.volume)||0));video.muted=!!settings.muted;video.style.objectFit=settings.fit;
  const remember=()=>{if(!Number.isInteger(item.id))return;write(owner,{id:item.id,live,position:live?0:video.currentTime,updated:Date.now()});};
  video.addEventListener('playing',remember);let saved=0;video.addEventListener('timeupdate',()=>{if(!video.paused&&Math.abs(video.currentTime-saved)>5){saved=video.currentTime;remember();}});
  video.addEventListener('volumechange',()=>{if(key('last')!==owner)return;const p=prefs();p.volume=video.volume;p.muted=video.muted;write(key('preferences'),p);});
  video.addEventListener('loadedmetadata',()=>{for(const track of video.textTracks)track.mode=settings.captions?'showing':'disabled';});
  const bar=document.createElement('div');bar.className='actions';
  const button=(title,fn)=>{const b=document.createElement('button');b.textContent=title;b.onclick=fn;bar.append(b);return b;};
  if(live){button('↩ Previous channel',()=>previous?tune(previous):status('No previous channel yet.'));const favorite=button('☆ Favorite channel',()=>{let ids=read(key('favorites'),[]);ids=ids.includes(item.id)?ids.filter(id=>id!==item.id):[...ids,item.id];write(key('favorites'),ids);favorite.textContent=ids.includes(item.id)?'★ Favorite saved':'☆ Favorite channel';});favorite.textContent=read(key('favorites'),[]).includes(item.id)?'★ Favorite saved':'☆ Favorite channel';button('Now / Next',info);}
  button('TV settings',settingsView);video.after(bar);
 };
 async function restore(){const p=prefs(),last=read(key('last'),null);if(p.resume===false||!last||document.querySelector('dialog[open]'))return;if(me.profiles.find(p=>p.id===profile)?.kids)return;
  const owner=key('last');try{const items=last.live?(await api('guide')).channels:await api('catalog?profile_id='+profile);if(owner!==key('last')||document.querySelector('dialog[open]'))return;const item=items.find(i=>i.id===last.id);if(!item){status('Your last programme is unavailable. Choose another from Home or the guide.');return;}watch({...item,title:item.title||item.name},last.live);const v=document.querySelector('#modal video');if(!v)return;
   if(!last.live&&last.position>0)v.addEventListener('loadedmetadata',()=>{if(Number.isFinite(v.duration)&&last.position<v.duration-5)v.currentTime=last.position;},{once:true});
   v.play().catch(()=>status('Welcome back. Press Play or OK to resume your last programme.'));
  }catch{status('Unable to restore your last programme. Your channel guide is still available.');}}
 function settingsView(){
  let dialog=document.querySelector('#tv-settings');if(!dialog){dialog=document.createElement('dialog');dialog.id='tv-settings';document.body.append(dialog);}
  const p=prefs();dialog.innerHTML='<h2>Television settings</h2><p>Saved for this profile on this device.</p><label><input id="tv-start-last" type="checkbox" '+(p.resume!==false?'checked':'')+'> Open last watched programme on startup</label><p><label>Picture fit <select id="tv-fit"><option value="contain">Fit (original ratio)</option><option value="cover">Fill (crop edges)</option></select></label></p><label><input id="tv-captions" type="checkbox" '+(p.captions?'checked':'')+'> Captions when provided by the source</label><p><label>Sleep timer <select id="tv-sleep"><option value="0">Off</option><option value="15">15 minutes</option><option value="30">30 minutes</option><option value="60">60 minutes</option><option value="90">90 minutes</option></select></label></p><p id="tv-sleep-status"></p><div class="actions"><button id="tv-save">Save</button><button id="tv-clear-history">Forget last watched</button><button id="tv-favorites">Favorite channels</button><button id="tv-settings-close">Close</button></div><p>The sleep timer pauses playback while this app remains open. It does not switch off the TV. Picture quality, audio languages and captions depend on source tracks and device support.</p>';
  dialog.querySelector('#tv-fit').value=p.fit||'contain';dialog.querySelector('#tv-sleep-status').textContent=sleepAt?'Playback will pause at '+new Date(sleepAt).toLocaleTimeString():'';
  dialog.querySelector('#tv-save').onclick=()=>{const fresh=prefs();fresh.resume=dialog.querySelector('#tv-start-last').checked;fresh.fit=dialog.querySelector('#tv-fit').value;fresh.captions=dialog.querySelector('#tv-captions').checked;write(key('preferences'),fresh);document.querySelectorAll('video').forEach(v=>{v.style.objectFit=fresh.fit;for(const track of v.textTracks)track.mode=fresh.captions?'showing':'disabled';});clearTimeout(sleepTimer);const minutes=Number(dialog.querySelector('#tv-sleep').value);sleepAt=minutes?Date.now()+minutes*60000:0;if(minutes)sleepTimer=setTimeout(()=>{stop();sleepAt=0;status('Sleep timer finished. Playback paused.');},minutes*60000);dialog.close();};
  dialog.querySelector('#tv-clear-history').onclick=()=>{try{localStorage.removeItem(key('last'));}catch{}status('Last watched programme forgotten.');};
  dialog.querySelector('#tv-favorites').onclick=async()=>{dialog.close();stop();document.querySelector('#modal[open]')?.close();try{const g=await api('guide'),ids=read(key('favorites'),[]);document.querySelector('#view').innerHTML='<h1>Favorite channels</h1><div id="tv-favorite-list"></div>';const list=document.querySelector('#tv-favorite-list');for(const c of g.channels.filter(c=>ids.includes(c.id))){const b=document.createElement('button');b.textContent='CH '+(c.number||c.id)+' · '+c.name;b.onclick=()=>tune(c.id);list.append(b);}if(!list.children.length)list.textContent='No available favorites. Use Favorite channel while watching live TV.';}catch(e){status(e.message);}};
  dialog.querySelector('#tv-settings-close').onclick=()=>dialog.close();dialog.showModal();dialog.querySelector('#tv-start-last').focus();
 }
 const settings=document.createElement('button');settings.textContent='TV settings';settings.onclick=settingsView;document.querySelector('header').append(settings);
 const startup=()=>{if(!['/install','/build-a-station','/station'].includes(location.pathname)&&!new URLSearchParams(location.search).has('video')&&!new URLSearchParams(location.search).has('market_order'))restore();};
 document.addEventListener('media-ready',startup);if(window.mediaReady)startup();
 document.querySelector('#profiles').addEventListener('change',()=>{++tuneRequest;stop();document.querySelector('#modal[open]')?.close();current=null;previous=null;clearTimeout(sleepTimer);sleepAt=0;});
 document.querySelector('#account').addEventListener('click',stop);
 document.addEventListener('keydown',e=>{if(localStorage.getItem('mediaTVMode')!=='on'||/INPUT|TEXTAREA|SELECT/.test(document.activeElement?.tagName))return;if(e.key==='LastChannel'||e.key==='GoBack'||e.keyCode===10190){e.preventDefault();if(previous)tune(previous);}else if(e.key==='Info'||e.keyCode===457){e.preventDefault();info();}else if(e.key==='Guide'||e.keyCode===458){e.preventDefault();stop();document.querySelector('#modal[open]')?.close();navigate('Live TV').catch(e=>status(e.message));}},true);
})();
