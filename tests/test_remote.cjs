const {test}=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
function remote(){
 const handlers={},timers=new Map(),watched=[];let seq=0;
 const element=()=>({classList:{add(){},remove(){},toggle(){}},setAttribute(){},append(){},addEventListener(){},focus(){},querySelectorAll(){return []}});
 const hint=element(),toggle=element(),modal=element();
 const document={body:element(),activeElement:{tagName:'BUTTON',click(){throw Error('OK must tune rather than click focused button');}},createElement:()=>++seq===1?hint:toggle,addEventListener:(name,fn)=>handlers[name]=fn,querySelector:s=>s==='header'?element():s==='#modal'?modal:null,querySelectorAll:()=>[]};
 const ctx={document,localStorage:{getItem:()=> 'on',setItem(){}},location:{search:''},URLSearchParams,getComputedStyle:()=>({visibility:'visible'}),setTimeout:fn=>{const id=timers.size+1;timers.set(id,fn);return id;},clearTimeout:id=>timers.delete(id),api:async()=>({channels:[{id:7,number:7,name:'Seven'},{id:42,number:42,name:'Forty Two'}]}),watch:(c)=>watched.push(c),page:'Home'};
 vm.createContext(ctx);vm.runInContext(fs.readFileSync('static/smart-tv.js','utf8'),ctx);
 return {ctx,watched,hint,timers,key:async(key,keyCode=0)=>{let prevented=false;handlers.keydown({key,keyCode,preventDefault(){prevented=true;}});await new Promise(setImmediate);return prevented;}};
}
test('multi-digit OK uses stable channel number from Home',async()=>{const r=remote();await r.key('4');await r.key('2');await r.key('Enter');assert.equal(r.watched[0].id,42);assert.match(r.hint.textContent,/Channel 42/);});
test('legacy numeric keys, backspace and timer tune',async()=>{const r=remote();await r.key('Unidentified',55);await r.key('2');await r.key('Backspace');for(const fn of [...r.timers.values()])fn();await new Promise(setImmediate);assert.equal(r.watched[0].id,7);});
test('missing channel leaves current playback alone',async()=>{const r=remote();await r.key('9');await r.key('Enter');assert.equal(r.watched.length,0);assert.match(r.hint.textContent,/unavailable/);});
test('cancel and editable fields do not tune',async()=>{const r=remote();await r.key('7');await r.key('Escape');for(const fn of [...r.timers.values()])fn();await new Promise(setImmediate);assert.equal(r.watched.length,0);r.ctx.document.activeElement={tagName:'INPUT'};assert.equal(await r.key('7'),false);});
