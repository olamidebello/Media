import sqlite3,unittest
import advertising as a
class AdvertisingTests(unittest.TestCase):
 def setUp(self):
  self.c=sqlite3.connect(':memory:');self.c.row_factory=sqlite3.Row;self.c.execute('PRAGMA foreign_keys=ON');self.c.execute('CREATE TABLE settings(key PRIMARY KEY,value)');a.init(self.c);self.audit=lambda *x:None
  a.admin(self.c,1,'POST',dict(action='save',name='Test',title='Hello',target='/',placement='home',active=True),self.audit)
 def test_disabled_kids_and_counts(self):
  self.assertIsNone(a.serve(self.c,'home',False));a.admin(self.c,1,'POST',dict(action='toggle',enabled=True),self.audit)
  self.assertIsNone(a.serve(self.c,'home',True));ad=a.serve(self.c,'home',False)
  for _ in range(2):a.event(self.c,dict(token=ad['token'],event='impression'))
  self.assertEqual(self.c.execute('SELECT impressions FROM ad_campaigns').fetchone()[0],1)
  self.assertFalse(a.event(self.c,dict(token='fake',event='click'))['ok'])
 def test_no_external_redirects(self):
  for url in ['//evil.test','https://evil.test','/\\evil.test']:
   with self.assertRaises(ValueError):a.target(url)
 def test_schedule(self):
  a.admin(self.c,1,'POST',dict(action='toggle',enabled=True),self.audit);self.c.execute('UPDATE ad_campaigns SET start=9999999999');self.assertIsNone(a.serve(self.c,'home',False))
