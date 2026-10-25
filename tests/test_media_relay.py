import unittest
import socket
from unittest.mock import patch
import media_relay as relay

class RelayTests(unittest.TestCase):
    def test_tokens_require_owner_signature_and_fresh_expiry(self):
        with patch('media_relay.time.time',return_value=1000):
            url=relay.sign('secret','http://example.com/live.m3u8',7,'channel:1')
            token=url.partition('token=')[2]
            self.assertEqual(relay.verify('secret',token,7),('http://example.com/live.m3u8','channel:1'))
            for secret,uid in [('wrong',7),('secret',8)]:
                with self.assertRaises(PermissionError):relay.verify(secret,token,uid)
        with patch('media_relay.time.time',return_value=1000+relay.TTL+1):
            with self.assertRaises(PermissionError):relay.verify('secret',token,7)

    def test_hls_nested_variants_audio_keys_and_segments_are_relayed(self):
        manifest=b'#EXTM3U\n#EXT-X-MEDIA:TYPE=AUDIO,URI="audio/index.m3u8"\n#EXT-X-KEY:METHOD=AES-128,URI="http://keys.example/key"\n#EXT-X-STREAM-INF:BANDWIDTH=1000\n../low/index.m3u8\nsegment.ts\n'
        with patch('media_relay.fetch',return_value=(manifest,'http://cdn.example/live/master.m3u8',200,{})):
            data,status,headers=relay.relay('http://cdn.example/live/master.m3u8','secret',7,'channel:1')
        self.assertNotIn(b'http://',data)
        self.assertEqual(status,200)
        import re
        tokens=re.findall(r'/api/playback/resource\?token=([^"\n]+)',data.decode())
        urls=[relay.verify('secret',t,7)[0] for t in tokens]
        self.assertEqual(urls,['http://cdn.example/live/audio/index.m3u8','http://keys.example/key','http://cdn.example/low/index.m3u8','http://cdn.example/live/segment.ts'])

    def test_private_dns_and_mixed_public_private_dns_are_rejected(self):
        def address(ip):return (socket.AF_INET,socket.SOCK_STREAM,6,'',(ip,80))
        for addresses in [[address('127.0.0.1')],[address('8.8.8.8'),address('169.254.169.254')]]:
            with patch('media_relay.socket.getaddrinfo',return_value=addresses):
                with self.assertRaises(ValueError):relay.target('http://cdn.example/segment.ts')
        for url in ['http://localhost/x','http://user:pass@example.com/x','file:///etc/passwd']:
            with self.assertRaises(ValueError):relay.target(url)

    def test_redirect_to_private_destination_is_rejected_before_connection(self):
        conn=unittest.mock.MagicMock()
        conn.getresponse.return_value.status=302
        conn.getresponse.return_value.getheader.return_value='http://127.0.0.1/private'
        address=(socket.AF_INET,socket.SOCK_STREAM,6,'',('8.8.8.8',80))
        with patch('media_relay.socket.getaddrinfo',return_value=[address]),patch('media_relay.http.client.HTTPConnection',return_value=conn):
            with self.assertRaises(ValueError):relay.fetch('http://cdn.example/x')
        self.assertEqual(conn.request.call_count,1)
        conn.close.assert_called()

class PlatformRelayTests(unittest.TestCase):
    def setUp(self):
        import test_app
        self.helper=test_app.PlatformTests()
        self.helper.setUp()

    def test_only_signed_in_users_get_relay_urls_and_disabled_channels_stop(self):
        import app
        with app.db() as c:
            c.execute("INSERT INTO channels(name,url,category) VALUES('News','http://example.com/live.m3u8','News')")
        anonymous=self.helper.req('/api/guide')[1]['channels'][0]
        self.assertEqual(anonymous['playback_url'],'')
        self.helper.register()
        channel=self.helper.req('/api/guide')[1]['channels'][0]
        self.assertTrue(channel['url'].startswith('http://'))
        token=channel['playback_url'].partition('token=')[2]
        with app.db() as c:c.execute('UPDATE channels SET enabled=0')
        with patch('media_relay.relay') as network:
            self.assertEqual(self.helper.req('/api/playback/resource?token='+token)[0],403)
            network.assert_not_called()
        self.helper.cookie=''
        self.assertEqual(self.helper.req('/api/playback/resource?token='+token)[0],403)

    def test_resource_route_serves_rewritten_playlist_without_origin_url_input(self):
        import app,io
        self.helper.register()
        with app.db() as c:c.execute("INSERT INTO channels(name,url,category) VALUES('News','http://example.com/live.m3u8','News')")
        url=self.helper.req('/api/guide')[1]['channels'][0]['playback_url']
        env={'REQUEST_METHOD':'GET','PATH_INFO':'/api/playback/resource','QUERY_STRING':url.partition('?')[2],'HTTP_COOKIE':self.helper.cookie,'HTTP_HOST':'localhost','wsgi.input':io.BytesIO(b'')}
        captured=[]
        with patch('media_relay.fetch',return_value=(b'#EXTM3U\nhttp://cdn.example/segment.ts\n','http://example.com/live.m3u8',200,{})):
            data=b''.join(app.app(env,lambda status,headers:captured.append((status,dict(headers)))))
        self.assertEqual(captured[0][0],'200 OK')
        self.assertIn(b'/api/playback/resource?token=',data)
        self.assertNotIn(b'http://',data)
        self.assertEqual(captured[0][1]['Cross-Origin-Resource-Policy'],'same-origin')
        self.assertNotIn('Access-Control-Allow-Origin',captured[0][1])
