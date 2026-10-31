"""Station communities: bounded polling chat, moderation, engagement and verified passes."""
import hashlib
import json
import re
import secrets
import time
import unicodedata
from stations import active, can_preview, signal, text, url

def init(c):
 c.executescript('''
 CREATE TABLE IF NOT EXISTS community_channels(station_id INTEGER PRIMARY KEY REFERENCES stations(id) ON DELETE CASCADE,
 title TEXT DEFAULT '',captions TEXT DEFAULT '',tags TEXT DEFAULT '',banner TEXT DEFAULT '',panels TEXT DEFAULT '[]',emotes TEXT DEFAULT '[]',member_badge TEXT DEFAULT 'Member',
 slow INTEGER DEFAULT 3,followers_only INTEGER DEFAULT 0,members_only INTEGER DEFAULT 0,blocked_terms TEXT DEFAULT '',
 monetized INTEGER DEFAULT 0,payout_note TEXT DEFAULT '',raid_id INTEGER,raid_until INTEGER DEFAULT 0);
 CREATE TABLE IF NOT EXISTS community_accounts(user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,handle TEXT UNIQUE NOT NULL,avatar TEXT DEFAULT '');
 CREATE TABLE IF NOT EXISTS community_follows(station_id INTEGER REFERENCES stations(id) ON DELETE CASCADE,user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,notify INTEGER DEFAULT 1,created INTEGER,PRIMARY KEY(station_id,user_id));
 CREATE TABLE IF NOT EXISTS community_members(station_id INTEGER REFERENCES stations(id) ON DELETE CASCADE,user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,role TEXT DEFAULT 'viewer',banned INTEGER DEFAULT 0,timeout INTEGER DEFAULT 0,points INTEGER DEFAULT 0,member_until INTEGER DEFAULT 0,PRIMARY KEY(station_id,user_id));
 CREATE TABLE IF NOT EXISTS community_blocks(user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,target_id INTEGER REFERENCES users(id) ON DELETE CASCADE,PRIMARY KEY(user_id,target_id));
 CREATE TABLE IF NOT EXISTS community_chat(id INTEGER PRIMARY KEY,station_id INTEGER REFERENCES stations(id) ON DELETE CASCADE,user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,body TEXT NOT NULL,reply_id INTEGER,pinned INTEGER DEFAULT 0,state TEXT DEFAULT 'public',created INTEGER);
 CREATE INDEX IF NOT EXISTS community_chat_station ON community_chat(station_id,id);
 CREATE TABLE IF NOT EXISTS community_presence(station_id INTEGER REFERENCES stations(id) ON DELETE CASCADE,user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,seen INTEGER,award INTEGER,started INTEGER,PRIMARY KEY(station_id,user_id));
 CREATE TABLE IF NOT EXISTS community_stats(station_id INTEGER REFERENCES stations(id) ON DELETE CASCADE,day TEXT,visits INTEGER DEFAULT 0,watch_seconds INTEGER DEFAULT 0,peak INTEGER DEFAULT 0,PRIMARY KEY(station_id,day));
 CREATE TABLE IF NOT EXISTS community_notifications(id INTEGER PRIMARY KEY,user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,station_id INTEGER REFERENCES stations(id) ON DELETE CASCADE,body TEXT,created INTEGER,seen INTEGER DEFAULT 0);
 CREATE TABLE IF NOT EXISTS community_polls(id INTEGER PRIMARY KEY,station_id INTEGER REFERENCES stations(id) ON DELETE CASCADE,title TEXT,options TEXT,kind TEXT,ends INTEGER,locked INTEGER DEFAULT 0,settled INTEGER DEFAULT 0,winner INTEGER);
 CREATE TABLE IF NOT EXISTS community_votes(poll_id INTEGER REFERENCES community_polls(id) ON DELETE CASCADE,user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,choice INTEGER,stake INTEGER DEFAULT 0,PRIMARY KEY(poll_id,user_id));
 CREATE TABLE IF NOT EXISTS community_rewards(id INTEGER PRIMARY KEY,station_id INTEGER REFERENCES stations(id) ON DELETE CASCADE,title TEXT,cost INTEGER,enabled INTEGER DEFAULT 1);
 CREATE TABLE IF NOT EXISTS community_redemptions(id INTEGER PRIMARY KEY,reward_id INTEGER REFERENCES community_rewards(id) ON DELETE CASCADE,user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,cost INTEGER,status TEXT DEFAULT 'pending',created INTEGER);
 CREATE TABLE IF NOT EXISTS community_videos(id INTEGER PRIMARY KEY,station_id INTEGER REFERENCES stations(id) ON DELETE CASCADE,title TEXT,kind TEXT,url TEXT,thumbnail TEXT,captions TEXT,start REAL DEFAULT 0,end REAL DEFAULT 0,created INTEGER);
 CREATE TABLE IF NOT EXISTS community_reports(id INTEGER PRIMARY KEY,user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,station_id INTEGER REFERENCES stations(id) ON DELETE CASCADE,message_id INTEGER,reason TEXT,status TEXT DEFAULT 'open',created INTEGER);
 CREATE TABLE IF NOT EXISTS community_bot_keys(id INTEGER PRIMARY KEY,station_id INTEGER REFERENCES stations(id) ON DELETE CASCADE,token_hash TEXT UNIQUE,name TEXT,expires INTEGER,window INTEGER DEFAULT 0,calls INTEGER DEFAULT 0);
 CREATE TABLE IF NOT EXISTS community_events(id INTEGER PRIMARY KEY,station_id INTEGER REFERENCES stations(id) ON DELETE CASCADE,kind TEXT,object_id INTEGER,created INTEGER);
 CREATE TABLE IF NOT EXISTS community_offers(id INTEGER PRIMARY KEY,station_id INTEGER REFERENCES stations(id) ON DELETE CASCADE,product_id INTEGER UNIQUE REFERENCES market_products(id),kind TEXT,active INTEGER DEFAULT 1);
 CREATE TABLE IF NOT EXISTS community_payments(order_id TEXT PRIMARY KEY REFERENCES market_orders(id),station_id INTEGER REFERENCES stations(id) ON DELETE CASCADE,beneficiary INTEGER REFERENCES users(id) ON DELETE CASCADE,kind TEXT,applied INTEGER DEFAULT 0);
 ''')

