import sys, pathlib, sqlite3, unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from iptv import parse, refresh, stream_url, download
from unittest.mock import patch

SAMPLE='''#EXTM3U
#EXTINF:-1 tvg-id="Sport" group-title="Sports",Sport One
https://example.com/live.m3u8
#EXTINF:-1,HTTP channel
http://example.com/live.m3u8
#EXTINF:-1,Local channel
https://127.0.0.1/live.m3u8
'''
class Imports(unittest.TestCase):
 def test_complete_requested_category_directory(self):
  from iptv import SOURCES
  categories=['animation', 'auto', 'business', 'classic', 'comedy', 'cooking', 'culture', 'documentary', 'education', 'entertainment', 'family', 'general', 'interactive', 'kids', 'legislative', 'lifestyle', 'movies', 'music', 'news', 'outdoor', 'public', 'relax', 'religious', 'science', 'series', 'shop', 'sports', 'travel', 'weather', 'undefined']
  self.assertEqual(SOURCES['all'],'index.m3u')
  for category in categories:self.assertEqual(SOURCES[category],'categories/'+category+'.m3u')

 def test_parser_and_safety(self):
  items,skipped=parse(SAMPLE)
  self.assertEqual(len(items),2);self.assertEqual(skipped,1);self.assertEqual(items[0]['category'],'Sports')
  for value in ['file:///etc/passwd','https://localhost/a','https://[::1]/a','https://user:pass@example.com/a']:self.assertFalse(stream_url(value))
 def test_http_upgrade(self):
  from iptv import normalize_media_url
  self.assertEqual(normalize_media_url('http://example.com:80/a.m3u8?token=a%2Fb&x=1'),'https://example.com/a.m3u8?token=a%2Fb&x=1')
  self.assertEqual(normalize_media_url('http://example.com:8080/a'),'https://example.com:8080/a')
  for url in ['http://127.0.0.1/a','http://localhost/a','http://user:pass@example.com/a','http://example.com:bad/a']:
   with self.assertRaises(ValueError):normalize_media_url(url)
 def test_bundled_source_does_not_fetch_remote(self):
  with patch('iptv.Path.read_text',return_value=SAMPLE), patch('iptv.build_opener') as network:
   self.assertEqual(download('working'),SAMPLE)
   network.assert_not_called()
 def test_refresh_keeps_disabled_and_deduplicates(self):
  c=sqlite3.connect(':memory:');c.executescript('CREATE TABLE channels(id INTEGER PRIMARY KEY,name TEXT,url TEXT,category TEXT,enabled INTEGER DEFAULT 1);CREATE TABLE settings(key TEXT PRIMARY KEY,value TEXT);')
  self.assertEqual(refresh(c,'sports',SAMPLE)['added'],1)
  c.execute('UPDATE channels SET enabled=0')
  result=refresh(c,'sports',SAMPLE)
  self.assertEqual(result['added'],0);self.assertEqual(result['existing'],2)
  self.assertEqual(c.execute('SELECT enabled FROM channels').fetchone()[0],0)
  with self.assertRaises(ValueError):refresh(c,'sports','#EXTM3U')
  self.assertEqual(c.execute('SELECT count(*) FROM channels').fetchone()[0],1)
if __name__=='__main__':unittest.main()

