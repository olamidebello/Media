'use strict';
const {contextBridge,ipcRenderer}=require('electron');
contextBridge.exposeInMainWorld('MediaTVInstaller',Object.freeze({scan:()=>ipcRenderer.invoke('tv:scan'),discover:()=>ipcRenderer.invoke('tv:discover'),install:id=>ipcRenderer.invoke('tv:install',id)}));

contextBridge.exposeInMainWorld('MediaCameras',Object.freeze({discover:()=>ipcRenderer.invoke('camera:discover')}));
