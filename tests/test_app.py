import os, tempfile, unittest, io, json, sys
sys.path.insert(0,os.path.dirname(os.path.dirname(__file__)))
os.environ['MEDIA_DB']=tempfile.mktemp(suffix='.db')
os.environ['MEDIA_SECURE_COOKIE']='0'
import app

class PlatformTests(unittest.TestCase):
    def setUp(self):
        with app.db() as c:
            for t in ['reports','audit','sessions','videos','channels','users']: c.execute('DELETE FROM '+t)
        self.cookie=''; self.csrf=''
    def req(self,path,body=None):
        raw=json.dumps(body or {}).encode(); status=[]; headers=[]
        env={'REQUEST_METHOD':'POST' if body is not None else 'GET','PATH_INFO':path.split('?')[0],'QUERY_STRING':path.partition('?')[2],'CONTENT_LENGTH':str(len(raw)),'wsgi.input':io.BytesIO(raw),'HTTP_COOKIE':self.cookie,'HTTP_X_CSRF_TOKEN':self.csrf,'HTTP_HOST':'localhost'}
        out=b''.join(app.app(env,lambda s,h:(status.append(s),headers.extend(h))))
        for k,v in headers:
            if k=='Set-Cookie': self.cookie=v.split(';')[0]
        return int(status[0].split()[0]),json.loads(out)
    def register(self,email='viewer@example.com'):
        self.assertEqual(self.req('/api/register',{'email':email,'password':'strong-password-123','policy_version':'2026-10-25','adult_account':True})[0],200)
        _,m=self.req('/api/me'); self.csrf=m['csrf']; return m['profiles'][0]['id']
    def test_auth_csrf_and_admin_authorization(self):
        p=self.register(); self.assertEqual(self.req('/api/admin')[0],403)
        self.csrf='wrong'; self.assertEqual(self.req('/api/profiles',{'name':'Other'})[0],403)
    def test_moderation_and_profile_isolation(self):
        p=self.register(); self.assertEqual(self.req('/api/studio',{'title':'Film','url':'https://example.com/a.mp4'})[0],200)
        self.assertEqual(self.req('/api/catalog')[1],[])
        with app.db() as c: c.execute("UPDATE videos SET visibility='public'")
        vid=self.req('/api/catalog')[1][0]['id']
        self.assertEqual(self.req('/api/action',{'profile_id':p,'video_id':vid,'action':'save'})[0],200)
        self.assertEqual(len(self.req('/api/library?profile_id='+str(p))[1]['saved']),1)
        self.req('/api/logout',{}); self.cookie=''; self.csrf=''; self.register('other@example.com')
        self.assertEqual(self.req('/api/library?profile_id='+str(p))[0],403)
    def test_kids_and_comments(self):
        p=self.register()
        self.req('/api/studio',{'title':'Adults','url':'https://example.com/a.mp4'})
        with app.db() as c: c.execute("UPDATE videos SET visibility='public'")
        self.req('/api/profiles',{'name':'Child','kids':True})
        kid=self.req('/api/me')[1]['profiles'][-1]['id']
        self.assertEqual(self.req('/api/catalog?profile_id='+str(kid))[1],[])
        self.assertEqual(self.req('/api/action',{'profile_id':kid,'video_id':1,'action':'save'})[0],403)
    def test_admin_publish_and_live_schedule(self):
        p=self.register()
        with app.db() as c:c.execute("UPDATE users SET role='admin'")
        self.assertEqual(self.req('/api/admin',{'action':'channel','name':'News','url':'file:///unsafe'})[0],400)
        self.assertEqual(self.req('/api/admin',{'action':'channel','name':'News','url':'http://example.com:80/live.m3u8'})[0],200)
        channel=self.req('/api/guide')[1]['channels'][0]
        self.assertEqual(channel['url'],'https://example.com/live.m3u8')
        cid=channel['id']
        self.assertEqual(self.req('/api/admin',{'action':'program','channel_id':cid,'title':'News hour','start':2000000000,'end':2000003600})[0],200)
        self.assertEqual(self.req('/api/record',{'profile_id':p,'program_id':1})[0],400)

app.init()
if __name__=='__main__':unittest.main()
