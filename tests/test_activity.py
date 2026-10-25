import sqlite3,time,unittest
import activity
class ActivityTests(unittest.TestCase):
 def setUp(self):
  self.c=sqlite3.connect(':memory:');self.c.row_factory=sqlite3.Row
  self.c.executescript('CREATE TABLE users(id INTEGER PRIMARY KEY,email TEXT);INSERT INTO users VALUES(1,"a@example.com");CREATE TABLE settings(key TEXT PRIMARY KEY,value TEXT);')
  activity.init(self.c);self.audit=lambda *args:None
 def test_filters_counts(self):
  activity.record(self.c,1,'location','selected_country','NG');activity.record(self.c,None,'download','served','app.apk')
  r=activity.manage(self.c,1,'GET',{}, {'kind':['location']},self.audit)
  self.assertEqual(r['total'],1);self.assertEqual(r['locations'][0]['country'],'NG');self.assertEqual(r['downloads'][0]['count'],1)
 def test_disable_and_purge(self):
  activity.manage(self.c,1,'POST',{'action':'settings','enabled':False,'days':7},{},self.audit)
  activity.record(self.c,1,'user','test');self.assertEqual(self.c.execute('SELECT count(*) FROM activity').fetchone()[0],0)
  with self.assertRaises(ValueError):activity.manage(self.c,1,'POST',{'action':'purge'},{},self.audit)
 def test_retention(self):
  self.c.execute('INSERT INTO activity(user_id,kind,event,created) VALUES(1,"user","old",?)',(int(time.time())-100*86400,))
  r=activity.manage(self.c,1,'GET',{}, {},self.audit);self.assertEqual(r['total'],0)
