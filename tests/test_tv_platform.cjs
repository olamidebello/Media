const test=require('node:test'),assert=require('node:assert/strict');
const {detect,platforms}=require('../static/tv-platform.js');
const {classify}=require('../apps/desktop/tv-discovery.cjs');
test('operating system wins over TV brand',()=>{for(const [text,id] of [['TCL Roku TV','roku'],['TCL Android TV','android'],['Hisense VIDAA','vidaa'],['Hisense Google TV','android'],['Samsung Tizen 7','samsung'],['LG webOS','lg'],['AFTMM','fire'],['AppleTV tvOS','apple'],['Philips Titan OS','titan'],['Hisense','browser'],['TCL','browser']])assert.equal(detect(text),id);});
test('only compatible platforms share APKs',()=>{assert.equal(platforms.fire.package,'android');assert.equal(platforms.android.package,'android');assert.equal(platforms.lg.package,'lg');assert.equal(platforms.samsung.package,'samsung');assert.equal(platforms.roku.package,'roku');for(const id of ['apple','vidaa','titan','browser'])assert.equal(platforms[id].package,null);});
test('unknown network devices remain unclassified',()=>{assert.equal(classify('Hisense MediaRenderer'),'browser');assert.equal(classify('Roku MediaRenderer'),'roku');assert.equal(classify('LG Electronics webOS MediaRenderer'),'lg');});
