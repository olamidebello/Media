const {app,BrowserWindow,shell,session}=require('electron');
const HOME='https://media.africandroid.world/';
function external(url){try{if(new URL(url).protocol==='https:')shell.openExternal(url);}catch{}}
app.whenReady().then(()=>{session.defaultSession.setPermissionRequestHandler((web,permission,callback)=>callback(false));const w=new BrowserWindow({width:1400,height:900,backgroundColor:'#0c1018',webPreferences:{nodeIntegration:false,contextIsolation:true,sandbox:true}});w.webContents.setWindowOpenHandler(({url})=>{external(url);return {action:'deny'};});w.webContents.on('will-navigate',(e,url)=>{try{if(new URL(url).origin!==new URL(HOME).origin){e.preventDefault();external(url);}}catch{e.preventDefault();}});w.loadURL(HOME);});
app.on('window-all-closed',()=>app.quit());