def config(c,sid):
 c.execute('INSERT OR IGNORE INTO community_channels(station_id) VALUES(?)',(sid,))
 return c.execute('SELECT * FROM community_channels WHERE station_id=?',(sid,)).fetchone()

def member(c,sid,uid):
 if not uid:return None
 c.execute('INSERT OR IGNORE INTO community_members(station_id,user_id) VALUES(?,?)',(sid,uid))
 c.execute('INSERT OR IGNORE INTO community_accounts(user_id,handle) VALUES(?,?)',(uid,'viewer'+str(uid)))
 return c.execute('SELECT * FROM community_members WHERE station_id=? AND user_id=?',(sid,uid)).fetchone()

def staff(c,s,uid):
 return can_preview(c,s,uid) or bool(uid and member(c,s['id'],uid)['role']=='moderator')

def station(c,sid,uid):
 s=active(c,sid)
 if not s or (not s['approved'] and not can_preview(c,s,uid)):raise LookupError('Channel unavailable')
 return s

def event(c,sid,kind,obj=0):
 c.execute('INSERT INTO community_events(station_id,kind,object_id,created) VALUES(?,?,?,?)',(sid,kind,obj,int(time.time())))
 c.execute('DELETE FROM community_events WHERE station_id=? AND id NOT IN (SELECT id FROM community_events WHERE station_id=? ORDER BY id DESC LIMIT 1000)',(sid,sid))

def notify_start(c,sid):
 s=active(c,sid)
 if not s or not s['approved']:return
 now=int(time.time())
 if c.execute('SELECT id FROM community_events WHERE station_id=? AND kind=? AND created>?',(sid,'broadcast_enabled',now-300)).fetchone():return
 c.execute('INSERT INTO community_notifications(user_id,station_id,body,created) SELECT user_id,station_id,?,? FROM community_follows WHERE station_id=? AND notify=1',(s['name']+' enabled a broadcast. Open the channel to check its live signal.',now,sid))
 event(c,sid,'broadcast_enabled')

def chat(c,s,uid,after=0,moderation=False):
 args=[s['id']];where='station_id=?'
 if not moderation:where+=" AND state='public'"
 if uid:
  where+=' AND (user_id IS NULL OR user_id NOT IN (SELECT target_id FROM community_blocks WHERE user_id=?))';args.append(uid)
 if after:where+=' AND id>?';args.append(after)
 records=[dict(r) for r in c.execute('SELECT * FROM community_chat WHERE '+where+' ORDER BY id DESC LIMIT 100',args)][::-1]
 if not after:
  pinned=c.execute('SELECT * FROM community_chat WHERE '+where+' AND pinned=1 ORDER BY id DESC LIMIT 1',args).fetchone()
  if pinned and not any(r['id']==pinned['id'] for r in records):records.insert(0,dict(pinned))
 now=int(time.time())
 for r in records:
  a=c.execute('SELECT handle,avatar FROM community_accounts WHERE user_id=?',(r['user_id'],)).fetchone()
  m=c.execute('SELECT role,member_until FROM community_members WHERE station_id=? AND user_id=?',(s['id'],r['user_id'])).fetchone()
  r['handle']=a[0] if a else 'Station bot'
  r['avatar']=a[1] if a else ''
  r['badge']='Broadcaster' if r['user_id']==s['owner_id'] else 'Moderator' if m and m['role']=='moderator' else config(c,s['id'])['member_badge'] if m and m['member_until']>now else ''
 return records

