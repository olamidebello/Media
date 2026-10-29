const {app,BrowserWindow,shell,session}=require('electron');
const path=require('node:path');
const fs=require('node:fs/promises');
const {ipcMain,dialog,net}=require('electron');
const HOME='https://media.africandroid.world/';
function external(url){try{const u=new URL(url);if(u.protocol!=='https:'||u.username||u.password)return;shell.openExternal(u.href).catch(()=>{});}catch{}}
app.whenReady().then(()=>{
const apkPath=path.join(app.getPath('temp'),'africa-media-tv.apk');
require('./tv-install.cjs').register({ipcMain,dialog,apkPath,download:async()=>{
 const response=await net.fetch(HOME+'downloads/android',{redirect:'error'});
 if(!response.ok)throw Error('Android TV package is not available on the server yet.');
 const chunks=[];let size=0;
 for await(const chunk of response.body){size+=chunk.length;if(size>150*1024*1024)throw Error('Package exceeds download limit.');chunks.push(Buffer.from(chunk));}
 const data=Buffer.concat(chunks);if(data.length<4||data[0]!==80||data[1]!==75)throw Error('Invalid APK download.');
 await fs.writeFile(apkPath,data,{mode:0o600});
}});
session.defaultSession.setPermissionRequestHandler((web,permission,callback)=>callback(false));const w=new BrowserWindow({width:1400,height:900,backgroundColor:'#0c1018',webPreferences:{preload:path.join(__dirname,'preload.cjs'),nodeIntegration:false,contextIsolation:true,sandbox:true}});w.webContents.setWindowOpenHandler(({url})=>{external(url);return {action:'deny'};});w.webContents.on('will-navigate',(e,url)=>{try{if(new URL(url).origin!==new URL(HOME).origin){e.preventDefault();external(url);}}catch{e.preventDefault();}});w.loadURL(HOME);});
app.on('window-all-closed',()=>app.quit());
