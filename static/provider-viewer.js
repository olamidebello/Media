'use strict';
(()=>{
 let returnFocus;
 function openProvider(url,label){
  const u=new URL(url);if(u.protocol!=='https:')return;
  if(window.MediaNative?.openProvider){window.MediaNative.openProvider(u.href);return;}
  if(window.webkit?.messageHandlers?.mediaProvider){window.webkit.messageHandlers.mediaProvider.postMessage(u.href);return;}
  if(/Electron\//.test(navigator.userAgent)){window.open(u.href,'_blank');return;}
  returnFocus=document.activeElement;
  let viewer=document.querySelector('#provider-viewer');if(!viewer){viewer=document.createElement('dialog');viewer.id='provider-viewer';document.body.append(viewer);}
  viewer.replaceChildren();
  const toolbar=document.createElement('div');toolbar.className='actions';
  const close=document.createElement('button');close.textContent='← Back to Africa Media Hub';close.onclick=()=>viewer.close();
  const title=document.createElement('strong');title.textContent=label||u.hostname;toolbar.append(close,title);
  const message=document.createElement('p');message.className='muted';message.textContent='Provider viewing panel. Some services block embedding, require sign-in, or restrict playback. A blank or refused page means this provider cannot load in an embedded browser.';
  const frame=document.createElement('iframe');frame.title=label||'Provider viewer';frame.referrerPolicy='strict-origin-when-cross-origin';frame.allow='autoplay; encrypted-media; fullscreen; picture-in-picture';frame.setAttribute('sandbox','allow-scripts allow-same-origin allow-forms allow-presentation');
  if(u.hostname==='www.youtube.com'||u.hostname==='youtube.com'){const id=u.searchParams.get('v');if(id&&/^[a-zA-Z0-9_-]{11}$/.test(id))frame.src='https://www.youtube.com/embed/'+id;else{frame.src=u.href;message.textContent='YouTube channel pages may block embedding. A specific video URL can use the YouTube embedded player; live-channel pages are not direct video URLs.';}}
  else frame.src=u.href;
  viewer.append(toolbar,message,frame);viewer.onclose=()=>{frame.src='about:blank';if(returnFocus?.isConnected)returnFocus.focus();};viewer.showModal();close.focus();
 }
 document.addEventListener('click',e=>{const link=e.target.closest('a[href]');if(!link)return;let url;try{url=new URL(link.href,location.href);}catch{return;}if(url.protocol==='https:'&&url.origin!==location.origin){e.preventDefault();e.stopImmediatePropagation();openProvider(url.href,link.closest('article')?.querySelector('h3')?.textContent||link.textContent.replace('↗','').trim());}},true);
 document.addEventListener('keydown',e=>{const viewer=document.querySelector('#provider-viewer[open]');if(viewer&&['Escape','BrowserBack','Backspace'].includes(e.key)){e.preventDefault();e.stopImmediatePropagation();viewer.close();}},true);
})();
