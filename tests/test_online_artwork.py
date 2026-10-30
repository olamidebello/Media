import unittest
from online_artwork import choose
class OnlineArtworkTests(unittest.TestCase):
 def candidate(self,**changes):
  info={'url':'https://upload.wikimedia.org/example.svg','mime':'image/svg+xml','descriptionurl':'https://commons.wikimedia.org/wiki/File:BBC_News_2022.svg','extmetadata':{'ImageDescription':{'value':'BBC News television logo'},'LicenseShortName':{'value':'Public domain'},'Artist':{'value':'<b>BBC</b>'}}};info.update(changes)
  return {'title':'File:BBC News 2022.svg','index':1,'imageinfo':[info]}
 def test_matching_logo_retains_plain_attribution(self):
  result=choose('BBC News HD',[self.candidate()]);self.assertEqual(result['credit'],'BBC');self.assertEqual(result['license'],'Public domain');self.assertTrue(result['source'].startswith('https://commons.wikimedia.org/'))
 def test_unrelated_and_unlicensed_results_are_not_assigned(self):
  self.assertIsNone(choose('Football Africa',[self.candidate()]));self.assertIsNone(choose('BBC News',[self.candidate(extmetadata={})]));self.assertIsNone(choose('BBC News',[self.candidate(url='https://example.com/unknown.svg')]))
