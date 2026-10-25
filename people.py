"""Audited account groups and bulk account controls. Groups do not grant roles."""
import time

def init(c):
 c.executescript('''CREATE TABLE IF NOT EXISTS user_groups(id INTEGER PRIMARY KEY,name TEXT UNIQUE NOT NULL,description TEXT NOT NULL DEFAULT '');
 CREATE TABLE IF NOT EXISTS user_group_members(group_id INTEGER REFERENCES user_groups(id) ON DELETE CASCADE,user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,PRIMARY KEY(group_id,user_id));''')

def manage(c,actor,method,b,audit):
 if method=='GET':
  return {key:[dict(r) for r in c.execute(sql)] for key,sql in {'users':'SELECT id,email,role,active FROM users ORDER BY id DESC','groups':'SELECT * FROM user_groups ORDER BY name','members':'SELECT * FROM user_group_members','profiles':'SELECT id,user_id,name,kids FROM profiles ORDER BY id'}.items()}
 action=b.get('action');target=int(b.get('id') or 0)
 if action in ('create_group','edit_group'):
  name=str(b.get('name','')).strip()[:80]
  if not name:raise ValueError('Group name required')
  description=str(b.get('description',''))[:500]
  if action=='create_group':target=c.execute('INSERT INTO user_groups(name,description) VALUES(?,?)',(name,description)).lastrowid
  elif not c.execute('UPDATE user_groups SET name=?,description=? WHERE id=?',(name,description,target)).rowcount:raise LookupError('Group not found')
 elif action=='delete_group':c.execute('DELETE FROM user_groups WHERE id=?',(target,))
 elif action in ('group_add','group_remove','bulk_active','bulk_role','bulk_revoke'):
  ids=b.get('ids',[])
  if not isinstance(ids,list) or not 1<=len(ids)<=500:raise ValueError('Select 1 to 500 accounts')
  ids=sorted({int(x) for x in ids});marks=','.join('?' for _ in ids)
  if c.execute('SELECT count(*) FROM users WHERE id IN ('+marks+')',ids).fetchone()[0]!=len(ids):raise LookupError('Account not found')
  if action.startswith('group_'):
   if not c.execute('SELECT 1 FROM user_groups WHERE id=?',(target,)).fetchone():raise LookupError('Group not found')
   for uid in ids:
    if action=='group_add':c.execute('INSERT OR IGNORE INTO user_group_members VALUES(?,?)',(target,uid))
    else:c.execute('DELETE FROM user_group_members WHERE group_id=? AND user_id=?',(target,uid))
  else:
   if action=='bulk_role':
    role=b.get('role')
    if role not in ('viewer','creator','admin'):raise ValueError('Invalid role')
    if actor in ids and role!='admin':raise ValueError('Cannot remove your own administrator role')
    c.execute('UPDATE users SET role=? WHERE id IN ('+marks+')',[role]+ids)
   elif action=='bulk_active':
    active=b.get('active')
    if not isinstance(active,bool):raise ValueError('Select active or suspended')
    if actor in ids and not active:raise ValueError('Cannot suspend yourself')
    c.execute('UPDATE users SET active=? WHERE id IN ('+marks+')',[int(active)]+ids)
   c.execute('DELETE FROM sessions WHERE user_id IN ('+marks+')',ids)
  audit(c,actor,'people '+action+' ids='+','.join(map(str,ids))+' group='+str(target));return {'ok':True}
 elif action=='edit_profile':
  name=str(b.get('name','')).strip()[:50]
  if not name:raise ValueError('Profile name required')
  if not c.execute('UPDATE profiles SET name=?,kids=? WHERE id=?',(name,int(bool(b.get('kids'))),target)).rowcount:raise LookupError('Profile not found')
 else:raise ValueError('Unknown account action')
 audit(c,actor,'people '+action+' target='+str(target));return {'ok':True}
