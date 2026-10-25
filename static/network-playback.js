'use strict';
const MediaNetwork={
 constrained(connection,mode){return mode==='low'||(mode==='auto'&&!!connection&&(connection.saveData||['slow-2g','2g','3g'].includes(connection.effectiveType)||Number(connection.downlink)>0&&connection.downlink<2));},
 variants(text,base){const lines=text.split(/\r?\n/),out=[];for(let i=0;i<lines.length;i++){const line=lines[i];if(!line.startsWith('#EXT-X-STREAM-INF:')||/\bAUDIO=/.test(line))continue;const bitrate=Number(line.match(/(?:^|[:,])BANDWIDTH=(\d+)/)?.[1]);let next=i+1;while(next<lines.length&&!lines[next].trim())next++;if(!bitrate||!lines[next]||lines[next].startsWith('#'))continue;try{const url=new URL(lines[next].trim(),base);if(url.protocol==='https:'&&!url.username&&!url.password)out.push({bitrate,url:url.href});}catch{}}return out.sort((a,b)=>a.bitrate-b.bitrate);},
 choose(variants,connection){const budget=Math.min(900000,Math.max(200000,(Number(connection?.downlink)||1)*1000000*0.6));return variants.filter(v=>v.bitrate<=budget).at(-1)||variants[0];}
};
(()=>{
 let cleanup=()=>{};const previousWatch=watch;
 const mode=()=>{try{return localStorage.getItem('mediaNetworkMode')||'auto';}catch{return 'auto';}};
 function light(){document.body.classList.toggle('low-data-mode',MediaNetwork.constrained(navigator.connection,mode()));}
 light();navigator.connection?.addEventListener('change',light);
 watch=function(item,live=false){cleanup();previousWatch(item,live);const video=document.querySelector('#modal video');if(!video)return;
  let disposed=false,attempts=0,timer,stall,wanted=false,reloading=false,revision=0,controller=null;
  const original=platformHTTPS(item.url);let source=original;
  const panel=document.createElement('div');panel.className='network-playback';const status=document.createElement('p');status.setAttribute('role','status');
  const label=document.createElement('label');label.textContent='Connection mode ';const select=document.createElement('select');select.setAttribute('aria-label','Connection mode');for(const [value,text] of [['auto','Auto'],['low','Low data'],['normal','Standard']]){const o=document.createElement('option');o.value=value;o.textContent=text;select.append(o);}select.value=mode();label.append(select);
  const retry=document.createElement('button');retry.textContent='Retry playback';retry.onclick=()=>{attempts=0;wanted=true;recover();};panel.append(label,retry,status);video.after(panel);
  function say(text){if(!disposed)status.textContent=text;}
  async function configure(){const seq=++revision;controller?.abort();const low=MediaNetwork.constrained(navigator.connection,select.value);video.preload=low?'none':'metadata';light();say(low?'Low-data mode. Lower quality is used when the source provides compatible HTTPS variants.':'Automatic stream quality is managed by your browser and the source.');
   let chosen=original;
   if(low&&/\.m3u8(?:$|\?)/i.test(original)&&video.canPlayType('application/vnd.apple.mpegurl')){
    controller=new AbortController();const request=controller;const timeout=setTimeout(()=>request.abort(),6000);
    try{const response=await fetch(original,{signal:request.signal,credentials:'omit',redirect:'error'});if(!response.ok||!response.body)throw Error();const reader=response.body.getReader();let size=0,text='';const decoder=new TextDecoder();while(true){const part=await reader.read();if(part.done)break;size+=part.value.length;if(size>262144){await reader.cancel();throw Error();}text+=decoder.decode(part.value,{stream:true});}const variants=MediaNetwork.variants(text,original),choice=MediaNetwork.choose(variants,navigator.connection);if(choice){chosen=choice.url;say('Low-data stream selected · '+Math.round(choice.bitrate/1000)+' kbps advertised bitrate.');}else say('No compatible lower-quality variant found. Using the original stream.');}catch{say('Source does not expose selectable quality here. Using browser-managed playback.');}finally{clearTimeout(timeout);}
   }
   if(disposed||seq!==revision)return;if(chosen!==source){const position=video.currentTime,resume=wanted;source=chosen;reload(position,resume);}
  }
  function reload(position,resume){reloading=true;video.src=source;video.load();if(!live&&position>0)video.addEventListener('loadedmetadata',()=>{if(!disposed&&Number.isFinite(video.duration))video.currentTime=Math.min(position,Math.max(0,video.duration-1));},{once:true});if(resume)video.play().then(()=>{reloading=false;}).catch(()=>{reloading=false;wanted=false;say('Press Play to resume.');});else reloading=false;}
  function recover(){clearTimeout(timer);clearTimeout(stall);if(disposed||!wanted)return;if(navigator.onLine===false){say('You are offline. Waiting for the connection to return.');return;}if(attempts>=3){say('Playback could not recover. Try Retry playback or another channel.');return;}attempts++;say('Reconnecting · attempt '+attempts+' of 3');reload(video.currentTime,true);}
  function schedule(){if(disposed||!wanted)return;clearTimeout(timer);if(attempts>=3){say('Playback unavailable. Try Retry playback or another channel.');return;}timer=setTimeout(recover,Math.min(12000,3000*2**attempts));}
  const play=()=>{wanted=true;},pause=()=>{if(!reloading){wanted=false;clearTimeout(timer);clearTimeout(stall);}},playing=()=>{clearTimeout(timer);clearTimeout(stall);say('Playing'+(MediaNetwork.constrained(navigator.connection,select.value)?' · Low data':'')+'.');},waiting=()=>{if(wanted){say('Buffering. A slower stream or a different channel may help.');clearTimeout(stall);stall=setTimeout(schedule,20000);}},offline=()=>{clearTimeout(timer);say('You are offline. Playback may continue from its existing buffer.');},online=()=>{if(wanted)recover();},ended=()=>{wanted=false;clearTimeout(timer);};
  const listeners={play,pause,playing,waiting,stalled:waiting,error:schedule,ended};Object.entries(listeners).forEach(([event,fn])=>video.addEventListener(event,fn));window.addEventListener('offline',offline);window.addEventListener('online',online);
  select.onchange=()=>{try{localStorage.setItem('mediaNetworkMode',select.value);}catch{}configure();};const change=()=>configure();navigator.connection?.addEventListener('change',change);configure();
  cleanup=()=>{disposed=true;++revision;controller?.abort();clearTimeout(timer);clearTimeout(stall);Object.entries(listeners).forEach(([event,fn])=>video.removeEventListener(event,fn));window.removeEventListener('offline',offline);window.removeEventListener('online',online);navigator.connection?.removeEventListener('change',change);};
 };
 document.querySelector('#modal').addEventListener('close',()=>cleanup());
})();
