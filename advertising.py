"""First-party display campaigns, with bounded anonymous exposure tokens."""
import time,secrets
from urllib.parse import urlparse
PLACEMENTS=('home','guide','catalog')
def init(c):
 c.executescript('''CREATE TABLE IF NOT EXISTS ad_campaigns(id INTEGER PRIMARY KEY,name TEXT,title TEXT,description TEXT,image TEXT,target TEXT,placement TEXT,active INTEGER DEFAULT 0,start INTEGER,end INTEGER,priority INTEGER DEFAULT 0,cap INTEGER DEFAULT 0,impressions INTEGER DEFAULT 0,clicks INTEGER DEFAULT 0);
 CREATE TABLE IF NOT EXISTS ad_exposures(token TEXT PRIMARY KEY,campaign_id INTEGER REFERENCES ad_campaigns(id) ON DELETE CASCADE,created INTEGER,seen INTEGER DEFAULT 0,clicked INTEGER DEFAULT 0);''')
def enabled(c):
 r=c.execute("SELECT value FROM settings WHERE key='advertising_enabled'").fetchone();return bool(r and r[0]=='1')
def target(value):
 value=str(value)
 if not value.startswith('/') or value.startswith('//') or '\\' in value or any(ord(x)<32 for x in value) or urlparse(value).netloc:raise ValueError('Use a platform path such as /?market_order=...')
 return value[:500]
def admin(c,user,method,b,audit):
 if method=='POST':
  action=b.get('action');cid=int(b.get('id',0))
  if action=='toggle':c.execute("INSERT OR REPLACE INTO settings VALUES('advertising_enabled',?)",('1' if b.get('enabled') is True else '0',))
  elif action=='delete':c.execute('DELETE FROM ad_campaigns WHERE id=?',(cid,))
  elif action=='save':
   name=str(b.get('name','')).strip()[:120];title=str(b.get('title','')).strip()[:150]
   if not name or not title:raise ValueError('Campaign name and title required')
   place=b.get('placement');start=int(b.get('start') or 0);end=int(b.get('end') or 0)
   if place not in PLACEMENTS or (end and end<=start):raise ValueError('Invalid placement or schedule')
   image=str(b.get('image','')).strip();u=urlparse(image)
   if image and (u.scheme!='https' or not u.hostname or u.username or u.password):raise ValueError('Use an HTTPS image URL')
   priority=int(b.get('priority',0));cap=int(b.get('cap',0))
   if not 0<=priority<=100 or not 0<=cap<=100000000:raise ValueError('Invalid priority or impression limit')
   values=(name,title,str(b.get('description',''))[:400],image,target(b.get('target','/')),place,int(b.get('active') is True),start,end,priority,cap)
   if cid:
    if not c.execute('SELECT id FROM ad_campaigns WHERE id=?',(cid,)).fetchone():raise LookupError('Campaign unavailable')
    c.execute('UPDATE ad_campaigns SET name=?,title=?,description=?,image=?,target=?,placement=?,active=?,start=?,end=?,priority=?,cap=? WHERE id=?',values+(cid,))
   else:c.execute('INSERT INTO ad_campaigns(name,title,description,image,target,placement,active,start,end,priority,cap) VALUES(?,?,?,?,?,?,?,?,?,?,?)',values)
  else:raise ValueError('Unknown advertising action')
  audit(c,user,'advertising_'+str(action))
 return {'enabled':enabled(c),'campaigns':[dict(r) for r in c.execute('SELECT * FROM ad_campaigns ORDER BY id DESC')],'placements':PLACEMENTS}
def serve(c,placement,kids):
 now=int(time.time());c.execute('DELETE FROM ad_exposures WHERE created<?',(now-3600,))
 if kids or not enabled(c) or placement not in PLACEMENTS:return None
 if c.execute('SELECT count(*) FROM ad_exposures').fetchone()[0]>=10000:return None
 r=c.execute('SELECT * FROM ad_campaigns WHERE active=1 AND placement=? AND start<=? AND (end=0 OR end>?) AND (cap=0 OR impressions<cap) ORDER BY priority DESC,random() LIMIT 1',(placement,now,now)).fetchone()
 if not r:return None
 token=secrets.token_urlsafe(32);c.execute('INSERT INTO ad_exposures(token,campaign_id,created) VALUES(?,?,?)',(token,r['id'],now))
 return {k:r[k] for k in ('id','title','description','image','target')}|{'token':token}
def event(c,b):
 token=str(b.get('token',''))[:100];kind=b.get('event')
 if kind not in ('impression','click'):raise ValueError('Invalid advertising event')
 r=c.execute('SELECT * FROM ad_exposures WHERE token=? AND created>?',(token,int(time.time())-3600)).fetchone()
 if not r:return {'ok':False}
 col='seen' if kind=='impression' else 'clicked';metric='impressions' if kind=='impression' else 'clicks'
 changed=c.execute('UPDATE ad_exposures SET '+col+'=1 WHERE token=? AND '+col+'=0',(token,)).rowcount
 if changed:c.execute('UPDATE ad_campaigns SET '+metric+'='+metric+'+1 WHERE id=?',(r['campaign_id'],))
 return {'ok':True}