def send(c,s,uid,b,bot=False):
 now=int(time.time());sid=s['id'];cfg=config(c,sid);m=member(c,sid,uid)
 mod=staff(c,s,uid)
 if not bot and (m['banned'] or m['timeout']>now):raise PermissionError('Chat access is restricted on this channel')
 if not bot and not mod:
  if cfg['followers_only'] and not c.execute('SELECT 1 FROM community_follows WHERE station_id=? AND user_id=?',(sid,uid)).fetchone():raise PermissionError('Follow this channel to chat')
  if cfg['members_only'] and m['member_until']<=now:raise PermissionError('An active channel membership is required to chat')
 body=text(b,'message',500,True);fold=unicodedata.normalize('NFKC',body).casefold()
 if any(word.strip() in fold for word in cfg['blocked_terms'].casefold().splitlines() if word.strip()):raise ValueError('Message contains a blocked term')
 author=None if bot else uid
 recent=c.execute('SELECT created FROM community_chat WHERE station_id=? AND user_id IS ? ORDER BY id DESC LIMIT 1',(sid,author)).fetchone()
 if recent and now-recent[0]<max(1,cfg['slow'] if not mod else 1):raise ValueError('Slow mode: wait before posting again')
 if c.execute('SELECT count(*) FROM community_chat WHERE station_id=? AND user_id IS ? AND created>?',(sid,author,now-60)).fetchone()[0]>=20:raise ValueError('Chat rate limit reached')
 reply=int(b.get('reply_id') or 0)
 if reply and not c.execute("SELECT id FROM community_chat WHERE id=? AND station_id=? AND state='public'",(reply,sid)).fetchone():raise ValueError('Reply target unavailable')
 state='held' if not mod and ('http://' in fold or 'https://' in fold or re.search(r'(.)\1{9,}',fold)) else 'public'
 mid=c.execute('INSERT INTO community_chat(station_id,user_id,body,reply_id,state,created) VALUES(?,?,?,?,?,?)',(sid,author,body,reply or None,state,now)).lastrowid
 if state=='public':
  event(c,sid,'chat',mid)
  for handle in sorted(set(re.findall(r'@([A-Za-z][A-Za-z0-9_]{2,23})',body)))[:5]:
   target=c.execute('SELECT user_id FROM community_accounts WHERE lower(handle)=lower(?)',(handle,)).fetchone()
   if target and target[0]!=uid and not c.execute('SELECT 1 FROM community_blocks WHERE user_id=? AND target_id=?',(target[0],uid)).fetchone():
    c.execute('INSERT INTO community_notifications(user_id,station_id,body,created) VALUES(?,?,?,?)',(target[0],sid,'You were mentioned in channel chat.',now))
 c.execute('DELETE FROM community_chat WHERE station_id=? AND created<?',(sid,now-30*86400))
 if body in ('!help','!schedule','!points') and state=='public':
  answer='Commands: !help, !schedule, !points. Use Polls and Rewards below the player.'
  if body=='!points':answer='Your free channel points: '+str(m['points'])
  if body=='!schedule':
   p=c.execute('SELECT title FROM station_programs WHERE station_id=? AND end>? ORDER BY start LIMIT 1',(sid,now)).fetchone();answer='Next scheduled program: '+p[0] if p else 'No upcoming programs listed.'
  c.execute('INSERT INTO community_chat(station_id,user_id,body,created) VALUES(?,NULL,?,?)',(sid,answer,now))
 return {'id':mid,'state':state}

def directory(c,uid,q):
 term=q.get('q',[''])[0].casefold()[:100];category=q.get('category',[''])[0];tag=q.get('tag',[''])[0].casefold();following=q.get('following',[''])[0]=='1'
 result=[]
 for s in c.execute('SELECT s.* FROM stations s JOIN users u ON u.id=s.owner_id WHERE s.approved=1 AND s.suspended=0 AND u.active=1 ORDER BY s.id DESC LIMIT 1000'):
  cfg=config(c,s['id']);follow=bool(uid and c.execute('SELECT 1 FROM community_follows WHERE station_id=? AND user_id=?',(s['id'],uid)).fetchone())
  if following and not follow:continue
  if term and term not in (s['name']+' '+s['description']+' '+cfg['title']+' '+cfg['tags']).casefold():continue
  if category and s['category']!=category:continue
  if tag and tag not in [x.strip().casefold() for x in cfg['tags'].split(',')]:continue
  followers=c.execute('SELECT count(*) FROM community_follows WHERE station_id=?',(s['id'],)).fetchone()[0]
  result.append({'id':s['id'],'public_id':s['public_id'],'name':s['name'],'category':s['category'],'logo':s['logo'],'title':cfg['title'],'tags':cfg['tags'],'signal':signal(s),'followers':followers,'following':follow})
 return sorted(result,key=lambda s:(s['following'],s['signal']=='live',s['followers']),reverse=True)[:200]

