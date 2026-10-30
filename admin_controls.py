"""Administrator operations; called only after authentication and CSRF checks."""
import re
import time

def manage(c, actor, method, b, password, valid_url, audit):
    if method == 'GET':
        def all(sql): return [dict(r) for r in c.execute(sql)]
        return {'users': all('SELECT id,email,role,active FROM users ORDER BY id DESC'),
                'channels': all('SELECT * FROM channels'), 'programs': all('SELECT * FROM programs ORDER BY start DESC LIMIT 500'),
                'comments': all('SELECT id,user_id,video_id,body,created FROM comments ORDER BY id DESC LIMIT 200'),
                'settings': dict(c.execute('SELECT key,value FROM settings')),
                'metrics': {t: c.execute('SELECT count(*) FROM '+t).fetchone()[0] for t in ('users','videos','channels','reports','recording_requests')},
                'sessions': c.execute('SELECT count(*) FROM sessions WHERE expires>?',(int(time.time()),)).fetchone()[0],
                'audit': all('SELECT * FROM audit ORDER BY id DESC LIMIT 500')}
    if method != 'POST': raise ValueError('Unsupported method')
    action=b.get('action'); target=int(b.get('id') or 0)
    if action in ('create_user','edit_user','reset_password','revoke_sessions'):
        if action != 'create_user':
            old=c.execute('SELECT * FROM users WHERE id=?',(target,)).fetchone()
            if not old: raise LookupError('User not found')
            from roles import protect
            protect(c,actor,[target])
        if action in ('create_user','edit_user'):
            email=str(b.get('email','')).strip().lower()
            role=b.get('role','viewer'); active=int(bool(b.get('active',True)))
            if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email): raise ValueError('Valid email required')
            from roles import validate_role
            validate_role(c,actor,role)
            if target==actor and (not active or role not in ('admin','superadmin')): raise ValueError('Cannot remove your own admin access')
            if action=='create_user':
                pw=str(b.get('password',''))
                if len(pw)<12: raise ValueError('Password must have at least 12 characters')
                target=c.execute('INSERT INTO users(email,password,role,active) VALUES(?,?,?,?)',(email,password(pw),role,active)).lastrowid
                c.execute('INSERT INTO profiles(user_id,name) VALUES(?,?)',(target,'My profile'))
            else:
                c.execute('UPDATE users SET email=?,role=?,active=? WHERE id=?',(email,role,active,target))
                c.execute('DELETE FROM sessions WHERE user_id=?',(target,))
        elif action=='reset_password':
            pw=str(b.get('password',''))
            if len(pw)<12: raise ValueError('Password must have at least 12 characters')
            c.execute('UPDATE users SET password=? WHERE id=?',(password(pw),target))
            c.execute('DELETE FROM sessions WHERE user_id=?',(target,))
        else: c.execute('DELETE FROM sessions WHERE user_id=?',(target,))
    elif action=='edit_channel':
        name=str(b.get('name','')).strip()[:100]
        if not name: raise ValueError('Channel name required')
        if not c.execute('SELECT id FROM channels WHERE id=?',(target,)).fetchone(): raise LookupError('Channel not found')
        c.execute('UPDATE channels SET name=?,url=?,category=?,enabled=? WHERE id=?',(name,valid_url(str(b.get('url',''))),str(b.get('category',''))[:80],int(bool(b.get('enabled'))),target))
    elif action in ('delete_channel','delete_program','delete_comment'):
        table={'delete_channel':'channels','delete_program':'programs','delete_comment':'comments'}[action]
        if not c.execute('DELETE FROM '+table+' WHERE id=?',(target,)).rowcount: raise LookupError('Record not found')
    elif action=='settings':
        for key in ('registration','announcement'):
            value=str(b.get(key,''))[:1000]
            if key=='registration' and value not in ('on','off'): raise ValueError('Invalid registration setting')
            c.execute('INSERT OR REPLACE INTO settings VALUES(?,?)',(key,value))
    else: raise ValueError('Unknown management action')
    audit(c,actor,'management '+str(action)+' target='+str(target))
    return {'ok':True}
