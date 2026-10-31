import unittest,time,os,hashlib,io
from unittest.mock import patch
import test_stations as station_tests
import app,community

class CommunityTests(unittest.TestCase):
 setUp=station_tests.StationTests.setUp
 tearDown=station_tests.StationTests.tearDown
 req=station_tests.StationTests.req
 create=station_tests.StationTests.create
 post=station_tests.StationTests.post
 def ready(self):
  sid=self.create()
  with app.db() as c:c.execute('UPDATE stations SET approved=1')
  return sid
 def actor(self,uid):
  self.cookie='media_session='+('owner' if uid==1 else 'other');self.csrf='csrf' if uid==1 else 'othercsrf';self.profile=uid
 def action(self,sid,action,**b):return self.req('/api/community/channel',{'station_id':sid,'profile_id':getattr(self,'profile',1),'action':action,**b})
 def snapshot(self,sid,view=''):return self.req('/api/community/channel?station_id='+str(sid)+'&profile_id='+str(getattr(self,'profile',1))+('&view='+view if view else ''))
 def test_ownership_kids_and_private_state(self):
  sid=self.ready();self.actor(2)
  self.assertEqual(self.action(sid,'customize',title='stolen')[0],403)
  self.assertEqual(self.snapshot(sid,'dashboard')[0],403)
  self.assertEqual(self.req('/api/community/channel?station_id='+str(sid)+'&profile_id=3')[0],403)
  self.actor(1);self.csrf='wrong';self.assertEqual(self.action(sid,'message',message='hello')[0],403)
  self.cookie='';self.csrf='';status,data=self.req('/api/community/channel?station_id='+str(sid));self.assertEqual(status,200);self.assertNotIn('blocked_terms',data['channel']);self.assertNotIn('key_hash',str(data))
 def test_follow_notifications_and_discovery(self):
  sid=self.ready();self.actor(2);self.assertEqual(self.action(sid,'follow',enabled=True,notify=True)[0],200)
  self.assertEqual(len(self.req('/api/community/directory?following=1&profile_id=2')[1]),1)
  self.actor(1);self.post(sid,'save',name='Community TV',category='Gaming',source='external',external_url='https://example.com/live.m3u8')
  with app.db() as c:c.execute('UPDATE stations SET approved=1')
  self.post(sid,'start');self.post(sid,'start');self.actor(2)
  self.assertEqual(len(self.req('/api/community/notifications?profile_id=2')[1]),1)
  self.assertEqual(self.req('/api/community/directory?q=no-match&profile_id=2')[1],[])
 def test_chat_review_reply_moderation_and_blocking(self):
  sid=self.ready();self.actor(2)
  status,msg=self.action(sid,'message',message='https://example.com link');self.assertEqual(status,200);self.assertEqual(msg['state'],'held')
  self.assertEqual(self.snapshot(sid,'chat')[1]['messages'],[])
  self.actor(1);self.assertEqual(self.action(sid,'moderate',operation='approve',message_id=msg['id'])[0],200)
  self.assertEqual(self.action(sid,'moderate',operation='pin',message_id=msg['id'])[0],200)
  self.assertTrue(self.snapshot(sid,'chat')[1]['messages'][0]['pinned'])
  self.assertEqual(self.action(sid,'message',message='Reply',reply_id=9999)[0],400)
  self.assertEqual(self.action(sid,'moderate',operation='ban',user_id=2)[0],200)
  self.actor(2);self.assertEqual(self.action(sid,'message',message='bypassing ban')[0],403)
  self.actor(1);self.action(sid,'block',user_id=2,enabled=True);self.assertEqual(self.snapshot(sid,'chat')[1]['messages'],[])
 def test_restrictions_roles_and_owner_protection(self):
  sid=self.ready();self.action(sid,'restrictions',slow=0,followers_only=True,members_only=False,blocked_terms='forbidden')
  self.actor(2);self.assertEqual(self.action(sid,'message',message='hello')[0],403)
  self.action(sid,'follow',enabled=True,notify=False);self.assertEqual(self.action(sid,'message',message='forbidden')[0],400)
  self.actor(1);self.action(sid,'role',user_id=2,role='moderator');self.actor(2)
  self.assertEqual(self.snapshot(sid,'dashboard')[0],200)
  self.assertEqual(self.action(sid,'moderate',operation='ban',user_id=1)[0],403)
  self.assertEqual(self.action(sid,'bot_key',name='escalation')[0],403)
  self.actor(1);self.action(sid,'moderate',operation='ban',user_id=2);self.actor(2);self.assertEqual(self.snapshot(sid,'dashboard')[0],403)
 def test_points_are_timed_and_predictions_settle_once(self):
  sid=self.ready()
  with app.db() as c:c.execute("UPDATE stations SET broadcasting=1,source='external',external_url='https://example.com/live.m3u8'")
  self.actor(2);now=int(time.time());self.action(sid,'heartbeat')
  self.assertEqual(self.snapshot(sid)[1]['me']['points'],0)
  for step in (30,60):
   with patch('time.time',return_value=now+step):self.action(sid,'heartbeat')
  self.assertEqual(self.snapshot(sid)[1]['me']['points'],10)
  self.actor(1);self.assertEqual(self.action(sid,'poll',title='Outcome?',kind='prediction',options=['A','B'],duration=15)[0],200)
  pid=self.snapshot(sid)[1]['polls'][0]['id'];self.actor(2)
  self.assertEqual(self.action(sid,'vote',poll_id=pid,choice=0,stake=10)[0],200)
  self.assertEqual(self.action(sid,'vote',poll_id=pid,choice=0,stake=10)[0],400)
  self.actor(1);self.assertEqual(self.action(sid,'resolve',poll_id=pid,winner=0)[0],400)
  with app.db() as c:c.execute('UPDATE community_polls SET ends=?',(now-1,))
  self.assertEqual(self.action(sid,'resolve',poll_id=pid,winner=0)[0],200)
  self.assertEqual(self.action(sid,'resolve',poll_id=pid,winner=0)[0],400)
  self.actor(2);self.assertEqual(self.snapshot(sid)[1]['me']['points'],10)
 def test_rewards_refunds_are_idempotent_and_scoped(self):
  sid=self.ready();self.action(sid,'reward',title='Pick a song',cost=10);reward=self.snapshot(sid)[1]['rewards'][0]['id'];self.actor(2);self.snapshot(sid)
  with app.db() as c:c.execute('UPDATE community_members SET points=10 WHERE station_id=? AND user_id=2',(sid,))
  self.assertEqual(self.action(sid,'redeem',reward_id=reward)[0],200)
  self.assertEqual(self.action(sid,'redeem',reward_id=reward)[0],400)
  self.actor(1);r=self.snapshot(sid,'dashboard')[1]['redemptions'][0]
  self.assertEqual(self.action(sid,'redemption',redemption_id=r['id'],status='refunded')[0],200)
  self.assertEqual(self.action(sid,'redemption',redemption_id=r['id'],status='refunded')[0],400)
  self.actor(2);self.assertEqual(self.snapshot(sid)[1]['me']['points'],10)
 def test_scoped_bot_keys_expire_revoke_and_cannot_moderate(self):
  sid=self.ready();code,data=self.action(sid,'bot_key',name='Fixture');self.assertEqual(code,200);token=data['token']
  with app.db() as c:
   key=c.execute('SELECT * FROM community_bot_keys').fetchone();self.assertEqual(key['token_hash'],hashlib.sha256(token.encode()).hexdigest())
   self.assertNotEqual(key['token_hash'],token)
   result=community.bot(c,token,'POST',{'action':'message','message':'Bot hello'},{});self.assertEqual(result['state'],'public')
   with self.assertRaises(PermissionError):community.bot(c,token,'POST',{'action':'moderate'}, {})
   c.execute('DELETE FROM community_bot_keys')
   with self.assertRaises(PermissionError):community.bot(c,token,'GET',{}, {})
 def test_verified_gift_pass_and_duplicate_verification(self):
  sid=self.ready();self.actor(2);self.snapshot(sid);self.actor(1)
  self.action(sid,'offer',title='Member pass',kind='membership',amount=500,currency='USD')
  offer=self.snapshot(sid)[1]['offers'][0]['id']
  self.assertEqual(self.action(sid,'checkout',offer_id=offer,gateway='stripe',request_key='fixture-payment-12345')[0],400)
  with app.db() as c:
   c.execute('UPDATE community_channels SET monetized=1');c.execute("INSERT OR REPLACE INTO settings VALUES('gateway_stripe','on')")
  with patch.dict(os.environ,{'MEDIA_STRIPE_SECRET_KEY':'sk_live_fixture_placeholder'}),patch('commerce.request',return_value={'id':'cs_fixture','url':'https://checkout.stripe.com/c/fixture'}):
   code,order=self.action(sid,'checkout',offer_id=offer,gateway='stripe',request_key='fixture-payment-12345',gift_handle='viewer2');self.assertEqual(code,200,order)
  with app.db() as c:self.assertEqual(c.execute('SELECT member_until FROM community_members WHERE user_id=2').fetchone()[0],0)
  response={'payment_status':'paid','client_reference_id':order['id'],'amount_total':500,'currency':'usd'}
  with patch('commerce.request',return_value=response):self.assertEqual(self.action(sid,'verify',order_id=order['id'])[0],200)
  self.actor(2);until=self.snapshot(sid)[1]['me']['member_until'];self.assertGreater(until,int(time.time())+29*86400)
  self.actor(1);self.action(sid,'verify',order_id=order['id']);self.actor(2);self.assertEqual(self.snapshot(sid)[1]['me']['member_until'],until)
 def test_invalid_payment_amount_cannot_grant_membership(self):
  sid=self.ready();self.action(sid,'offer',title='Pass',kind='membership',amount=500,currency='USD');offer=self.snapshot(sid)[1]['offers'][0]['id']
  with app.db() as c:c.execute('UPDATE community_channels SET monetized=1');c.execute("INSERT OR REPLACE INTO settings VALUES('gateway_stripe','on')")
  with patch.dict(os.environ,{'MEDIA_STRIPE_SECRET_KEY':'sk_live_fixture_placeholder'}),patch('commerce.request',return_value={'id':'cs_fixture','url':'https://checkout.stripe.com/c/fixture'}):
   code,o=self.action(sid,'checkout',offer_id=offer,gateway='stripe',request_key='fixture-invalid-12345');self.assertEqual(code,200)
  with patch('commerce.request',return_value={'payment_status':'paid','client_reference_id':o['id'],'amount_total':1,'currency':'usd'}):self.assertEqual(self.action(sid,'verify',order_id=o['id'])[0],400)
  self.assertEqual(self.snapshot(sid)[1]['me']['member_until'],0)
 def test_static_assets_embed_policy_and_private_embed_denial(self):
  for path in ('/community','/community.js','/community.css','/embed/station','/station-embed.js'):
   status=[];headers=[]
   output=b''.join(app.app({'PATH_INFO':path,'REQUEST_METHOD':'GET'},lambda code,h:(status.append(code),headers.extend(h))))
   self.assertTrue(status[0].startswith('200'),(path,status,output[:200]))
   self.assertTrue(output)
   policy=dict(headers).get('Content-Security-Policy','')
   self.assertIn('frame-ancestors https:' if path=='/embed/station' else "frame-ancestors 'none'",policy)
  sid=self.ready()
  with app.db() as c:
   public_id=c.execute('SELECT public_id FROM stations WHERE id=?',(sid,)).fetchone()[0]
   c.execute('UPDATE stations SET approved=0')
  self.assertEqual(self.req('/api/community/embed?id='+public_id)[0],404)
  self.assertEqual(self.req('/api/community/bot')[0],403)
 def test_chat_default_handles_cannot_be_claimed_by_another_account(self):
  sid=self.ready()
  self.assertEqual(self.action(sid,'handle',handle='viewer2')[0],400)
  self.actor(2);self.assertEqual(self.snapshot(sid)[0],200)
 def test_customization_url_safety_and_creator_library(self):
  sid=self.ready()
  self.assertEqual(self.action(sid,'customize',title='Title',tags='gaming',panels=[{'title':'Bad','url':'javascript:alert(1)'}],emotes=[])[0],400)
  self.assertEqual(self.action(sid,'video',title='Clip',kind='clip',url='https://example.com/video.mp4',start=10,end=5)[0],400)
  self.assertEqual(self.action(sid,'video',title='Clip',kind='clip',url='https://example.com/video.mp4',start=10,end=20)[0],200)
  self.assertEqual(len(self.snapshot(sid)[1]['videos']),1)
  self.actor(2);self.assertEqual(self.action(sid,'delete_video',video_id=1)[0],403)

if __name__=='__main__':unittest.main()
