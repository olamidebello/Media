'use strict';
liveGuide=async function(){
 const guide=await api('guide');window.mediaGuideArtwork=new Map(guide.channels.map(c=>[String(c.id),c]));let limit=100,category='';
 $('#view').innerHTML='<section class="channel-guide"><div class="guide-screen"><span class="guide-live">LIVE TV</span><h1>Your channels. One place.</h1><p>Select a channel below to start watching.</p></div><div class="guide-categories" role="group" aria-label="Channel categories"></div><div class="actions"><input id="channel-search" aria-label="Find a channel" placeholder="Search channels or enter a number"><button id="reload-guide">Refresh</button></div><p id="channel-count" class="muted"></p><div id="guide-rows"></div><button id="more-channels" hidden>Show more channels</button></section>';
 const cats=['All',...new Set(guide.channels.map(c=>c.category))];
 function draw(){const now=Date.now()/1000,term=$('#channel-search').value.toLowerCase();const list=guide.channels.filter(c=>(!category||c.category===category)&&(c.name.toLowerCase().includes(term)||String(c.number||c.id)===term));
 $('.guide-categories').innerHTML=cats.map(x=>'<button class="'+((category||'All')===x?'selected':'')+'" aria-pressed="'+((category||'All')===x)+'">'+esc(x)+'</button>').join('');$('.guide-categories').querySelectorAll('button').forEach(b=>b.onclick=()=>{category=b.textContent==='All'?'':b.textContent;limit=100;draw();});
 $('#channel-count').textContent=list.length+' channels';
 $('#guide-rows').innerHTML=list.slice(0,limit).map(c=>{const p=guide.programs.find(p=>p.channel_id===c.id&&p.start<=now&&p.end>now),left=p?Math.ceil((p.end-now)/60):0,percent=p?Math.max(0,Math.min(100,100*(now-p.start)/(p.end-p.start))):0;return '<article class="guide-channel"><span class="guide-station"><strong>'+esc(c.name)+'</strong><small>CH '+esc(c.number||c.id)+'</small></span><button class="guide-tune" data-channel="'+c.id+'" aria-label="Watch '+esc(c.name)+'"><span class="guide-thumb" aria-hidden="true">▶</span><span class="guide-description"><strong>'+esc(p?p.title:c.name)+'</strong><span class="guide-meta">'+(p?esc(left>=60?Math.floor(left/60)+'h '+left%60+'m left':left+'m left'):'Live · '+esc(c.category))+'</span>'+(p?'<progress max="100" value="'+percent+'" aria-label="Program progress"></progress>':'<small>Schedule unavailable</small>')+'</span></button><button class="guide-info" data-info="'+c.id+'" aria-label="Information about '+esc(c.name)+'">ⓘ</button></article>';}).join('')||'<p>No matching channels.</p>';
 $('#more-channels').hidden=list.length<=limit;
 document.querySelectorAll('[data-channel]').forEach(b=>b.onclick=()=>{const c=guide.channels.find(c=>c.id===Number(b.dataset.channel));watch({...c,title:c.name},true);});
 document.querySelectorAll('[data-info]').forEach(b=>b.onclick=()=>{const c=guide.channels.find(c=>c.id===Number(b.dataset.info));modal('<h2>'+esc(c.name)+'</h2><p>Channel '+esc(c.number||c.id)+' · '+esc(c.category)+'</p>'+guide.programs.filter(p=>p.channel_id===c.id&&p.end>now).slice(0,6).map(p=>'<p>'+esc(new Date(p.start*1000).toLocaleString())+' · '+esc(p.title)+'</p>').join('')+'<button id="guide-info-watch">Watch live</button>');$('#guide-info-watch').onclick=()=>watch({...c,title:c.name},true);});}
 $('#channel-search').oninput=()=>{limit=100;draw();};$('#reload-guide').onclick=run(()=>liveGuide());$('#more-channels').onclick=()=>{limit+=100;draw();};draw();
};
(()=>{const bar=document.createElement('nav');bar.className='mobile-bottom';bar.setAttribute('aria-label','Main navigation');bar.innerHTML=[['Home','⌂'],['Live TV','◉'],['Search','⌕'],['Account','◎']].map(([name,icon])=>'<button data-bottom="'+name+'"><span aria-hidden="true">'+icon+'</span>'+name+'</button>').join('');document.body.append(bar);bar.querySelectorAll('button').forEach(b=>b.onclick=run(async()=>{const n=b.dataset.bottom;if(n==='Account')auth();else{await navigate(n);if(n==='Search')$('#search').focus();}}));})();

// Start in the same user gesture, after player preferences and recovery listeners attach.
(()=>{
 const openPlayer=watch;
 watch=function(item,live=false){
  openPlayer(item,live);
  const video=document.querySelector('#modal video');
  if(!video)return;
  const feedback=document.createElement('p');feedback.setAttribute('role','status');video.after(feedback);
  const start=()=>{try{const pending=video.play();if(pending&&pending.catch)pending.catch(()=>{if(video.isConnected&&document.querySelector('#modal[open]'))feedback.textContent='Press Play to start. Your browser or this source prevented automatic playback.';});}catch{feedback.textContent='Press Play to start playback.';}};
  video.addEventListener('playing',()=>{feedback.textContent='';});
  start();
 };
})();
