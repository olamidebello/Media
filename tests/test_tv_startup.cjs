const {test}=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
async function startup({last={id:42,live:true},resume=true,kids=false,channels=[{id:42,name:'News'}],search='',pathname='/',ready=false}={}){
 const events={},watched=[],notices=[],data=new Map([['mediaTV:1:2:last',JSON.stringify(last)],['mediaTV:1:2:preferences',JSON.stringify({resume})]]);
 const el={append(){},addEventListener(){}};
 const document={querySelector:s=>['header','#profiles','#account'].includes(s)?el:null,createElement:()=>({}),addEventListener:(name,fn)=>events[name]=fn};
 const ctx={document,window:{mediaReady:ready},me:{user:{id:1},profiles:[{id:2,kids}]},profile:2,localStorage:{getItem:k=>data.get(k)??null,setItem:(k,v)=>data.set(k,v)},location:{search,pathname},URLSearchParams,watch:(item,live)=>watched.push({item,live}),api:async()=>({channels}),note:text=>notices.push(text),setTimeout,clearTimeout};
 vm.createContext(ctx);vm.runInContext(fs.readFileSync('static/tv-experience.js','utf8'),ctx);if(!ready)events['media-ready']();await new Promise(setImmediate);return {watched,notices};
}
test('startup revalidates last live channel and opens it',async()=>{const r=await startup();assert.equal(r.watched[0].item.id,42);assert.equal(r.watched[0].live,true);});
test('missing or disabled last channel falls back without opening',async()=>{const r=await startup({channels:[]});assert.equal(r.watched.length,0);assert.match(r.notices[0],/unavailable/);});
test('opt-out, kids, install and deep links prevent automatic restore',async()=>{for(const options of [{resume:false},{kids:true},{pathname:'/install'},{pathname:'/build-a-station'},{pathname:'/station'},{search:'?video=1'}])assert.equal((await startup(options)).watched.length,0);});
test('startup also works when app is ready before script loads',async()=>{assert.equal((await startup({ready:true})).watched.length,1);});
