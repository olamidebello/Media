import base64,io,json,time,unittest
from test_app import PlatformTests,app
class CameraAPITests(unittest.TestCase):
    req=PlatformTests.req
    register=PlatformTests.register
    def setUp(self):PlatformTests.setUp(self)
    def create(self,profile):
        status,result=self.req('/api/my-streaming',{'action':'add','profile_id':profile,'name':'Entrance','device_hint':'192.168.1.50'})
        self.assertEqual(status,200)
        return result['id']
    def ingest(self,camera,token,jpeg=b'\xff\xd8test\xff\xd9'):
        payload=json.dumps({'camera_id':camera,'jpeg':base64.b64encode(jpeg).decode()}).encode();status=[]
        env={'REQUEST_METHOD':'POST','PATH_INFO':'/api/my-streaming/ingest','CONTENT_LENGTH':str(len(payload)),'wsgi.input':io.BytesIO(payload),'HTTP_AUTHORIZATION':'Bearer '+token}
        data=b''.join(app.app(env,lambda s,h:status.append(s)))
        return int(status[0].split()[0]),json.loads(data)
    def test_pair_ingest_view_and_revoke(self):
        profile=self.register();camera=self.create(profile)
        status,pair=self.req('/api/my-streaming',{'action':'pair','id':camera,'profile_id':profile})
        self.assertEqual(status,200);token=pair['gateway_token']
        self.assertEqual(self.ingest(camera,'x'*40)[0],403)
        self.assertEqual(self.ingest(camera,token)[0],200)
        status,frame=self.req(f'/api/my-streaming/frame?profile_id={profile}&id={camera}')
        self.assertEqual(status,200);self.assertTrue(frame['online']);self.assertTrue(frame['jpeg'])
        self.assertNotIn(token,json.dumps(self.req(f'/api/my-streaming?profile_id={profile}')[1]))
        with app.db() as c:
            self.assertNotEqual(c.execute('SELECT token_hash FROM profile_cameras WHERE id=?',(camera,)).fetchone()[0],token)
            c.execute('UPDATE profile_cameras SET last_seen=? WHERE id=?',(int(time.time())-40,camera))
        self.assertEqual(self.req(f'/api/my-streaming/frame?profile_id={profile}&id={camera}')[1]['jpeg'],'')
        self.req('/api/my-streaming',{'action':'revoke','id':camera,'profile_id':profile})
        self.assertEqual(self.ingest(camera,token)[0],403)
        with app.db() as c:self.assertIsNone(c.execute('SELECT frame FROM profile_cameras WHERE id=?',(camera,)).fetchone()[0])
    def test_other_accounts_and_children_cannot_read_or_pair(self):
        profile=self.register();camera=self.create(profile)
        self.req('/api/logout',{});self.cookie='';self.csrf='';other=self.register('other@example.com')
        for target in (profile,other):
            self.assertIn(self.req(f'/api/my-streaming/frame?profile_id={target}&id={camera}')[0],(403,404))
            self.assertIn(self.req('/api/my-streaming',{'action':'pair','id':camera,'profile_id':target})[0],(403,404))
        with app.db() as c:c.execute('UPDATE profiles SET kids=1 WHERE id=?',(other,))
        self.assertEqual(self.req(f'/api/my-streaming?profile_id={other}')[0],403)
    def test_bad_payload_and_token_rotation(self):
        profile=self.register();camera=self.create(profile)
        old=self.req('/api/my-streaming',{'action':'pair','id':camera,'profile_id':profile})[1]['gateway_token']
        new=self.req('/api/my-streaming',{'action':'pair','id':camera,'profile_id':profile})[1]['gateway_token']
        self.assertEqual(self.ingest(camera,old)[0],403)
        self.assertEqual(self.ingest(camera,new,b'not jpeg')[0],400)
        self.assertEqual(self.ingest(camera,new,b'\xff\xd8'+b'x'*60000+b'\xff\xd9')[0],400)

    def test_real_jpeg_round_trip(self):
        import shutil,subprocess
        if not shutil.which('ffmpeg'): self.skipTest('FFmpeg unavailable')
        jpeg=subprocess.check_output(['ffmpeg','-hide_banner','-loglevel','error','-f','lavfi','-i','color=c=blue:s=640x360','-frames:v','1','-threads','1','-f','image2pipe','-vcodec','mjpeg','pipe:1'])
        profile=self.register();camera=self.create(profile)
        token=self.req('/api/my-streaming',{'action':'pair','id':camera,'profile_id':profile})[1]['gateway_token']
        self.assertEqual(self.ingest(camera,token,jpeg)[0],200)
        frame=self.req(f'/api/my-streaming/frame?profile_id={profile}&id={camera}')[1]
        self.assertEqual(base64.b64decode(frame['jpeg']),jpeg)
