const test=require('node:test'),assert=require('node:assert/strict');
const {parseCamera}=require('../apps/desktop/camera-discovery.cjs');
test('camera discovery accepts private responders and treats names as untrusted text',()=>{assert.deepEqual(parseCamera('<ProbeMatch>onvif://www.onvif.org/name/Front%20Door</ProbeMatch>','192.168.1.4'),{name:'Front Door',address:'192.168.1.4'});assert.equal(parseCamera('<ProbeMatch/>','8.8.8.8'),null);assert.equal(parseCamera('<!DOCTYPE x><ProbeMatch/>','10.0.0.4'),null);assert.equal(parseCamera('<printer/>','10.0.0.4'),null);});
