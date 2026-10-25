"""Admin-only operational activity; no passwords, IPs or precise coordinates."""
import time,json

def init(c):
 c.executescript('''CREATE TABLE IF NOT EXISTS activity(id INTEGER PRIMARY KEY,user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,kind TEXT,event TEXT,detail TEXT,created INTEGER);CREATE INDEX IF NOT EXISTS activity_time ON activity(created);''')

def settings(c):
 d={r['key']:r['value'] for r in c.execute("SELECT key,value FROM settings WHERE key IN ('activity_enabled','activity_days')")}
 return d.get('activity_enabled','1')=='1',int(d.get('activity_days','90'))

def record(c,user,kind,event,detail=''):
 on,days=settings(c)
 if not on:return
 now=int(time.time());c.execute('DELETE FROM activity WHERE created<?',(now-days*86400,))
 c.execute('INSERT INTO activity(user_id,kind,event,detail,created) VALUES(?,?,?,?,?)',(user,kind,str(event)[:100],str(detail)[:160],now))

def manage(c,user,method,b,q,audit):
 if method=='POST':
  action=b.get('action')
  if action=='settings':
   days=int(b.get('days',90))
   if not 7<=days<=365:raise ValueError('Retention must be 7–365 days')
   for k,v in [('activity_enabled','1' if b.get('enabled') is True else '0'),('activity_days',str(days))]:c.execute('INSERT OR REPLACE INTO settings VALUES(?,?)',(k,v))
   c.execute('DELETE FROM activity WHERE created<?',(int(time.time())-days*86400,))
  elif action=='purge':
   if b.get('confirm')!='DELETE ACTIVITY':raise ValueError('Confirmation required')
   c.execute('DELETE FROM activity')
  else:raise ValueError('Unknown activity action')
  audit(c,user,'activity_'+action)
 on,days=settings(c);now=int(time.time());c.execute('DELETE FROM activity WHERE created<?',(now-days*86400,))
 where=['1=1'];args=[]
 for key,col in [('kind','a.kind'),('user','a.user_id')]:
  val=q.get(key,[''])[0]
  if val:where.append(col+'=?');args.append(val)
 term=q.get('search',[''])[0][:100]
 if term:where.append('(a.event LIKE ? OR a.detail LIKE ? OR u.email LIKE ?)');args.extend(['%'+term+'%']*3)
 offset=max(0,min(100000,int(q.get('offset',[0])[0])))
 base=' FROM activity a LEFT JOIN users u ON u.id=a.user_id WHERE '+' AND '.join(where)
 total=c.execute('SELECT count(*)'+base,args).fetchone()[0]
 records=[dict(r) for r in c.execute('SELECT a.*,u.email'+base+' ORDER BY a.id DESC LIMIT 100 OFFSET ?',args+[offset])]
 counts={r['kind']:r['n'] for r in c.execute('SELECT kind,count(*) n FROM activity GROUP BY kind')}
 downloads=[dict(r) for r in c.execute("SELECT detail AS package,event,count(*) AS count FROM activity WHERE kind='download' GROUP BY detail,event ORDER BY count DESC")]
 locations=[dict(r) for r in c.execute("SELECT detail AS country,count(*) AS count FROM activity WHERE kind='location' GROUP BY detail ORDER BY count DESC")]
 return dict(records=records,total=total,offset=offset,counts=counts,downloads=downloads,locations=locations,enabled=on,days=days)