def snapshot(c,s,uid):
 sid=s['id'];cfg=config(c,sid);m=member(c,sid,uid);now=int(time.time());mod=staff(c,s,uid)
 polls=[]
 for p in c.execute('SELECT * FROM community_polls WHERE station_id=? ORDER BY id DESC LIMIT 10',(sid,)):
  d=dict(p);d['options']=json.loads(d['options']);d['votes']=[dict(v) for v in c.execute('SELECT choice,count(*) AS votes,sum(stake) AS stake FROM community_votes WHERE poll_id=? GROUP BY choice',(p['id'],))];mine=c.execute('SELECT choice,stake FROM community_votes WHERE poll_id=? AND user_id=?',(p['id'],uid)).fetchone();d['mine']=dict(mine) if mine else None;polls.append(d)
 follows=c.execute('SELECT notify FROM community_follows WHERE station_id=? AND user_id=?',(sid,uid)).fetchone()
 offers=[dict(o) for o in c.execute('SELECT o.id,o.kind,p.title,p.amount,p.currency FROM community_offers o JOIN market_products p ON p.id=o.product_id WHERE o.station_id=? AND o.active=1',(sid,))]
 from commerce import gateways
 payment_gateways=[g for g in gateways(c) if g['configured'] and g['enabled'] and g['mode']=='live'] if cfg['monetized'] else []
 raid=active(c,cfg['raid_id']) if cfg['raid_until']>now and cfg['raid_id'] else None
 if raid and not raid['approved']:raid=None
 return {'station':{k:s[k] for k in ('id','public_id','name')},'broadcasting':bool(s['broadcasting']),'signal':signal(s),'channel':{k:cfg[k] for k in ('title','captions','tags','banner','panels','emotes','member_badge','slow','followers_only','members_only','monetized')},'following':bool(follows),'notifications':bool(follows and follows[0]),'followers':c.execute('SELECT count(*) FROM community_follows WHERE station_id=?',(sid,)).fetchone()[0],
 'avatar':c.execute('SELECT avatar FROM community_accounts WHERE user_id=?',(uid,)).fetchone()[0] if uid else '', 'handle':c.execute('SELECT handle FROM community_accounts WHERE user_id=?',(uid,)).fetchone()[0] if uid else '', 'me':dict(m) if m else None,'owner':s['owner_id']==uid,'moderator':mod,
 'messages':chat(c,s,uid), 'polls':polls,'rewards':[dict(r) for r in c.execute('SELECT * FROM community_rewards WHERE station_id=? AND enabled=1',(sid,))],
 'videos':[dict(v) for v in c.execute('SELECT * FROM community_videos WHERE station_id=? ORDER BY id DESC LIMIT 200',(sid,))], 'raid':{'name':raid['name'],'public_id':raid['public_id']} if raid else None,
 'offers':offers,'payment_gateways':payment_gateways,'payment_available':bool(payment_gateways), 'blocks':[dict(r) for r in c.execute('SELECT b.target_id,a.handle FROM community_blocks b LEFT JOIN community_accounts a ON a.user_id=b.target_id WHERE b.user_id=?',(uid,))] if uid else [], 'active_viewers':c.execute('SELECT count(*) FROM community_presence WHERE station_id=? AND seen>?',(sid,now-75)).fetchone()[0]}

def dashboard(c,s,uid):
 if not staff(c,s,uid):raise PermissionError('Channel moderator required')
 sid=s['id'];cfg=config(c,sid)
 safe_cfg=dict(cfg)
 if s['owner_id']!=uid:safe_cfg['payout_note']=''
 return {'offers':[dict(o) for o in c.execute('SELECT o.*,p.title,p.amount,p.currency FROM community_offers o JOIN market_products p ON p.id=o.product_id WHERE o.station_id=?',(sid,))] if s['owner_id']==uid else [], 'config':safe_cfg,'messages':chat(c,s,uid,moderation=True),
 'members':[dict(m) for m in c.execute('SELECT m.*,a.handle FROM community_members m LEFT JOIN community_accounts a ON a.user_id=m.user_id WHERE m.station_id=? ORDER BY m.user_id LIMIT 300',(sid,))],
 'redemptions':[dict(r) for r in c.execute('SELECT r.*,w.title FROM community_redemptions r JOIN community_rewards w ON w.id=r.reward_id WHERE w.station_id=? ORDER BY r.id DESC LIMIT 200',(sid,))],
 'stats':[dict(r) for r in c.execute('SELECT * FROM community_stats WHERE station_id=? ORDER BY day DESC LIMIT 30',(sid,))],
 'followers':c.execute('SELECT count(*) FROM community_follows WHERE station_id=?',(sid,)).fetchone()[0],
 'revenue':[dict(r) for r in c.execute("SELECT o.currency,sum(o.amount) AS gross,count(*) AS payments FROM community_payments p JOIN market_orders o ON o.id=p.order_id WHERE p.station_id=? AND p.applied=1 GROUP BY o.currency",(sid,))] if s['owner_id']==uid else [],
 'bot_keys':[dict(k) for k in c.execute('SELECT id,name,expires FROM community_bot_keys WHERE station_id=?',(sid,))] if s['owner_id']==uid else []}

