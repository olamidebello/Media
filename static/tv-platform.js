(function(root){
'use strict';
const platforms={
 android:{label:'Android / Google TV',package:'android',help:'Install the Android TV APK using the desktop installer after enabling wireless debugging and approving your TV. Also supports Android-based Sony, TCL, Hisense, Philips, Xiaomi and other brands.'},
 fire:{label:'Amazon Fire TV',package:'android',help:'Use the Android / Fire TV APK. Enable ADB debugging and approve the desktop connection on your Fire TV.'},
 samsung:{label:'Samsung Tizen',package:'samsung',help:'Install the signed WGT with Samsung TV developer tools and the certificate approved for your TV. An Android APK will not work.'},
 lg:{label:'LG webOS',package:'lg',help:'Enable LG Developer Mode, pair your computer using webOS CLI, then install the IPK with ares-install. An Android APK will not work.'},
 roku:{label:'Roku TV / player',package:'roku',help:'Enable Roku Developer Mode and upload the development ZIP through the Roku Development Application Installer. This replaces the currently sideloaded development channel.'},
 apple:{label:'Apple TV (tvOS)',package:null,help:'Requires an Apple-signed tvOS build distributed through TestFlight, the App Store or registered-device provisioning. No public store listing is configured yet.'},
 vidaa:{label:'Hisense VIDAA',package:null,help:'VIDAA requires its partner distribution process. Use the TV browser if available; no native VIDAA package is available.'},
 titan:{label:'Titan OS',package:null,help:'Titan OS requires platform approval and distribution. Use the TV browser if available; no native Titan OS package is available.'},
 browser:{label:'Other / unknown TV',package:null,help:'Open this site in the TV browser and use TV mode. Select the operating system from your TV settings; a brand name alone cannot determine the correct app.'}
};
function detect(value){const s=String(value||'');if(/Roku/i.test(s))return 'roku';if(/AppleTV|Apple TV|tvOS/i.test(s))return 'apple';if(/Tizen|Samsung Smart TV/i.test(s))return 'samsung';if(/web[o0]s|LG Smart TV/i.test(s))return 'lg';if(/VIDAA/i.test(s))return 'vidaa';if(/Titan[ _-]?OS/i.test(s))return 'titan';if(/AFT[A-Z0-9]*|Fire[ _-]?TV/i.test(s))return 'fire';if(/Android|Google[ _-]?TV|BRAVIA|SHIELD/i.test(s))return 'android';return 'browser';}
const api={platforms,detect};if(typeof module==='object')module.exports=api;else root.MediaTVPlatforms=api;
})(typeof globalThis!=='undefined'?globalThis:this);
