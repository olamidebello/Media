import sqlite3,unittest
from iptv import download,parse,refresh
class UploadedSources(unittest.TestCase):
 def test_directory_is_https_unique(self):
  items,skipped=parse(download('uploaded'))
  self.assertEqual(len(items),3581);self.assertEqual(skipped,0)
  self.assertEqual(len({i['url'] for i in items}),len(items))
  self.assertTrue(all(i['url'].startswith('https://') for i in items))
 def test_review_import_preserves_existing_and_requires_enable(self):
  c=sqlite3.connect(':memory:');c.executescript('CREATE TABLE channels(id INTEGER PRIMARY KEY,name TEXT,url TEXT,category TEXT,enabled INTEGER DEFAULT 1);CREATE TABLE settings(key TEXT PRIMARY KEY,value TEXT);')
  sample='#EXTM3U\n#EXTINF:-1 group-title="Sports",Sports One\nhttp://example.com/live.m3u8'
  self.assertEqual(refresh(c,'uploaded',sample)['added'],1)
  self.assertEqual(c.execute('SELECT category,enabled FROM channels').fetchone(),('Sports',0))
  c.execute('UPDATE channels SET enabled=1')
  self.assertEqual(refresh(c,'uploaded',sample)['existing'],1)
  self.assertEqual(c.execute('SELECT enabled FROM channels').fetchone()[0],1)
