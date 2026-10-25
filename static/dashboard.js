'use strict';
function openDashboardTarget(selector){
 const target=document.querySelector(selector);if(!target){note('This section is unavailable. Refresh the dashboard and try again.');return false;}
 for(let element=target;element;element=element.parentElement)if(element.tagName==='DETAILS')element.open=true;
 target.scrollIntoView({block:'start',behavior:'auto'});
 const focus=target.matches('button,input,select,textarea,a,summary,[tabindex]')?target:target.querySelector('input,button,select,textarea,a,summary');
 if(focus)focus.focus({preventScroll:true});return true;
}
(()=>{
 document.addEventListener('click',event=>{const button=event.target.closest('[data-dashboard-target]');if(button){event.preventDefault();openDashboardTarget(button.dataset.dashboardTarget);}});
 const beforeAdmin=adminView;
 adminView=async function(){await beforeAdmin();const area=document.createElement('section');area.className='dashboard-overview';area.setAttribute('aria-label','Administration dashboard');
 const destinations=[['Advertising','#admin-advertising'],['Activity & downloads','#admin-activity'],['Support inbox','#admin-support'],['Users','#people-list'],['Create user','#people-create'],['Groups','.people-group'],['Content','#admin-content'],['Channels','#console-channel-filter'],['Schedules','#program'],['Reports','#admin-reports'],['Marketplace','.market-product'],['Payment gateways','.market-gateway'],['Orders','#admin-orders'],['Feature switches','#console-features'],['Legal inbox','#admin-legal'],['Audit log','#admin-audit']];
 area.innerHTML='<h1>Administration dashboard</h1><p>Select a card to open its management controls.</p><div class="grid dashboard-links">'+destinations.map(([label,selector])=>'<button class="stat" data-dashboard-target="'+selector+'">'+esc(label)+' →</button>').join('')+'</div>';document.querySelector('#view').prepend(area);
 };
 const beforeHome=tvHome;
 function homeShortcuts(){if(page!=='Home'||document.querySelector('#home-dashboard-shortcuts'))return;const area=document.createElement('section');area.id='home-dashboard-shortcuts';area.setAttribute('aria-label','Dashboard shortcuts');area.innerHTML='<h2>Your dashboard</h2><div class="grid dashboard-links">'+['Live TV','Sports','Movies','Local Channels','My Stuff','Marketplace','History','Creator Studio','Settings',...(me.user?.role==='admin'?['Admin']:[])].map(label=>'<button class="stat" data-dashboard-page="'+esc(label)+'">'+esc(label)+' →</button>').join('')+'</div>';const landing=document.querySelector('.tv-landing');if(landing)landing.querySelector('.tv-feature').after(area);else document.querySelector('#view').prepend(area);area.querySelectorAll('[data-dashboard-page]').forEach(button=>button.onclick=run(()=>navigate(button.dataset.dashboardPage)));
 }
 tvHome=async function(){await beforeHome();homeShortcuts();};
 document.addEventListener('media-ready',homeShortcuts);if(window.mediaReady)homeShortcuts();
})();
