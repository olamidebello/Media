import unittest
from test_app import PlatformTests,app
class MarketplaceAPITests(unittest.TestCase):
 req=PlatformTests.req
 register=PlatformTests.register
 def setUp(self):PlatformTests.setUp(self)
 def test_admin_routes_require_admin_and_public_catalog_hides_fulfillment(self):
  profile=self.register()
  for path in ('/api/admin/people','/api/admin/market'):self.assertEqual(self.req(path)[0],403)
  with app.db() as c:c.execute("UPDATE users SET role='admin'")
  self.assertEqual(self.req('/api/admin/people',{'action':'create_group','name':'Test group'})[0],200)
  self.assertEqual(self.req('/api/admin/market',{'action':'product','title':'Resource','price':'2.00','currency':'USD','active':True,'fulfillment':'PRIVATE'})[0],200)
  catalog=self.req('/api/market')[1];self.assertNotIn('fulfillment',catalog['products'][0])
  with app.db() as c:c.execute('UPDATE profiles SET kids=1 WHERE id=?',(profile,))
  self.assertEqual(self.req('/api/market/checkout',{'profile_id':profile,'product_id':1,'gateway':'stripe','request_key':'test-request-key-000'})[0],403)
