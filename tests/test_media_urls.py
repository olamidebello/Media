import unittest
from media_urls import https_url
from app import valid_url
from iptv import parse, stream_url

class URLUpgrades(unittest.TestCase):
    def test_upgrade_preserves_source_path_and_query(self):
        for normalize in (https_url,):
            self.assertEqual(normalize(' http://Example.com:80/Live/A.m3u8?token=AbC%2F9#part '), 'https://example.com/Live/A.m3u8?token=AbC%2F9#part')
            self.assertEqual(normalize('http://example.com:1935/live/a.m3u8'), 'https://example.com:1935/live/a.m3u8')
            self.assertEqual(normalize('https://example.com/a'), 'https://example.com/a')
    def test_reject_invalid_schemes_credentials_and_ports(self):
        for value in ('javascript:alert(1)', 'file:///tmp/a', '//example.com/a', 'http://user:pass@example.com/a', 'http://example.com:bad/a', 'http://example.com/a\nHeader:evil', 'http://example.com\\evil/a'):
            with self.assertRaises(ValueError): https_url(value)
        self.assertFalse(stream_url('http://127.0.0.1/a'))
    def test_import_preserves_distinct_origins(self):
        import sqlite3
        from iptv import refresh
        c=sqlite3.connect(':memory:')
        c.executescript('CREATE TABLE channels(id INTEGER PRIMARY KEY,name TEXT,url TEXT,category TEXT,enabled INTEGER DEFAULT 1);CREATE TABLE settings(key TEXT PRIMARY KEY,value TEXT);')
        result=refresh(c,'working','#EXTM3U\n#EXTINF:-1,One\nhttp://example.com/a\n#EXTINF:-1,Two\nhttps://example.com/a')
        self.assertEqual(result['added'],2)
        self.assertEqual(result['existing'],0)
        self.assertEqual(c.execute('SELECT url FROM channels').fetchone()[0],'http://example.com/a')

    def test_deployment_preserves_existing_origins_idempotently(self):
        import tempfile
        import app
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp, patch.object(app, 'DB', tmp+'/test.db'):
            app.init()
            with app.db() as c:
                c.execute("INSERT INTO channels(name,url) VALUES('Legacy','http://example.com:80/live?token=x')")
                c.execute("INSERT INTO videos(title,url) VALUES('Legacy','http://example.com/video.mp4')")
            app.init()
            app.init()
            with app.db() as c:
                self.assertEqual(c.execute('SELECT url FROM channels').fetchone()[0],'http://example.com:80/live?token=x')
                self.assertEqual(c.execute('SELECT url FROM videos').fetchone()[0],'http://example.com/video.mp4')

