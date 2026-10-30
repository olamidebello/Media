import unittest
from test_app import PlatformTests,app
class RoleTests(unittest.TestCase):
 req=PlatformTests.req
 register=PlatformTests.register
 def setUp(self):PlatformTests.setUp(self)
 def test_superadmin_has_admin_access_and_regular_admin_cannot_change_superadmin(self):
  self.register('super@example.com')
  with app.db() as c:c.execute("UPDATE users SET role='superadmin' WHERE email='super@example.com'");uid=c.execute("SELECT id FROM users WHERE email='super@example.com'").fetchone()[0]
  self.assertEqual(self.req('/api/admin')[0],200)
  self.req('/api/logout',{});self.cookie='';self.csrf='';self.register('admin@example.com')
  with app.db() as c:c.execute("UPDATE users SET role='admin' WHERE email='admin@example.com'")
  self.assertEqual(self.req('/api/admin',{'action':'user','id':uid,'active':True,'role':'viewer'})[0],403)
  self.assertEqual(self.req('/api/admin/manage',{'action':'reset_password','id':uid,'password':'another-strong-password'})[0],403)
  self.assertEqual(self.req('/api/admin/people',{'action':'bulk_active','ids':[uid],'active':False})[0],403)
 def test_admin_cannot_grant_superadmin(self):
  profile=self.register()
  with app.db() as c:c.execute("UPDATE users SET role='admin'");uid=c.execute('SELECT user_id FROM profiles WHERE id=?',(profile,)).fetchone()[0]
  self.assertEqual(self.req('/api/admin',{'action':'user','id':uid,'active':True,'role':'superadmin'})[0],403)
