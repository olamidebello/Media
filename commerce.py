"""Hosted Stripe/Paystack checkout. Card data never enters this application."""
import os,json,time,secrets,re
from decimal import Decimal,InvalidOperation
from urllib.request import Request,build_opener,HTTPRedirectHandler
from urllib.parse import urlencode,quote,urlsplit
GATEWAYS={'stripe':('MEDIA_STRIPE_SECRET_KEY','https://api.stripe.com/v1/'),'paystack':('MEDIA_PAYSTACK_SECRET_KEY','https://api.paystack.co/')}
CURRENCIES={'USD','NGN','GHS','KES','ZAR','EUR','GBP'}

def init(c):
 c.executescript('''CREATE TABLE IF NOT EXISTS market_products(id INTEGER PRIMARY KEY,title TEXT NOT NULL,description TEXT NOT NULL,amount INTEGER NOT NULL,currency TEXT NOT NULL,kind TEXT NOT NULL,fulfillment TEXT NOT NULL DEFAULT '',active INTEGER NOT NULL DEFAULT 0);
 CREATE TABLE IF NOT EXISTS market_orders(id TEXT PRIMARY KEY,user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,product_id INTEGER REFERENCES market_products(id),title TEXT NOT NULL,amount INTEGER NOT NULL,currency TEXT NOT NULL,fulfillment TEXT NOT NULL,gateway TEXT NOT NULL,status TEXT NOT NULL,provider_id TEXT,checkout_url TEXT,request_key TEXT NOT NULL,created INTEGER NOT NULL,paid INTEGER,UNIQUE(user_id,request_key));''')

def gateways(c):
 return [{'id':key,'configured':bool(os.environ.get(value[0])),'mode':'test' if os.environ.get(value[0],'').startswith('sk_test_') else 'live' if os.environ.get(value[0],'').startswith('sk_live_') else 'unconfigured','enabled':c.execute('SELECT value FROM settings WHERE key=?',('gateway_'+key,)).fetchone() is not None and c.execute('SELECT value FROM settings WHERE key=?',('gateway_'+key,)).fetchone()[0]=='on'} for key,value in GATEWAYS.items()]

class NoRedirect(HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):raise ValueError('Payment API redirected unexpectedly')

def request(gateway,path,data=None,reference=None):
 env,base=GATEWAYS[gateway];secret=os.environ.get(env,'')
 if not secret:raise ValueError('Gateway is not configured')
 headers={'Authorization':'Bearer '+secret,'Accept':'application/json'}
 if data is None:payload=None
 elif gateway=='stripe':payload=urlencode(data).encode();headers['Content-Type']='application/x-www-form-urlencoded'
 else:payload=json.dumps(data).encode();headers['Content-Type']='application/json'
 if gateway=='stripe' and reference:headers['Idempotency-Key']=reference
 try:
  with build_opener(NoRedirect()).open(Request(base+path,data=payload,headers=headers),timeout=15) as r:
   raw=r.read(1024*1024+1)
   if len(raw)>1024*1024:raise ValueError('Oversized payment response')
   return json.loads(raw)
 except Exception as e:raise ValueError('Payment provider request failed. Check the gateway configuration or verify your order before trying again.') from e

def products(c,admin=False):
 fields='*' if admin else 'id,title,description,amount,currency,kind'
 return [dict(r) for r in c.execute('SELECT '+fields+' FROM market_products'+('' if admin else ' WHERE active=1')+' ORDER BY id DESC')]

def orders(c,uid=None):
 values=() if uid is None else (uid,)
 records=[dict(r) for r in c.execute('SELECT * FROM market_orders'+(' WHERE user_id=?' if uid is not None else '')+' ORDER BY created DESC LIMIT 200',values)]
 for row in records:
  if row['status']!='paid':row.pop('fulfillment',None)
 return records

def admin(c,actor,method,b,audit):
 if method=='GET':return {'products':products(c,True),'orders':orders(c),'gateways':gateways(c)}
 action=b.get('action')
 if action=='product':
  title=str(b.get('title','')).strip()[:200];currency=str(b.get('currency','USD')).upper();kind=b.get('kind','digital')
  try:
   price=Decimal(str(b.get('price','0')))
   if not price.is_finite() or price*100!=(price*100).to_integral_value():raise ValueError()
   amount=int(price*100)
  except (InvalidOperation,ValueError,OverflowError):raise ValueError('Use a price with at most two decimal places')
  if not title or not 100<=amount<=100000000 or currency not in CURRENCIES or kind not in ('digital','support'):raise ValueError('Title, supported currency and price between 1 and 1,000,000 required')
  values=(title,str(b.get('description',''))[:3000],amount,currency,kind,str(b.get('fulfillment',''))[:5000],int(bool(b.get('active'))))
  target=int(b.get('id') or 0)
  if target:
   if not c.execute('UPDATE market_products SET title=?,description=?,amount=?,currency=?,kind=?,fulfillment=?,active=? WHERE id=?',values+(target,)).rowcount:raise LookupError('Product not found')
  else:target=c.execute('INSERT INTO market_products(title,description,amount,currency,kind,fulfillment,active) VALUES(?,?,?,?,?,?,?)',values).lastrowid
 elif action=='gateway':
  gateway=b.get('gateway')
  if gateway not in GATEWAYS:raise ValueError('Unknown gateway')
  c.execute('INSERT OR REPLACE INTO settings VALUES(?,?)',('gateway_'+gateway,'on' if b.get('enabled') else 'off'))
 else:raise ValueError('Unknown marketplace action')
 audit(c,actor,'market '+action);return {'ok':True}

