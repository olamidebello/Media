import importlib.util,pathlib,sqlite3,tempfile,unittest
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('prune',pathlib.Path(__file__).resolve().parents[1]/'tools/prune_channels.py');prune=importlib.util.module_from_spec(spec);spec.loader.exec_module(prune)
class CleanupTests(unittest.TestCase):
 def database(self):
  c=sqlite3.connect(':memory:');c.executescript('CREATE TABLE channels(id INTEGER PRIMARY KEY,name TEXT,url TEXT,enabled INTEGER DEFAULT 1);CREATE TABLE audit(user_id INTEGER,action TEXT,created INTEGER);INSERT INTO channels VALUES(1,"Good","https://example.com/1",1),(2,"Bad","https://example.com/2",1),(3,"Timeout","https://example.com/3",1);');c.commit();return c
 def test_backup_remove_hard_failures_disable_uncertain_and_preserve_good(self):
  c=self.database();results=[{'id':i,'url':'https://example.com/'+str(i),'status':status} for i,status in [(1,'verified'),(2,'unavailable'),(3,'inconclusive')]]
  with tempfile.TemporaryDirectory() as tmp:
   report=prune.apply(c,results,tmp);self.assertEqual(report['removed'],1);self.assertEqual(report['disabled'],1)
   with sqlite3.connect(report['backup']) as b:self.assertEqual(b.execute('SELECT count(*) FROM channels').fetchone()[0],3)
  self.assertEqual(c.execute('SELECT id,enabled FROM channels ORDER BY id').fetchall(),[(1,1),(3,0)])
 def test_zero_success_guard_and_concurrent_admin_edits(self):
  c=self.database()
  with tempfile.TemporaryDirectory() as tmp:
   with self.assertRaises(ValueError):prune.apply(c,[{'id':1,'url':'https://example.com/1','status':'unavailable'}],tmp)
   self.assertEqual(c.execute('SELECT count(*) FROM channels').fetchone()[0],3)
   results=[{'id':1,'url':'https://example.com/1','status':'verified'},{'id':2,'url':'https://example.com/old','status':'unavailable'}]
   self.assertEqual(prune.apply(c,results,tmp)['removed'],0)
 def test_hard_failures_are_rechecked_before_deletion(self):
  rows=[{'id':1,'name':'Transient','url':'https://example.com/a'}]
  with patch.object(prune,'probe',side_effect=[{**rows[0],'status':'unavailable','detail':'HTTP 404'},{**rows[0],'status':'verified','detail':'Media received'}]):self.assertEqual(prune.scan(rows)[0]['status'],'verified')
 def test_private_streams_are_rejected_before_fetch(self):
  with patch.object(prune.socket,'getaddrinfo',return_value=[(2,1,6,'',('127.0.0.1',443))]):
   with self.assertRaises(prune.InvalidStream):prune.public_url('https://example.com/a')
