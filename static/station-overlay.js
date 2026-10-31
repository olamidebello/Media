'use strict';
(async function update(){
 try{const id=new URLSearchParams(location.search).get('id')||'',r=await fetch('/api/stations/overlay?id='+encodeURIComponent(id),{cache:'no-store'});if(!r.ok)throw Error();const s=await r.json();document.querySelector('#station-graphics').hidden=!s.overlay_enabled;document.querySelector('#overlay-name').textContent=s.name;const img=document.querySelector('#overlay-logo');img.hidden=!s.logo;if(s.logo&&img.getAttribute('src')!==s.logo)img.src=s.logo;img.onerror=()=>{img.hidden=true;};const lower=document.querySelector('#overlay-lower');lower.textContent=s.lower_third;lower.hidden=!s.lower_third;const ticker=document.querySelector('#overlay-ticker');ticker.hidden=!s.ticker;const span=ticker.querySelector('span');if(span.textContent!==s.ticker)span.textContent=s.ticker;
 }catch{document.querySelector('#station-graphics').hidden=true;}setTimeout(update,5000);
})();
