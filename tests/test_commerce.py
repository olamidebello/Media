import unittest,tempfile,sqlite3,os
from pathlib import Path
from unittest.mock import patch
import app,commerce,people
class CommerceTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.dbpatch=patch.object(app,'DB',str(Path(self.temp.name)/'test.db'));self.dbpatch.start();app.init();self.c=app.db();self.c.execute("INSERT INTO users(id,email,password,role) VALUES(1,'admin@example.com','hash','admin'),(2,'buyer@example.com','hash','viewer')")
  commerce.admin(self.c,1,'POST',{'action':'product','title':'Digital guide','price':'5.25','currency':'USD','fulfillment':'Your private instructions','active':True},app.audit)
  self.c.execute("INSERT INTO settings VALUES('gateway_stripe','on'),('gateway_paystack','on')");self.c.commit();self.env=patch.dict(os.environ,{'MEDIA_STRIPE_SECRET_KEY':'sk_test_fake','MEDIA_PAYSTACK_SECRET_KEY':'sk_test_fake'});self.env.start()
 def tearDown(self):self.env.stop();self.c.close();self.dbpatch.stop();self.temp.cleanup()
 def checkout(self,gateway='stripe'):
  response={'id':'cs_test_x','url':'https://checkout.stripe.com/c/test'} if gateway=='stripe' else {'status':True,'data':{'authorization_url':'https://checkout.paystack.com/test'}}
  with patch.object(commerce,'request',return_value=response) as provider:
   order=commerce.checkout(self.c,2,'buyer@example.com',{'gateway':gateway,'product_id':1,'request_key':'test-request-key-123','amount':1});self.c.commit();return order,provider
 def test_server_price_and_idempotent_checkout(self):
  order,provider=self.checkout();self.assertEqual(provider.call_args.args[2]['line_items[0][price_data][unit_amount]'],525)
  self.assertEqual(commerce.orders(self.c,2)[0]['amount'],525);self.assertNotIn('fulfillment',commerce.orders(self.c,2)[0])
  with patch.object(commerce,'request') as duplicate:
   again=commerce.checkout(self.c,2,'buyer@example.com',{'gateway':'stripe','product_id':1,'request_key':'test-request-key-123'});self.assertEqual(order['id'],again['id']);duplicate.assert_not_called()
 def test_payment_requires_matching_provider_confirmation(self):
  order,_=self.checkout();reference=order['id'];good={'payment_status':'paid','client_reference_id':reference,'amount_total':525,'currency':'usd'}
  with patch.object(commerce,'request',return_value={**good,'amount_total':1}):
   with self.assertRaises(ValueError):commerce.verify(self.c,2,reference,app.audit)
  self.assertEqual(commerce.orders(self.c,2)[0]['status'],'pending')
  with patch.object(commerce,'request',return_value=good):self.assertEqual(commerce.verify(self.c,2,reference,app.audit)['status'],'paid')
  self.assertEqual(commerce.orders(self.c,2)[0]['fulfillment'],'Your private instructions')
  with patch.object(commerce,'request') as provider:
   commerce.verify(self.c,2,reference,app.audit);provider.assert_not_called()
  with self.assertRaises(LookupError):commerce.verify(self.c,1,reference,app.audit)
 def test_paystack_verifies_currency_reference_and_amount(self):
  order,_=self.checkout('paystack');reference=order['id']
  with patch.object(commerce,'request',return_value={'status':True,'data':{'status':'success','amount':525,'currency':'USD','reference':reference}}):self.assertEqual(commerce.verify(self.c,2,reference,app.audit)['status'],'paid')
 def test_disabled_gateways_and_invalid_prices(self):
  self.c.execute("UPDATE settings SET value='off'")
  with self.assertRaises(ValueError):self.checkout()
  for price in ['NaN','Infinity','1.001','-5']:
   with self.assertRaises(ValueError):commerce.admin(self.c,1,'POST',{'action':'product','title':'Invalid','price':price},app.audit)
 def test_group_bulk_controls_protect_actor_and_revoke_sessions(self):
  people.manage(self.c,1,'POST',{'action':'create_group','name':'Creators'},app.audit)
  people.manage(self.c,1,'POST',{'action':'group_add','id':1,'ids':[2]},app.audit)
  people.manage(self.c,1,'POST',{'action':'group_add','id':1,'ids':[2]},app.audit)
  self.assertEqual(self.c.execute('SELECT count(*) FROM user_group_members').fetchone()[0],1)
  for action,fields in [('bulk_active',{'active':False}),('bulk_role',{'role':'viewer'})]:
   with self.assertRaises(ValueError):people.manage(self.c,1,'POST',{'action':action,'ids':[1],**fields},app.audit)
  self.c.execute("INSERT INTO sessions VALUES('session',2,'csrf',9999999999)")
  people.manage(self.c,1,'POST',{'action':'bulk_active','active':False,'ids':[2]},app.audit)
  self.assertEqual(self.c.execute('SELECT count(*) FROM sessions').fetchone()[0],0)
  people.manage(self.c,1,'POST',{'action':'delete_group','id':1},app.audit)
  self.assertEqual(self.c.execute('SELECT count(*) FROM users').fetchone()[0],2)
