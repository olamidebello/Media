import sqlite3,unittest
import iptv
class RequestedSourceTests(unittest.TestCase):
 def test_sources(self):
  self.assertEqual(len(iptv.REQUESTED_SOURCES),42)
  self.assertTrue(all(k in iptv.SOURCES for k in iptv.REQUESTED_SOURCES))
  self.assertEqual(iptv.source_url('uk'),iptv.BASE+'countries/gb.m3u')
  self.assertEqual(iptv.source_url('free-tv'),'https://raw.githubusercontent.com/Free-TV/IPTV/master/playlist.m3u8')
 def test_duplicate_disabled_and_external_pages(self):
  c=sqlite3.connect(':memory:');c.executescript('CREATE TABLE channels(id INTEGER PRIMARY KEY,name,url,category,enabled);CREATE TABLE settings(key PRIMARY KEY,value);')
  text='#EXTM3U\n#EXTINF:-1 group-title="News",Test\nhttps://example.com/live.m3u8\n#EXTINF:-1,External\nhttps://www.youtube.com/@channel/live\n'
  a=iptv.refresh(c,'free-tv',text);self.assertEqual(a['added'],1);self.assertEqual(a['skipped'],1)
  c.execute('UPDATE channels SET enabled=0')
  b=iptv.refresh(c,'index-country',text);self.assertEqual(b['added'],0);self.assertEqual(c.execute('SELECT enabled FROM channels').fetchone()[0],0)
