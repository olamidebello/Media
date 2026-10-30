import sqlite3,unittest
from iptv import parse,refresh
from artwork import init,safe_url
class ArtworkTests(unittest.TestCase):
 def test_refresh_preserves_disabled_channel_and_fills_logo(self):
  c=sqlite3.connect(':memory:');c.executescript('CREATE TABLE channels(id INTEGER PRIMARY KEY,name TEXT,url TEXT,category TEXT,enabled INTEGER DEFAULT 1);CREATE TABLE videos(id INTEGER PRIMARY KEY);CREATE TABLE settings(key TEXT PRIMARY KEY,value TEXT);');init(c)
  c.execute("INSERT INTO channels(name,url,category,enabled) VALUES('Sports','https://example.com/live.m3u8','Sports',0)")
  text='#EXTM3U\n#EXTINF:-1 tvg-logo="https://example.com/logo.png" group-title="Sports",Sports\nhttps://example.com/live.m3u8\n'
  refresh(c,'sports',text)
  self.assertEqual(c.execute('SELECT enabled,thumbnail FROM channels').fetchone(),(0,'https://example.com/logo.png'))
 def test_image_urls_reject_embedded_credentials_and_script_schemes(self):
  for url in ['javascript:alert(1)','https://user:secret@example.com/poster.png','data:image/svg+xml,test','http://example.com/logo.png']:
   self.assertEqual(safe_url(url),'')
