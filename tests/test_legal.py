import unittest
from test_app import PlatformTests
class LegalTests(unittest.TestCase):
 setUp=PlatformTests.setUp
 req=PlatformTests.req
 def test_public_legal_request_and_private_inbox(self):
  code,result=self.req('/api/legal/request',{'email':'rights@example.com','topic':'Copyright','message':'Please review the content at example media URL.'})
  self.assertEqual(code,200);self.assertTrue(result['reference'])
  self.assertEqual(self.req('/api/admin/legal-requests')[0],403)
 def test_registration_requires_current_policy_acknowledgement(self):
  self.assertEqual(self.req('/api/register',{'email':'legal@example.com','password':'strong-password-123'})[0],400)
