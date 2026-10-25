import sqlite3,unittest
from iptv import download,parse,refresh
class PlutoChannels(unittest.TestCase):
 def test_supplied_complete_entries(self):
  text=download('pluto');items,skipped=parse(text);self.assertEqual(len(items),63);self.assertEqual(skipped,0);self.assertEqual(len({i['url'] for i in items}),63)
  self.assertEqual({i['category'] for i in items},{'United States','United Kingdom','Canada'})
  self.assertEqual(sum(i['name']=='Andromeda' for i in items),3)
  self.assertNotIn('BET Cinema',text);self.assertTrue(all(i['url'].startswith('https://jmp2.uk/plu-') for i in items))
 def test_import_preserves_groups_and_disabled_preferences(self):
  c=sqlite3.connect(':memory:');c.executescript('CREATE TABLE channels(id INTEGER PRIMARY KEY,name TEXT,url TEXT,category TEXT,enabled INTEGER DEFAULT 1);CREATE TABLE settings(key TEXT PRIMARY KEY,value TEXT);')
  self.assertEqual(refresh(c,'pluto')['added'],63);c.execute('UPDATE channels SET enabled=0');self.assertEqual(refresh(c,'pluto')['existing'],63);self.assertEqual(c.execute('SELECT sum(enabled) FROM channels').fetchone()[0],0)
  self.assertEqual(c.execute('SELECT category FROM channels WHERE name=?',('BBC News',)).fetchone()[0],'United States')
