'use strict';
(()=>{
 let returnFocus;
 async function openProvider(url,label){
  try{const response=await fetch("/api/config");if(!response.ok)throw Error();const flags=await response.json();if(!flags.provider_links){alert("Provider viewing is disabled by the administrator.");return;}}catch{alert("Unable to check provider availability. Please retry.");return;}
  const u=new URL(platformHTTPS(url));if(u.protocol!=='https:')return;
  returnFocus=document.activeElement;
  let viewer=document.querySelector('#provider-viewer');if(!viewer){viewer=document.createElement('dialog');viewer.id='provider-viewer';document.body.append(viewer);}
  viewer.replaceChildren();
  const toolbar=document.createElement('div');toolbar.className='actions';
  const close=document.createElement('button');close.textContent='← Back to Africa Media Hub';close.onclick=()=>viewer.close();
  const title=document.createElement('strong');title.textContent=label||u.hostname;toolbar.append(close,title);
  const outside=document.createElement('a');outside.href=u.href;outside.target='_blank';outside.rel='noopener noreferrer';outside.dataset.openExternal='true';outside.className='provider-link';outside.textContent='Open externally ↗';
  outside.addEventListener('click',event=>{
   if(window.MediaNative?.openExternal){event.preventDefault();window.MediaNative.openExternal(u.href);}
   else if(window.webkit?.messageHandlers?.mediaExternal){event.preventDefault();window.webkit.messageHandlers.mediaExternal.postMessage(u.href);}
  });toolbar.append(outside);
  const nativeOpen=window.MediaNative?.openProvider?()=>window.MediaNative.openProvider(u.href):window.webkit?.messageHandlers?.mediaProvider?()=>window.webkit.messageHandlers.mediaProvider.postMessage(u.href):null;
  if(nativeOpen){const inside=document.createElement('button');inside.textContent='View inside app';inside.onclick=nativeOpen;toolbar.append(inside);}

  const message=document.createElement('p');message.className='muted';message.textContent='Provider viewing panel. Some services block embedding, require sign-in, or restrict playback. If the page is blank, refuses to load, or requires its own app, choose Open externally.';
  const frame=document.createElement('iframe');frame.title=label||'Provider viewer';frame.referrerPolicy='strict-origin-when-cross-origin';frame.allow='autoplay; encrypted-media; fullscreen; picture-in-picture';frame.setAttribute('sandbox','allow-scripts allow-same-origin allow-forms allow-presentation');
  if(u.hostname==='www.youtube.com'||u.hostname==='youtube.com'){const id=u.searchParams.get('v');if(id&&/^[a-zA-Z0-9_-]{11}$/.test(id))frame.src='https://www.youtube.com/embed/'+id;else{frame.src=u.href;message.textContent='YouTube channel pages may block embedding. A specific video URL can use the YouTube embedded player; live-channel pages are not direct video URLs.';}}
  else frame.src=u.href;
  viewer.append(toolbar,message);if(!nativeOpen)viewer.append(frame);viewer.onclose=()=>{frame.src='about:blank';if(returnFocus?.isConnected)returnFocus.focus();};viewer.showModal();close.focus();
 }
 document.addEventListener('click',e=>{const link=e.target.closest('a[href]');if(!link||link.dataset.openExternal==='true')return;let url;try{url=new URL(link.href,location.href);}catch{return;}if(['http:','https:'].includes(url.protocol)&&url.origin!==location.origin){e.preventDefault();e.stopImmediatePropagation();openProvider(url.href,link.closest('article')?.querySelector('h3')?.textContent||link.textContent.replace('↗','').trim());}},true);
 document.addEventListener('keydown',e=>{const viewer=document.querySelector('#provider-viewer[open]');if(viewer&&['Escape','BrowserBack','Backspace'].includes(e.key)){e.preventDefault();e.stopImmediatePropagation();viewer.close();}},true);
})();