def checkout(c,uid,email,b):
 gateway=b.get('gateway');key=str(b.get('request_key',''))
 if not re.fullmatch(r'[a-zA-Z0-9-]{16,80}',key):raise ValueError('Checkout request key required')
 if gateway not in GATEWAYS or not any(g['id']==gateway and g['enabled'] and g['configured'] for g in gateways(c)):raise ValueError('Gateway unavailable')
 product=c.execute('SELECT * FROM market_products WHERE id=? AND active=1',(int(b.get('product_id') or 0),)).fetchone()
 if not product:raise LookupError('Product unavailable')
 if gateway=='paystack' and product['currency'] not in ('NGN','GHS','ZAR','KES','USD'):raise ValueError('Choose a different gateway for this currency')
 old=c.execute('SELECT * FROM market_orders WHERE user_id=? AND request_key=?',(uid,key)).fetchone()
 if old:
  if old['product_id']!=product['id'] or old['gateway']!=gateway:raise ValueError('Checkout key already used')
  return {'id':old['id'],'status':old['status'],'checkout_url':old['checkout_url']}
 if c.execute('SELECT count(*) FROM market_orders WHERE user_id=? AND created>?',(uid,int(time.time())-3600)).fetchone()[0]>=20:raise ValueError('Checkout limit reached. Review your existing orders.')
 reference='amh-'+secrets.token_hex(16);now=int(time.time())
 c.execute('INSERT INTO market_orders(id,user_id,product_id,title,amount,currency,fulfillment,gateway,status,request_key,created) VALUES(?,?,?,?,?,?,?,?,?,?,?)',(reference,uid,product['id'],product['title'],product['amount'],product['currency'],product['fulfillment'],gateway,'pending',key,now));c.commit()
 origin=os.environ.get('MEDIA_PUBLIC_URL','https://media.africandroid.world').rstrip('/')
 parsed=urlsplit(origin)
 if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password:raise ValueError('Configure an HTTPS public platform URL')
 return_url=origin+'/?market_order='+reference
 try:
  if gateway=='stripe':
   data=request(gateway,'checkout/sessions',{'mode':'payment','client_reference_id':reference,'metadata[order_id]':reference,'success_url':return_url,'cancel_url':return_url,'line_items[0][price_data][currency]':product['currency'].lower(),'line_items[0][price_data][unit_amount]':product['amount'],'line_items[0][price_data][product_data][name]':product['title'],'line_items[0][quantity]':1,'customer_email':email},reference)
   provider_id=data['id'];url=data['url'];host='checkout.stripe.com'
  else:
   result=request(gateway,'transaction/initialize',{'email':email,'amount':product['amount'],'currency':product['currency'],'reference':reference,'callback_url':return_url})
   if not result.get('status'):raise ValueError('Payment provider rejected checkout')
   data=result['data'];provider_id=reference;url=data['authorization_url'];host='checkout.paystack.com'
  parsed=urlsplit(url)
  if parsed.scheme!='https' or parsed.hostname!=host or parsed.username or parsed.password:raise ValueError('Unexpected payment checkout URL')
  c.execute('UPDATE market_orders SET provider_id=?,checkout_url=? WHERE id=?',(provider_id,url,reference));return {'id':reference,'status':'pending','checkout_url':url}
 except Exception:
  c.execute("UPDATE market_orders SET status='checkout_error' WHERE id=?",(reference,));c.commit();raise

def verify(c,uid,reference,audit):
 order=c.execute('SELECT * FROM market_orders WHERE id=? AND user_id=?',(reference,uid)).fetchone()
 if not order:raise LookupError('Order not found')
 if order['status']=='paid':return {'id':reference,'status':'paid'}
 if order['gateway']=='stripe':
  if not order['provider_id']:raise ValueError('Checkout was not created; no payment is confirmed')
  data=request('stripe','checkout/sessions/'+quote(order['provider_id'],safe=''))
  paid=data.get('payment_status')=='paid';matches=data.get('client_reference_id')==reference and data.get('amount_total')==order['amount'] and str(data.get('currency','')).upper()==order['currency']
 else:
  result=request('paystack','transaction/verify/'+quote(reference,safe=''))
  if not result.get('status'):raise ValueError('Payment verification unavailable')
  data=result['data'];paid=data.get('status')=='success';matches=data.get('reference')==reference and data.get('amount')==order['amount'] and data.get('currency')==order['currency']
 if paid and not matches:raise ValueError('Payment details do not match this order. Contact the administrator.')
 if paid:
  c.execute("UPDATE market_orders SET status='paid',paid=? WHERE id=? AND status!='paid'",(int(time.time()),reference));audit(c,uid,'payment verified order='+reference)
 return {'id':reference,'status':'paid' if paid else 'pending'}
