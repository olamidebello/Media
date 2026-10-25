import sqlite3,unittest
from collections import Counter
from iptv import download,parse,refresh
class SamsungChannels(unittest.TestCase):
 def test_supplied_complete_entries_and_country_variants(self):
  text=download('samsung');items,skipped=parse(text)
  self.assertEqual(len(items),64);self.assertEqual(skipped,0);self.assertEqual(len({x['url'] for x in items}),64)
  self.assertEqual({x['category'] for x in items},{'United Kingdom','United States','Canada'})
  self.assertEqual(sum(x['name']=='21 Jump Street' for x in items),2)
  self.assertTrue(all(x['url'].startswith('https://jmp2.uk/stvp-') for x in items))
  self.assertIn('url-tvg=',text);self.assertNotIn('Are We There Yet?',text)
 def test_deduplication_keeps_disabled_preferences_and_groups(self):
  c=sqlite3.connect(':memory:');c.executescript('CREATE TABLE channels(id INTEGER PRIMARY KEY,name TEXT,url TEXT,category TEXT,enabled INTEGER DEFAULT 1);CREATE TABLE settings(key TEXT PRIMARY KEY,value TEXT);')
  self.assertEqual(refresh(c,'samsung')['added'],64);c.execute('UPDATE channels SET enabled=0')
  self.assertEqual(refresh(c,'samsung')['existing'],64)
  self.assertEqual(c.execute('SELECT sum(enabled) FROM channels').fetchone()[0],0)
  self.assertEqual(c.execute('SELECT category FROM channels WHERE name=?',('&TV',)).fetchone()[0],'United Kingdom')
