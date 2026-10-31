import hashlib
import io
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,os.path.dirname(os.path.dirname(__file__)))
import app, stations

class StationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.dbpatch=patch.object(app,'DB',str(Path(self.tmp.name)/'test.db')); self.dbpatch.start()
        app.init(); self.cookie='';self.csrf=''
        with app.db() as c:
            c.execute("INSERT INTO users(id,email,password) VALUES(1,'owner@example.com','unused'),(2,'other@example.com','unused')")
            c.execute("INSERT INTO profiles(id,user_id,name,kids) VALUES(1,1,'Owner',0),(2,2,'Other',0),(3,1,'Child',1)")
            c.execute('INSERT INTO sessions VALUES(?,?,?,?)',(hashlib.sha256(b'owner').hexdigest(),1,'csrf',int(time.time())+3600))
            c.execute('INSERT INTO sessions VALUES(?,?,?,?)',(hashlib.sha256(b'other').hexdigest(),2,'othercsrf',int(time.time())+3600))
        self.cookie='media_session=owner';self.csrf='csrf'
        self.enginepatch=patch.object(stations,'engine',return_value={'publish_url':'rtmps://example.com:1936/live'});self.enginepatch.start()
    def tearDown(self):
        self.enginepatch.stop();self.dbpatch.stop();self.tmp.cleanup()
    def req(self,path,body=None,remote='127.0.0.1',form=None):
        raw=(form.encode() if form is not None else json.dumps(body or {}).encode()); status=[]
        env={'REQUEST_METHOD':'POST' if body is not None or form is not None else 'GET','PATH_INFO':path.split('?')[0],'QUERY_STRING':path.partition('?')[2],'CONTENT_LENGTH':str(len(raw)),'wsgi.input':io.BytesIO(raw),'HTTP_COOKIE':self.cookie,'HTTP_X_CSRF_TOKEN':self.csrf,'HTTP_HOST':'localhost','REMOTE_ADDR':remote}
        out=b''.join(app.app(env,lambda s,h:status.append(s)))
        return int(status[0].split()[0]),json.loads(out)
    def create(self):
        code,data=self.req('/api/stations',{'profile_id':1,'action':'create','name':'Community TV'});self.assertEqual(code,200)
        return data['id']
    def post(self,id,action,**data):return self.req('/api/stations',{'profile_id':1,'id':id,'action':action,**data})
    def test_ownership_csrf_and_kids(self):
        sid=self.create()
        self.assertEqual(self.req('/api/stations?profile_id=3')[0],403)
        self.csrf='bad';self.assertEqual(self.post(sid,'delete')[0],403)
        self.cookie='media_session=other';self.csrf='othercsrf'
        self.assertEqual(self.req('/api/stations',{'profile_id':2,'id':sid,'action':'delete'})[0],404)
        self.cookie='';self.assertEqual(self.req('/api/stations?profile_id=1')[0],403)
    def test_encoder_key_lifecycle_and_suspension(self):
        sid=self.create();self.assertEqual(self.post(sid,'start')[0],400)
        _,r=self.post(sid,'rotate_key');key=r['stream_key'].split('key=')[1]
        with app.db() as c:
            row=c.execute('SELECT * FROM stations WHERE id=?',(sid,)).fetchone()
            self.assertNotEqual(key,row['key_hash']);self.assertEqual(hashlib.sha256(key.encode()).hexdigest(),row['key_hash'])
        self.assertEqual(self.post(sid,'start')[0],200)
        form='name=station-'+str(sid)+'&key='+key
        self.assertEqual(self.req('/station-engine/authorize',form=form)[0],200)
        self.assertEqual(self.req('/station-engine/authorize',form=form,remote='198.51.100.1')[0],403)
        self.post(sid,'rotate_key');self.post(sid,'start')
        self.assertEqual(self.req('/station-engine/authorize',form=form)[0],403)
        self.post(sid,'stop');self.assertEqual(self.req('/station-hls/station-'+str(sid)+'/index.m3u8')[0],403)
        with app.db() as c:c.execute('UPDATE stations SET suspended=1')
        self.assertEqual(self.post(sid,'start')[0],403)
    def test_schedule_overlap_isolation_public_redaction_and_review(self):
        sid=self.create()
        values=dict(title='Evening news',description='Community bulletin',start=2000000000,end=2000001800,kind='live',notes='private phone number',media_url='https://example.com/clip.mp4')
        self.assertEqual(self.post(sid,'program',**values)[0],200)
        self.assertEqual(self.post(sid,'program',**values)[0],400)
        self.assertEqual(self.post(sid,'save',name='Community TV',category='News',source='external',external_url='https://example.com/live.m3u8')[0],200)
        self.assertEqual(self.post(sid,'start')[0],200)
        s=self.req('/api/stations?profile_id=1')[1]['stations'][0];public_id=s['public_id']
        self.cookie='';self.csrf=''
        self.assertEqual(self.req('/api/stations/public?id='+public_id)[0],404)
        with app.db() as c:c.execute('UPDATE stations SET approved=1')
        code,data=self.req('/api/stations/public?id='+public_id);self.assertEqual(code,200)
        self.assertEqual(len(self.req('/api/stations/directory')[1]),1)
        self.assertEqual(self.req('/api/stations/directory?profile_id=3')[0],403)
        self.assertNotIn('notes',data['programs'][0]);self.assertNotIn('media_url',data['programs'][0]);self.assertNotIn('key_hash',data)
        self.cookie='media_session=owner';self.csrf='csrf'
        self.post(sid,'save',name='New identity',category='News',source='external',external_url='https://example.com/live.m3u8')
        with app.db() as c:
            s=c.execute('SELECT * FROM stations').fetchone();self.assertFalse(s['approved']);self.assertFalse(s['broadcasting'])
    def test_hls_authorization_streaming_and_signal(self):
        sid=self.create();self.post(sid,'rotate_key');self.post(sid,'start')
        root=Path(self.tmp.name)/'hls';folder=root/('station-'+str(sid));folder.mkdir(parents=True);(folder/'index.m3u8').write_text('#EXTM3U\n')
        with patch.object(stations,'HLS',root):
            state=self.req('/api/stations?profile_id=1')[1]['stations'][0];self.assertEqual(state['signal'],'live')
            with app.db() as c:
                stations.access(c,'/station-hls/station-'+str(sid)+'/index.m3u8',1)
                with self.assertRaises(PermissionError):stations.access(c,'/station-hls/station-'+str(sid)+'/index.m3u8',2)
                with self.assertRaises(PermissionError):stations.access(c,'/station-hls/station-'+str(sid)+'/../../etc/passwd',1)
                c.execute('UPDATE stations SET approved=1')
                stations.access(c,'/station-hls/station-'+str(sid)+'/123.ts',None)
            status=[]
            out=b''.join(app.app({'PATH_INFO':'/station-hls/station-'+str(sid)+'/index.m3u8','REQUEST_METHOD':'GET'},lambda s,h:status.append(s)))
            self.assertTrue(status[0].startswith('200'));self.assertEqual(out,b'#EXTM3U\n')
    def test_url_validation_and_admin_only_moderation(self):
        sid=self.create()
        self.assertEqual(self.post(sid,'save',name='TV',category='News',source='external',external_url='https://user:password@example.com/live.m3u8')[0],400)
        self.assertEqual(self.req('/api/admin/stations',{'action':'approve','id':sid})[0],403)
        with app.db() as c:c.execute("UPDATE users SET role='admin' WHERE id=1")
        self.assertEqual(self.req('/api/admin/stations',{'action':'approve','id':sid})[0],200)
        self.assertEqual(self.req('/api/admin/stations',{'action':'suspend','id':sid})[0],200)
        self.assertEqual(self.post(sid,'start')[0],403)

if __name__=='__main__':unittest.main()
