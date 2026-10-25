import unittest
import app

class PlaybackAssets(unittest.TestCase):
    def test_tv_and_network_scripts_are_served(self):
        for path in ('/tv-experience.js','/network-playback.js'):
            response=[]
            data=b''.join(app.app({'PATH_INFO':path,'REQUEST_METHOD':'GET'},lambda status,headers:response.append((status,dict(headers)))))
            self.assertEqual(response[0][0],'200 OK')
            self.assertIn('text/javascript',response[0][1]['Content-Type'])
            self.assertGreater(len(data),100)