def handle(c,uid,sid,method,b,q,audit,email=''):
 s=station(c,sid,uid);cfg=config(c,sid);now=int(time.time());m=member(c,sid,uid)
 if uid:c.execute('DELETE FROM community_notifications WHERE user_id=? AND id NOT IN (SELECT id FROM community_notifications WHERE user_id=? ORDER BY id DESC LIMIT 200)',(uid,uid))
 if method=='GET':
  if q.get('view',[''])[0]=='dashboard':return dashboard(c,s,uid)
  if q.get('view',[''])[0]=='chat':return {'messages':chat(c,s,uid,int(q.get('after',[0])[0]))}
  return snapshot(c,s,uid)
 if method!='POST' or not uid:raise PermissionError('Sign in required')
 action=b.get('action');owner=s['owner_id']==uid;mod=staff(c,s,uid)
 owner_actions={'customize','role','reward','video','delete_video','raid','offer','toggle_offer','bot_key','revoke_bot'}
 mod_actions={'moderate','restrictions','poll','lock_poll','resolve','redemption'}
 if action in owner_actions and not owner:raise PermissionError('Station owner required')
 if action in mod_actions and not mod:raise PermissionError('Channel moderator required')
 if action=='handle':
  handle=text(b,'handle',24,True)
  if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{2,23}',handle) or (re.fullmatch(r'viewer[0-9]+',handle,re.I) and handle.casefold()!='viewer'+str(uid)):raise ValueError('Handle needs 3–24 letters, numbers or underscores, starting with a letter')
  if c.execute('SELECT user_id FROM community_accounts WHERE lower(handle)=lower(?) AND user_id!=?',(handle,uid)).fetchone():raise ValueError('Handle already in use')
  c.execute('UPDATE community_accounts SET handle=?,avatar=? WHERE user_id=?',(handle,url(text(b,'avatar',2000)),uid))
 elif action=='follow':
  if b.get('enabled') is True:c.execute('INSERT INTO community_follows VALUES(?,?,?,?) ON CONFLICT(station_id,user_id) DO UPDATE SET notify=excluded.notify',(sid,uid,int(b.get('notify') is True),now))
  else:c.execute('DELETE FROM community_follows WHERE station_id=? AND user_id=?',(sid,uid))
 elif action=='message':return send(c,s,uid,b)
 elif action=='block':
  target=int(b.get('user_id',0))
  if target==uid or not c.execute('SELECT id FROM users WHERE id=?',(target,)).fetchone():raise ValueError('Invalid account')
  if b.get('enabled') is True:c.execute('INSERT OR IGNORE INTO community_blocks VALUES(?,?)',(uid,target))
  else:c.execute('DELETE FROM community_blocks WHERE user_id=? AND target_id=?',(uid,target))
 elif action=='report':
  if c.execute('SELECT count(*) FROM community_reports WHERE user_id=? AND created>?',(uid,now-3600)).fetchone()[0]>=10:raise ValueError('Report limit reached')
  mid=int(b.get('message_id') or 0)
  if mid and not c.execute('SELECT id FROM community_chat WHERE id=? AND station_id=?',(mid,sid)).fetchone():raise LookupError('Message unavailable')
  c.execute('INSERT INTO community_reports(user_id,station_id,message_id,reason,created) VALUES(?,?,?,?,?)',(uid,sid,mid or None,text(b,'reason',2000,True),now))
 elif action=='heartbeat':
  if not s['broadcasting'] or signal(s) not in ('live','external_stream'):return {'points':m['points'],'active':False}
  prev=c.execute('SELECT * FROM community_presence WHERE station_id=? AND user_id=?',(sid,uid)).fetchone()
  new=not prev or now-prev['seen']>75
  award=bool(prev and not new and now-prev['award']>=60)
  c.execute('INSERT INTO community_presence VALUES(?,?,?,?,?) ON CONFLICT(station_id,user_id) DO UPDATE SET seen=excluded.seen,award=excluded.award,started=excluded.started',(sid,uid,now,now if new or award else prev['award'],now if new else prev['started']))
  if award:c.execute('UPDATE community_members SET points=min(1000000000,points+10) WHERE station_id=? AND user_id=?',(sid,uid))
  viewers=c.execute('SELECT count(*) FROM community_presence WHERE station_id=? AND seen>?',(sid,now-75)).fetchone()[0]
  seconds=0 if new else max(0,min(30,now-prev['seen']))
  day=time.strftime('%Y-%m-%d',time.gmtime(now))
  c.execute('INSERT INTO community_stats VALUES(?,?,?,?,?) ON CONFLICT(station_id,day) DO UPDATE SET visits=visits+excluded.visits,watch_seconds=watch_seconds+excluded.watch_seconds,peak=max(peak,excluded.peak)',(sid,day,int(new),seconds,viewers))
  return {'points':member(c,sid,uid)['points'],'active':True}
 elif action=='customize':
  panels=b.get('panels',[]);emotes=b.get('emotes',[])
  if not isinstance(panels,list) or len(panels)>12 or not isinstance(emotes,list) or len(emotes)>24:raise ValueError('Maximum 12 panels and 24 emotes')
  clean=[]
  for panel in panels:
   clean.append({'title':text(panel,'title',80,True),'body':text(panel,'body',1000),'url':url(text(panel,'url',2000)),'sponsored':panel.get('sponsored') is True})
  icons=[]
  for e in emotes:
   code=text(e,'code',24,True)
   if not re.fullmatch(r':[A-Za-z0-9_]{2,20}:',code):raise ValueError('Emote code must look like :wave:')
   icons.append({'code':code,'url':url(text(e,'url',2000,True))})
  c.execute('UPDATE community_channels SET title=?,captions=?,tags=?,banner=?,panels=?,emotes=?,member_badge=? WHERE station_id=?',(text(b,'title',160),url(text(b,'captions',2000)),text(b,'tags',200),url(text(b,'banner',2000)),json.dumps(clean),json.dumps(icons),text(b,'member_badge',24) or 'Member',sid))
 elif action=='restrictions':
  slow=int(b.get('slow',3))
  if not 0<=slow<=120:raise ValueError('Slow mode must be 0–120 seconds')
  c.execute('UPDATE community_channels SET slow=?,followers_only=?,members_only=?,blocked_terms=? WHERE station_id=?',(slow,int(b.get('followers_only') is True),int(b.get('members_only') is True),text(b,'blocked_terms',4000),sid))
 elif action=='role':
  target=int(b.get('user_id',0));role=b.get('role')
  if role not in ('viewer','moderator') or target==s['owner_id']:raise ValueError('Invalid channel role')
  if not c.execute('SELECT id FROM users WHERE id=? AND active=1',(target,)).fetchone():raise LookupError('Account unavailable')
  member(c,sid,target);c.execute('UPDATE community_members SET role=? WHERE station_id=? AND user_id=?',(role,sid,target))
 elif action=='moderate':
  operation=b.get('operation');target=int(b.get('user_id',0));mid=int(b.get('message_id',0))
  if operation in ('ban','unban','timeout'):
   if target==s['owner_id'] or (not owner and staff(c,s,target)):raise PermissionError('Cannot restrict this channel operator')
   if not c.execute('SELECT id FROM users WHERE id=?',(target,)).fetchone():raise LookupError('Account unavailable')
   member(c,sid,target)
   if operation=='timeout':
    seconds=int(b.get('seconds',600))
    if not 1<=seconds<=604800:raise ValueError('Timeout must be 1 second to 7 days')
    c.execute('UPDATE community_members SET timeout=? WHERE station_id=? AND user_id=?',(now+seconds,sid,target))
   else:c.execute('UPDATE community_members SET banned=?,timeout=0 WHERE station_id=? AND user_id=?',(int(operation=='ban'),sid,target))
   if operation=='ban' and owner:c.execute("UPDATE community_members SET role='viewer' WHERE station_id=? AND user_id=?",(sid,target))
  elif operation in ('delete','approve','pin','unpin'):
   msg=c.execute('SELECT * FROM community_chat WHERE id=? AND station_id=?',(mid,sid)).fetchone()
   if not msg:raise LookupError('Message unavailable')
   if operation in ('pin','unpin'):
    if msg['state']!='public':raise ValueError('Approve the message first')
    if operation=='pin':c.execute('UPDATE community_chat SET pinned=0 WHERE station_id=?',(sid,))
    c.execute('UPDATE community_chat SET pinned=? WHERE id=?',(int(operation=='pin'),mid))
   else:c.execute('UPDATE community_chat SET state=?,pinned=0 WHERE id=?',('public' if operation=='approve' else 'deleted',mid))
   event(c,sid,'chat_changed',mid)
  else:raise ValueError('Invalid moderation action')
 elif action=='poll':
  options=b.get('options',[]);kind=b.get('kind','poll');duration=int(b.get('duration',300))
  if not isinstance(options,list) or not 2<=len(options)<=6 or kind not in ('poll','prediction') or not 15<=duration<=86400:raise ValueError('Use 2–6 options and duration 15 seconds to 24 hours')
  options=[str(v).strip() for v in options]
  if any(not v or len(v)>80 for v in options) or len(set(options))!=len(options):raise ValueError('Use distinct nonempty options up to 80 characters')
  if c.execute('SELECT count(*) FROM community_polls WHERE station_id=? AND ends>? AND settled=0',(sid,now)).fetchone()[0]>=5:raise ValueError('Maximum five open activities')
  pid=c.execute('INSERT INTO community_polls(station_id,title,options,kind,ends) VALUES(?,?,?,?,?)',(sid,text(b,'title',160,True),json.dumps(options),kind,now+duration)).lastrowid;event(c,sid,kind,pid)
 elif action in ('vote','lock_poll','resolve'):
  pid=int(b.get('poll_id',0));p=c.execute('SELECT * FROM community_polls WHERE id=? AND station_id=?',(pid,sid)).fetchone()
  if not p:raise LookupError('Activity unavailable')
  if p['settled']:raise ValueError('Activity already settled')
  if action=='vote':
   choice=int(b.get('choice',-1));stake=int(b.get('stake',0)) if p['kind']=='prediction' else 0
   if p['locked'] or p['ends']<=now or not 0<=choice<len(json.loads(p['options'])):raise ValueError('Voting closed or invalid choice')
   if c.execute('SELECT 1 FROM community_votes WHERE poll_id=? AND user_id=?',(pid,uid)).fetchone():raise ValueError('You already voted')
   if p['kind']=='prediction' and not 1<=stake<=1000:raise ValueError('Use 1–1000 free channel points')
   if c.execute('UPDATE community_members SET points=points-? WHERE station_id=? AND user_id=? AND points>=?',(stake,sid,uid,stake)).rowcount!=1:raise ValueError('Not enough free points')
   c.execute('INSERT INTO community_votes VALUES(?,?,?,?)',(pid,uid,choice,stake))
  elif action=='lock_poll':c.execute('UPDATE community_polls SET locked=1 WHERE id=?',(pid,))
  else:
   if p['ends']>now:raise ValueError('Wait until voting ends before resolving')
   winner=int(b.get('winner',-1))
   if winner < -1 or winner>=len(json.loads(p['options'])):raise ValueError('Invalid outcome')
   votes=c.execute('SELECT * FROM community_votes WHERE poll_id=?',(pid,)).fetchall();pool=sum(v['stake'] for v in votes);winning=sum(v['stake'] for v in votes if v['choice']==winner)
   if p['kind']=='prediction':
    for v in votes:
     payout=v['stake'] if winner==-1 or not winning else pool*v['stake']//winning if v['choice']==winner else 0
     c.execute('UPDATE community_members SET points=min(1000000000,points+?) WHERE station_id=? AND user_id=?',(payout,sid,v['user_id']))
   c.execute('UPDATE community_polls SET settled=1,locked=1,winner=? WHERE id=?',(winner,pid));event(c,sid,'activity_settled',pid)
 elif action=='reward':
  cost=int(b.get('cost',0))
  if not 1<=cost<=1000000:raise ValueError('Invalid point cost')
  if c.execute('SELECT count(*) FROM community_rewards WHERE station_id=?',(sid,)).fetchone()[0]>=50:raise ValueError('Maximum 50 rewards')
  c.execute('INSERT INTO community_rewards(station_id,title,cost) VALUES(?,?,?)',(sid,text(b,'title',120,True),cost))
 elif action=='redeem':
  r=c.execute('SELECT * FROM community_rewards WHERE id=? AND station_id=? AND enabled=1',(int(b.get('reward_id',0)),sid)).fetchone()
  if not r:raise LookupError('Reward unavailable')
  if c.execute('UPDATE community_members SET points=points-? WHERE station_id=? AND user_id=? AND points>=?',(r['cost'],sid,uid,r['cost'])).rowcount!=1:raise ValueError('Not enough free points')
  c.execute('INSERT INTO community_redemptions(reward_id,user_id,cost,created) VALUES(?,?,?,?)',(r['id'],uid,r['cost'],now))
 elif action=='redemption':
  r=c.execute('SELECT r.* FROM community_redemptions r JOIN community_rewards w ON w.id=r.reward_id WHERE r.id=? AND w.station_id=?',(int(b.get('redemption_id',0)),sid)).fetchone();status=b.get('status')
  if not r or r['status']!='pending' or status not in ('fulfilled','refunded'):raise ValueError('Invalid redemption update')
  if status=='refunded':c.execute('UPDATE community_members SET points=points+? WHERE station_id=? AND user_id=?',(r['cost'],sid,r['user_id']))
  c.execute('UPDATE community_redemptions SET status=? WHERE id=?',(status,r['id']))
 elif action=='video':
  kind=b.get('kind');start=float(b.get('start',0));end=float(b.get('end',0))
  if kind not in ('past','highlight','clip','featured') or not 0<=start<=86400 or not 0<=end<=86400 or (end and end<=start):raise ValueError('Invalid media type or clip range')
  if c.execute('SELECT count(*) FROM community_videos WHERE station_id=?',(sid,)).fetchone()[0]>=200:raise ValueError('Maximum 200 library entries')
  captions=url(text(b,'captions',2000))
  c.execute('INSERT INTO community_videos(station_id,title,kind,url,thumbnail,captions,start,end,created) VALUES(?,?,?,?,?,?,?,?,?)',(sid,text(b,'title',200,True),kind,url(text(b,'url',2000,True)),url(text(b,'thumbnail',2000)),captions,start,end,now))
 elif action=='delete_video':c.execute('DELETE FROM community_videos WHERE station_id=? AND id=?',(sid,int(b.get('video_id',0))))
 elif action=='raid':
  target=active(c,int(b.get('target_id',0)))
  if not target or not target['approved'] or target['id']==sid:raise ValueError('Choose another approved station')
  c.execute('UPDATE community_channels SET raid_id=?,raid_until=? WHERE station_id=?',(target['id'],now+600,sid));event(c,sid,'raid',target['id'])
 elif action=='bot_key':
  if c.execute('SELECT count(*) FROM community_bot_keys WHERE station_id=?',(sid,)).fetchone()[0]>=5:raise ValueError('Maximum five bot keys; revoke old keys first')
  key=secrets.token_urlsafe(32);expires=now+30*86400
  c.execute('INSERT INTO community_bot_keys(station_id,token_hash,name,expires) VALUES(?,?,?,?)',(sid,hashlib.sha256(key.encode()).hexdigest(),text(b,'name',60,True),expires))
  audit(c,uid,'Issued scoped community bot key for station '+str(sid));return {'token':key,'expires':expires}
 elif action=='revoke_bot':c.execute('DELETE FROM community_bot_keys WHERE station_id=? AND id=?',(sid,int(b.get('key_id',0))))
 elif action=='offer':
  from commerce import CURRENCIES
  kind=b.get('kind');amount=int(b.get('amount',0));currency=str(b.get('currency','USD')).upper()
  if kind not in ('membership','cheer') or not 100<=amount<=100000 or currency not in CURRENCIES:raise ValueError('Use membership or cheer, supported currency, and 100–100000 minor units')
  if c.execute('SELECT count(*) FROM community_offers WHERE station_id=?',(sid,)).fetchone()[0]>=10:raise ValueError('Maximum ten offers')
  title=text(b,'title',120,True);product=c.execute("INSERT INTO market_products(title,description,amount,currency,kind,fulfillment,active) VALUES(?,?,?,?,'digital','Channel benefit activated after verified payment',0)",(s['name']+' · '+title,'30-day nonrenewing channel membership' if kind=='membership' else 'One-time channel support payment',amount,currency)).lastrowid
  c.execute('INSERT INTO community_offers(station_id,product_id,kind) VALUES(?,?,?)',(sid,product,kind))
 elif action=='toggle_offer':
  c.execute('UPDATE community_offers SET active=? WHERE id=? AND station_id=?',(int(b.get('enabled') is True),int(b.get('offer_id',0)),sid))
 elif action=='checkout':return checkout(c,s,uid,email,b)
 elif action=='verify':
  from commerce import verify
  reference=text(b,'order_id',100,True)
  if not c.execute('SELECT p.order_id FROM community_payments p JOIN market_orders o ON o.id=p.order_id WHERE p.order_id=? AND p.station_id=? AND o.user_id=?',(reference,sid,uid)).fetchone():raise LookupError('Channel payment unavailable')
  result=verify(c,uid,reference,audit);apply_paid(c,reference);return result
 else:raise ValueError('Unknown community action')
 if action in owner_actions or action in mod_actions:audit(c,uid,'Station community '+str(sid)+': '+str(action))
 return {'ok':True}

