import sqlite3, unittest
from unittest.mock import patch
import support

class SupportTests(unittest.TestCase):
 def setUp(self):
  self.c=sqlite3.connect(':memory:');self.c.row_factory=sqlite3.Row
  self.c.execute('PRAGMA foreign_keys=ON');self.c.executescript('CREATE TABLE users(id INTEGER PRIMARY KEY); INSERT INTO users VALUES(1); INSERT INTO users VALUES(2);')
  support.init(self.c);self.audit=lambda *args:None
 def create(self):return support.tickets(self.c,1,False,'POST',{'subject':'No sound','message':'Muted channel','category':'playback'},self.audit)[0]
 def test_private_tickets_and_reply(self):
  t=self.create();self.assertEqual(support.tickets(self.c,2,False,'GET',{},self.audit),[])
  with self.assertRaises(PermissionError):support.tickets(self.c,2,False,'POST',{'action':'reply','id':t['id'],'message':'bad'},self.audit)
  r=support.tickets(self.c,2,True,'POST',{'action':'reply','id':t['id'],'message':'Check volume'},self.audit)
  self.assertEqual(r[0]['status'],'waiting_user');self.assertEqual(r[0]['messages'][-1]['staff'],1)
 def test_status_permissions(self):
  t=self.create()
  with self.assertRaises(ValueError):support.tickets(self.c,1,False,'POST',{'action':'status','id':t['id'],'status':'resolved'},self.audit)
 def test_rate_limit(self):
  for _ in range(5):self.create()
  with self.assertRaises(ValueError):self.create()
 def test_ai_unconfigured(self):
  with patch.dict('os.environ',{'OPENAI_API_KEY':''}):self.assertFalse(support.ask(self.c,1,{'question':'Help'})['available'])
 def test_ai_failure_redacted(self):
  with patch.dict('os.environ',{'OPENAI_API_KEY':'private'}),patch('urllib.request.OpenerDirector.open',side_effect=RuntimeError('private')):
   r=support.ask(self.c,1,{'question':'Help'});self.assertFalse(r['available']);self.assertNotIn('private',r['answer'])
