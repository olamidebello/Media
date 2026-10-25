import sqlite3,unittest
from iptv import download,parse,refresh
class PlutoChannels(unittest.TestCase):
 def test_supplied_complete_entries(self):
  text=download('pluto');items,skipped=parse(text);self.assertEqual(len(items),95);self.assertEqual(skipped,0);self.assertEqual(len({i['url'] for i in items}),95)
  self.assertTrue({'Movies','Sports','Kids','United Kingdom','Canada'}.issubset({i['category'] for i in items}))
  self.assertEqual(sum(i['name']=='Andromeda' for i in items),3)
  self.assertIn('BET Cinema',text);self.assertTrue(all(i['url'].startswith('https://jmp2.uk/plu-') for i in items))
 def test_import_preserves_groups_and_disabled_preferences(self):
  c=sqlite3.connect(':memory:');c.executescript('CREATE TABLE channels(id INTEGER PRIMARY KEY,name TEXT,url TEXT,category TEXT,enabled INTEGER DEFAULT 1);CREATE TABLE settings(key TEXT PRIMARY KEY,value TEXT);')
  self.assertEqual(refresh(c,'pluto')['added'],95);c.execute('UPDATE channels SET enabled=0');self.assertEqual(refresh(c,'pluto')['existing'],95);self.assertEqual(c.execute('SELECT sum(enabled) FROM channels').fetchone()[0],0)
  self.assertEqual(c.execute('SELECT category FROM channels WHERE name=?',('BBC News',)).fetchone()[0],'News + Opinion')

 def test_refines_generic_us_group_without_overwriting_admin_preferences(self):
  c=sqlite3.connect(':memory:');c.executescript('CREATE TABLE channels(id INTEGER PRIMARY KEY,name TEXT,url TEXT,category TEXT,enabled INTEGER DEFAULT 1);CREATE TABLE settings(key TEXT PRIMARY KEY,value TEXT);')
  text='#EXTM3U\n#EXTINF:-1 group-title="United States",Existing\nhttps://example.com/live.m3u8'
  refresh(c,'pluto',text);c.execute('UPDATE channels SET enabled=0')
  updated=text.replace('United States','Movies');refresh(c,'pluto',updated)
  self.assertEqual(c.execute('SELECT category,enabled FROM channels').fetchone(),('Movies',0))
  c.execute("UPDATE channels SET category='Custom'");refresh(c,'pluto',updated)
  self.assertEqual(c.execute('SELECT category FROM channels').fetchone()[0],'Custom')
