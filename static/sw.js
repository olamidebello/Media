'use strict';
const CACHE='africa-media-shell-v2';
self.addEventListener('install',event=>{event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(['/offline.html','/offline.css','/reconnect.js','/assets/app-icon.svg'])));self.skipWaiting();});
self.addEventListener('activate',event=>{event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k.startsWith('africa-media-shell-')&&k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim()));});
self.addEventListener('fetch',event=>{if(new URL(event.request.url).origin===self.location.origin&&new URL(event.request.url).pathname.match(/^\/(reconnect\.js|offline\.css)$/)){event.respondWith(fetch(event.request).catch(()=>caches.match('/reconnect.js')));return;}if(event.request.mode==='navigate')event.respondWith(fetch(event.request).catch(()=>caches.match('/offline.html')));});
