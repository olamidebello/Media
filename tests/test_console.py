import unittest
from test_app import PlatformTests,app
class ConsoleTests(unittest.TestCase):
 req=PlatformTests.req
 register=PlatformTests.register
 def setUp(self):
  PlatformTests.setUp(self)
  with app.db() as c:c.execute('DELETE FROM settings')
 def tearDown(self):
  with app.db() as c:c.execute('DELETE FROM settings')
 def become_admin(self):
  self.register()
  with app.db() as c:c.execute("UPDATE users SET role='admin'")
 def test_permissions_and_switch_enforcement(self):
  self.register()
  self.assertEqual(self.req('/api/admin/console',{'action':'features','live_tv':'off'})[0],403)
  with app.db() as c:c.execute("UPDATE users SET role='admin'")
  self.assertEqual(self.req('/api/admin/console',{'action':'features','live_tv':'off'})[0],200)
  self.assertEqual(self.req('/api/guide')[0],403)
  self.assertFalse(self.req('/api/config')[1]['live_tv'])
 def test_bulk_import_duplicates_and_self_deletion(self):
  self.become_admin();b={'action':'bulk_channels','playlist':'#EXTM3U\n#EXTINF:-1 group-title="News",Example\nhttps://example.com/live.m3u8\n'}
  self.assertEqual(self.req('/api/admin/console',b)[1]['added'],1)
  self.assertEqual(self.req('/api/admin/console',b)[1]['added'],0)
  uid=self.req('/api/me')[1]['user']['id']
  self.assertEqual(self.req('/api/admin/console',{'action':'delete_user','id':uid})[0],400)
 def test_admin_creates_public_content(self):
  self.become_admin()
  b={'action':'create_content','title':'Authorized film','url':'https://example.com/movie.mp4','visibility':'public','kind':'movie','kids':False}
  self.assertEqual(self.req('/api/admin/console',b)[0],200)
  self.assertEqual(self.req('/api/catalog')[1][0]['title'],'Authorized film')
