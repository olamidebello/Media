import sqlite3,unittest
from iptv import download,parse,refresh
class RokuChannels(unittest.TestCase):
 def test_complete_supplied_entries(self):
  text=download('roku');items,skipped=parse(text);self.assertEqual(len(items),43);self.assertEqual(skipped,0);self.assertEqual(len({i['url'] for i in items}),43)
  self.assertEqual(next(i for i in items if i['name']=='Unbeaten Sports')['category'],'3X3 Basketball')
  self.assertTrue(any(i['name']=="Hell's Kitchen | Kitchen Nightmares" for i in items))
  self.assertNotIn('5a1dec25daac971f191b10e808ec0c5d',text)
 def test_repeated_import_preserves_groups_and_disabled_states(self):
  c=sqlite3.connect(':memory:');c.executescript('CREATE TABLE channels(id INTEGER PRIMARY KEY,name TEXT,url TEXT,category TEXT,enabled INTEGER DEFAULT 1);CREATE TABLE settings(key TEXT PRIMARY KEY,value TEXT);')
  self.assertEqual(refresh(c,'roku')['added'],43);c.execute('UPDATE channels SET enabled=0');self.assertEqual(refresh(c,'roku')['existing'],43);self.assertEqual(c.execute('SELECT sum(enabled) FROM channels').fetchone()[0],0)
  self.assertEqual(c.execute('SELECT category FROM channels WHERE name=?',('Iron Chef',)).fetchone()[0],'Cooking')
