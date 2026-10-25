import json,sqlite3,unittest
from pathlib import Path
from iptv import download,parse,refresh
class InternationalChannels(unittest.TestCase):
 def test_streams_are_normalized_and_provider_pages_are_separate(self):
  items,skipped=parse(download('international'));self.assertEqual(len(items),46);self.assertEqual(skipped,0)
  self.assertEqual(len({x['url'] for x in items}),46)
  self.assertEqual({x['category'] for x in items},{'Albania','Andorra','Argentina','Armenia','Australia'})
  self.assertTrue(all(x['url'].startswith('https://') and '.m3u8' in x['url'] for x in items))
  self.assertTrue(any(x['url'].startswith('https://45.226.28.9:8085/') for x in items))
  self.assertNotIn('SBS Food',{x['name'] for x in items})
 def test_provider_urls_not_inserted_as_streams(self):
  root=Path(__file__).resolve().parents[1];providers=json.loads((root/'data/International_Providers.json').read_text());self.assertEqual(len(providers),16)
  self.assertTrue(all('youtube.com/' in p['url'] or 'twitch.tv/' in p['url'] for p in providers))
  self.assertTrue(all(not p['kids'] for p in providers))
 def test_import_preserves_existing_disabled_state(self):
  c=sqlite3.connect(':memory:');c.executescript('CREATE TABLE channels(id INTEGER PRIMARY KEY,name TEXT,url TEXT,category TEXT,enabled INTEGER DEFAULT 1);CREATE TABLE settings(key TEXT PRIMARY KEY,value TEXT);')
  self.assertEqual(refresh(c,'international')['added'],46);c.execute('UPDATE channels SET enabled=0');self.assertEqual(refresh(c,'international')['existing'],46);self.assertEqual(c.execute('SELECT sum(enabled) FROM channels').fetchone()[0],0)
