'use strict';
(()=>{
 const keys=['Home','Live TV','Movies','Search','Account','Sign in','Settings','Help','More ▾','Watch live','Watch now','Kids & Family'];
 const packs={
 en:keys,
 pcm:['Home','Live TV','Films','Find','My account','Sign in','Settings','Help','More ▾','Watch live','Watch now','Pikin & Family'],
 sw:['Mwanzo','TV Mubashara','Filamu','Tafuta','Akaunti','Ingia','Mipangilio','Msaada','Zaidi ▾','Tazama mubashara','Tazama sasa','Watoto na Familia'],
 ha:['Gida','Talabijin kai tsaye','Fina-finai','Bincika','Asusu','Shiga','Saituna','Taimako','Ƙari ▾','Kalli kai tsaye','Kalla yanzu','Yara da Iyali'],
 yo:['Ilé','TV tààrà','Àwọn fíìmù','Ṣàwárí','Àkọọ́lẹ̀','Wọlé','Ètò','Ìrànlọ́wọ́','Síwájú ▾','Wò tààrà','Wò báyìí','Ọmọdé àti Ìdílé'],
 ig:['Ụlọ','TV na-aga ugbu a','Ihe nkiri','Chọọ','Akaụntụ','Banye','Ntọala','Enyemaka','Ọzọ ▾','Lelee ugbu a','Lelee ugbu a','Ụmụaka na Ezinụlọ'],
 zu:['Ikhaya','I-TV ebukhoma','Amafilimu','Sesha','I-akhawunti','Ngena','Izilungiselelo','Usizo','Okunye ▾','Buka bukhoma','Buka manje','Izingane Nomndeni'],
 xh:['Ekhaya','I-TV ephilayo','Iimuvi','Khangela','Iakhawunti','Ngena','Iisetingi','Uncedo','Okunye ▾','Bukela ngqo','Bukela ngoku','Abantwana Nosapho'],
 so:['Bogga hore','TV toos ah','Filimaan','Raadi','Akoon','Soo gal','Dejinta','Caawimaad','Dheeraad ▾','Daawo toos','Daawo hadda','Carruurta iyo Qoyska'],
 rw:['Ahabanza','TV imbonankubone','Filime','Shakisha','Konti','Injira','Igenamiterere','Ubufasha','Ibindi ▾','Reba imbonankubone','Reba ubu','Abana n’Umuryango'],
 am:['መነሻ','ቀጥታ ቴሌቪዥን','ፊልሞች','ፈልግ','መለያ','ግባ','ቅንብሮች','እገዛ','ተጨማሪ ▾','በቀጥታ ይመልከቱ','አሁን ይመልከቱ','ልጆች እና ቤተሰብ'],
 ar:['الرئيسية','بث مباشر','أفلام','بحث','الحساب','تسجيل الدخول','الإعدادات','المساعدة','المزيد ▾','شاهد مباشرة','شاهد الآن','الأطفال والعائلة'],
 fr:['Accueil','TV en direct','Films','Rechercher','Compte','Connexion','Paramètres','Aide','Plus ▾','Regarder en direct','Regarder maintenant','Enfants et famille'],
 pt:['Início','TV ao vivo','Filmes','Pesquisar','Conta','Entrar','Configurações','Ajuda','Mais ▾','Assistir ao vivo','Assistir agora','Crianças e família'],
 es:['Inicio','TV en directo','Películas','Buscar','Cuenta','Iniciar sesión','Ajustes','Ayuda','Más ▾','Ver en directo','Ver ahora','Niños y familia']};
 const codes='en pcm sw ha yo ig zu xh so rw am ar fr pt es aa af ak an ang arq ary arz asa ast bem bez bm brx bss byn cgg chr ckb co dav dje doi dua dyo dz ebu ee efi ewo ff fon fur ga gaa gez gu guz he hr hy ia id ii jgo jmc kab kam kde kea kg khq ki kln km kn ko kok ksb ksf ksh ku lag lg ln lo lrc lt lu luo luy mas mer mfe mg mgh mgo mi mk ml mn mr ms mt mua my mzn naq nd nds ne nmg nn nnh nr nso nus ny nyn om os pa pl ps qu rm rn ro rof ru rwk sa sah saq sat sbp sd se seh ses sg shi si sk sl sma smj smn sms sn ss ssy st su syr ta te teo tg th ti tk tn to tr ts tt tum twq tzm ug uk ur uz vai ve vi vo vun wae wal wo xog yav yi zgh'.split(' ');
 let language;try{language=localStorage.getItem('mediaLanguage')||'en';}catch{language='en';}
 const original=new WeakMap(),rendered=new WeakMap();let observer;
 function apply(){observer?.disconnect();document.documentElement.lang=language;document.documentElement.dir=/^(ar|he|fa|ur|ps|sd|ku)(-|$)/.test(language)?'rtl':'ltr';
 const pack=packs[language]||packs[language.split('-')[0]]||keys;
 document.querySelectorAll('#nav button,#nav summary,header button,.mobile-bottom button,.tv-tabs button,#view>h1,.tv-row-title button').forEach(el=>{
  for(const n of el.childNodes){if(n.nodeType!==3)continue;const text=n.textContent.trim();let source=original.get(n);if(!source||rendered.get(n)!==text)source=text;if(!keys.includes(source))continue;original.set(n,source);const i=keys.indexOf(source);n.textContent=pack[i];rendered.set(n,pack[i]);}
 });observer?.observe(document.body,{childList:true,subtree:true});}
 const area=document.createElement('div');area.className='language-control';
 const names=new Intl.DisplayNames(['en'],{type:'language'});const native=code=>{try{return new Intl.DisplayNames([code],{type:'language'}).of(code);}catch{return names.of(code);}};
 area.innerHTML='<label for="media-language">Language</label><select id="media-language" aria-label="Interface language"></select><button id="custom-language" type="button">Other language</button><small id="language-status" role="status"></small>';
 const select=area.querySelector('select');[...new Set(codes)].sort((a,b)=>names.of(a).localeCompare(names.of(b))).forEach(code=>{const o=document.createElement('option');o.value=code;o.textContent=native(code)+' · '+names.of(code)+(packs[code]?'':' (English interface)');select.append(o);});
 function save(code){language=code;try{localStorage.setItem('mediaLanguage',code);}catch{}if(![...select.options].some(o=>o.value===code)){const o=document.createElement('option');o.value=code;o.textContent=names.of(code)+' (English interface)';select.append(o);}select.value=code;area.querySelector('small').textContent=packs[code]?'Core navigation translated; other text uses English.':'Language preference saved. Interface translations currently use English.';apply();}
 select.onchange=()=>save(select.value);area.querySelector('button').onclick=()=>{const input=prompt('Enter your language tag, for example: sw-KE, ff-Adlm, or yo-NG');if(!input)return;try{save(Intl.getCanonicalLocales(input.trim())[0]);}catch{note('Enter a valid language tag.');}};
 document.querySelector('header').append(area);observer=new MutationObserver(apply);save(language);
})();