def checkout(c,s,uid,email,b):
 from commerce import checkout as purchase,gateways
 cfg=config(c,s['id']);gateway=b.get('gateway')
 if not cfg['monetized'] or not any(g['id']==gateway and g['enabled'] and g['configured'] and g['mode']=='live' for g in gateways(c)):raise ValueError('Channel payments require administrator eligibility and an enabled live gateway')
 o=c.execute('SELECT * FROM community_offers WHERE id=? AND station_id=? AND active=1',(int(b.get('offer_id',0)),s['id'])).fetchone()
 if not o:raise LookupError('Offer unavailable')
 beneficiary=uid;gift=text(b,'gift_handle',24)
 if gift:
  if o['kind']!='membership':raise ValueError('Only memberships can be gifted')
  a=c.execute('SELECT a.user_id FROM community_accounts a JOIN users u ON u.id=a.user_id WHERE lower(a.handle)=lower(?) AND u.active=1',(gift,)).fetchone()
  if not a:raise ValueError('Recipient must have an existing community handle')
  beneficiary=a[0]
 request_key=text(b,'request_key',80,True)
 old=c.execute('SELECT p.* FROM community_payments p JOIN market_orders m ON m.id=p.order_id WHERE m.user_id=? AND m.request_key=?',(uid,request_key)).fetchone()
 if old and (old['beneficiary']!=beneficiary or old['station_id']!=s['id']):raise ValueError('Checkout key belongs to another purchase')
 def bind(reference):c.execute('INSERT INTO community_payments VALUES(?,?,?,?,0)',(reference,s['id'],beneficiary,o['kind']))
 return purchase(c,uid,email,{'gateway':gateway,'request_key':request_key,'product_id':o['product_id']},allow_unlisted=True,on_order_created=bind)

