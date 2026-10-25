"""Additional privileged controls, behind existing admin and CSRF checks."""
import time
from iptv import parse
FEATURES=('live_tv','catalog','creator_submissions','comments','downloads','provider_links','registration')
def enabled(c,key):
 row=c.execute('SELECT value FROM settings WHERE key=?',(key,)).fetchone()
 return not row or row[0]!='off'
def operate(c,actor,b,valid_url,audit):
 action=b.get('action');target=int(b.get('id') or 0)
 if action=='features':
  for key in FEATURES:
   if key in b:
    if b[key] not in ('on','off'):raise ValueError('Invalid switch')
    c.execute('INSERT OR REPLACE INTO settings VALUES(?,?)',(key,b[key]))
 elif action=='delete_user':
  if target==actor:raise ValueError('Cannot delete your own administrator account')
  if not c.execute('SELECT id FROM users WHERE id=?',(target,)).fetchone():raise LookupError('Account not found')
  c.execute('UPDATE videos SET owner_id=NULL WHERE owner_id=?',(target,))
  c.execute('UPDATE reports SET user_id=NULL WHERE user_id=?',(target,))
  c.execute('UPDATE audit SET user_id=NULL WHERE user_id=?',(target,))
  c.execute('DELETE FROM users WHERE id=?',(target,))
 elif action in ('create_content','edit_content'):
  title=str(b.get('title','')).strip()[:200];kind=b.get('kind','video');visibility=b.get('visibility','draft')
  if not title or kind not in ('video','movie','tv','short','podcast','live') or visibility not in ('draft','public'):raise ValueError('Invalid title, format or visibility')
  fields=(title,str(b.get('description',''))[:5000],kind,str(b.get('category','General'))[:80],valid_url(str(b.get('url',''))),visibility,int(bool(b.get('kids'))))
  if action=='create_content':c.execute('INSERT INTO videos(title,description,kind,category,url,visibility,kids,owner_id,created) VALUES(?,?,?,?,?,?,?,?,?)',fields+(actor,int(time.time())))
  elif not c.execute('UPDATE videos SET title=?,description=?,kind=?,category=?,url=?,visibility=?,kids=? WHERE id=?',fields+(target,)).rowcount:raise LookupError('Content not found')
 elif action=='bulk_channels':
  text=str(b.get('playlist',''))
  if not text.lstrip().startswith('#EXTM3U'):raise ValueError('Paste an M3U playlist beginning #EXTM3U')
  items,skipped=parse(text);added=0
  for item in items:
   if c.execute('SELECT id FROM channels WHERE url=?',(item['url'],)).fetchone():continue
   c.execute('INSERT INTO channels(name,url,category) VALUES(?,?,?)',(item['name'],item['url'],item['category']));added+=1
  audit(c,actor,'bulk channel import added='+str(added));return {'ok':True,'added':added,'skipped':skipped}
 elif action=='channel_state':
  ids=b.get('ids',[])
  if not isinstance(ids,list) or len(ids)>1000:raise ValueError('Select up to 1000 channels')
  for value in ids:c.execute('UPDATE channels SET enabled=? WHERE id=?',(int(bool(b.get('enabled'))),int(value)))
 elif action=='legal_resolve':
  c.execute('INSERT OR REPLACE INTO settings VALUES(?,?)',('legal_resolved_'+str(target),'yes'))
 else:raise ValueError('Unknown console action')
 audit(c,actor,'console '+str(action)+' target='+str(target));return {'ok':True}
