import unittest,sys,pathlib
from unittest.mock import patch,MagicMock
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import location_channels as location
class LocationTests(unittest.TestCase):
 def test_rejects_arbitrary_fetch_targets(self):
  for code in ['https://localhost','../../private','ZZ']:
   with self.assertRaises(ValueError):location.country_channels(code)
 def test_country_directory_is_cached(self):
  location._cache.clear()
  response=MagicMock();response.read.return_value=b'#EXTM3U\n#EXTINF:-1 group-title="News",Local News\nhttps://example.com/live.m3u8\n'
  opener=MagicMock();opener.open.return_value.__enter__.return_value=response
  with patch('location_channels.build_opener',return_value=opener):
   result=location.country_channels('ng');self.assertEqual(result['country'],'NG');self.assertEqual(len(result['channels']),1)
   self.assertEqual(location.country_channels('NG'),result);self.assertEqual(opener.open.call_count,1)