def apply_paid(c,reference):
 p=c.execute("SELECT p.*,o.status FROM community_payments p JOIN market_orders o ON o.id=p.order_id WHERE p.order_id=?",(reference,)).fetchone()
 if not p or p['applied'] or p['status']!='paid':return
 if c.execute('UPDATE community_payments SET applied=1 WHERE order_id=? AND applied=0',(reference,)).rowcount!=1:return
 member(c,p['station_id'],p['beneficiary']);now=int(time.time())
 if p['kind']=='membership':c.execute('UPDATE community_members SET member_until=max(member_until,?)+2592000 WHERE station_id=? AND user_id=?',(now,p['station_id'],p['beneficiary']))
 else:c.execute('INSERT INTO community_chat(station_id,user_id,body,created) VALUES(?,NULL,?,?)',(p['station_id'],'A viewer sent verified channel support. Thank you!',now))
 c.execute('INSERT INTO community_notifications(user_id,station_id,body,created) VALUES(?,?,?,?)',(p['beneficiary'],p['station_id'],'Channel '+('membership activated for 30 days.' if p['kind']=='membership' else 'support payment verified.'),now))
 event(c,p['station_id'],'payment_verified')

def bot(c,token,method,b,q):
 now=int(time.time())
 if not 32<=len(token)<=128:raise PermissionError('Invalid bot key')
 key=c.execute('SELECT * FROM community_bot_keys WHERE token_hash=? AND expires>?',(hashlib.sha256(token.encode()).hexdigest(),now)).fetchone()
 if not key:raise PermissionError('Invalid or expired bot key')
 calls=key['calls']+1 if key['window']==now//60 else 1
 if calls>30:raise PermissionError('Bot rate limit reached')
 c.execute('UPDATE community_bot_keys SET window=?,calls=? WHERE id=?',(now//60,calls,key['id']))
 s=station(c,key['station_id'],None)
 if method=='GET':
  return {'messages':chat(c,s,None,int(q.get('after',[0])[0])),'events':[dict(e) for e in c.execute('SELECT id,kind,object_id,created FROM community_events WHERE station_id=? AND id>? ORDER BY id LIMIT 100',(s['id'],int(q.get('event_after',[0])[0])))]}
 if method=='POST' and b.get('action')=='message':return send(c,s,s['owner_id'],b,True)
 raise PermissionError('Bot keys can only read public events/chat and post messages')

def admin(c,uid,method,b,audit):
 if method=='GET':return {'reports':[dict(r) for r in c.execute('SELECT * FROM community_reports ORDER BY id DESC LIMIT 300')],'eligibility':[dict(r) for r in c.execute('SELECT s.id,s.name,cc.monetized,cc.payout_note FROM stations s LEFT JOIN community_channels cc ON cc.station_id=s.id')]}
 sid=int(b.get('station_id',0))
 if b.get('action')=='monetization':
  if not active(c,sid):raise LookupError('Station unavailable')
  note=text(b,'payout_note',1000);enabled=b.get('enabled') is True
  if enabled and len(note)<20:raise ValueError('Document the operator-managed creator payout arrangement first')
  config(c,sid);c.execute('UPDATE community_channels SET monetized=?,payout_note=? WHERE station_id=?',(int(enabled),note,sid))
 elif b.get('action')=='resolve_report':c.execute("UPDATE community_reports SET status='resolved' WHERE id=?",(int(b.get('report_id',0)),))
 elif b.get('action')=='revoke_membership':c.execute('UPDATE community_members SET member_until=0 WHERE station_id=? AND user_id=?',(sid,int(b.get('user_id',0))))
 else:raise ValueError('Unknown community administration action')
 audit(c,uid,'Community administrator: '+str(b.get('action')));return {'ok':True}
