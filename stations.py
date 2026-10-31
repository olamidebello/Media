"""User-owned broadcast stations, rundown/EPG and authenticated RTMPS publishing."""
import hashlib
import hmac
import json
import re
import secrets
import time
from pathlib import Path
from urllib.parse import urlparse

ENGINE = Path('/etc/africa-media-station/engine.json')
HLS = Path('/var/lib/africa-media-station/hls')

def init(c):
    c.executescript('''
    CREATE TABLE IF NOT EXISTS stations(
      id INTEGER PRIMARY KEY, owner_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      public_id TEXT UNIQUE NOT NULL, name TEXT NOT NULL, description TEXT NOT NULL DEFAULT '',
      category TEXT NOT NULL DEFAULT 'Entertainment', logo TEXT NOT NULL DEFAULT '',
      source TEXT NOT NULL DEFAULT 'encoder', external_url TEXT NOT NULL DEFAULT '',
      approved INTEGER NOT NULL DEFAULT 0, suspended INTEGER NOT NULL DEFAULT 0,
      broadcasting INTEGER NOT NULL DEFAULT 0, key_hash TEXT NOT NULL DEFAULT '',
      lower_third TEXT NOT NULL DEFAULT '', ticker TEXT NOT NULL DEFAULT '',
      overlay_enabled INTEGER NOT NULL DEFAULT 1, created INTEGER NOT NULL);
    CREATE TABLE IF NOT EXISTS station_programs(
      id INTEGER PRIMARY KEY, station_id INTEGER NOT NULL REFERENCES stations(id) ON DELETE CASCADE,
      title TEXT NOT NULL, description TEXT NOT NULL DEFAULT '', start INTEGER NOT NULL,
      end INTEGER NOT NULL, kind TEXT NOT NULL, media_url TEXT NOT NULL DEFAULT '',
      notes TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'planned');
    ''')

def engine():
    try:
        data = json.loads(ENGINE.read_text())
        if not re.fullmatch(r'rtmps://[a-z0-9.-]+:1936/live', data['publish_url']): return None
        return data
    except (OSError, ValueError, KeyError, TypeError): return None

def text(body, key, maximum, required=False):
    value = str(body.get(key, '')).strip()
    if len(value) > maximum or (required and not value): raise ValueError('Invalid '+key.replace('_',' '))
    return value

def url(value, suffix=False):
    if not value: return ''
    p = urlparse(value)
    if p.scheme != 'https' or not p.hostname or p.username or p.password or len(value)>2000:
        raise ValueError('Use an HTTPS URL without credentials')
    if suffix and not p.path.lower().endswith('.m3u8'): raise ValueError('Use an HTTPS HLS .m3u8 stream')
    return value

def active(c, station_id):
    return c.execute('''SELECT s.*,u.active FROM stations s JOIN users u ON u.id=s.owner_id
        WHERE s.id=? AND u.active=1 AND s.suspended=0''',(station_id,)).fetchone()

def signal(s):
    if not s['broadcasting']: return 'off_air'
    if s['source']=='external': return 'external_stream' # Not a verified upstream health claim.
    try:
        age=time.time()-(HLS/('station-'+str(s['id']))/'index.m3u8').stat().st_mtime
        return 'live' if age<20 else 'waiting_for_encoder'
    except OSError: return 'waiting_for_encoder'

def public_data(c,s,owner=False):
    keys=['id','public_id','name','description','category','logo','source','approved','suspended','broadcasting','lower_third','ticker','overlay_enabled']
    out={k:s[k] for k in keys}
    out['signal']=signal(s)
    out['playback_url'] = s['external_url'] if s['source']=='external' else '/station-hls/station-'+str(s['id'])+'/index.m3u8'
    out['programs']=[dict(p) for p in c.execute('SELECT id,title,description,start,end,kind,status FROM station_programs WHERE station_id=? AND end>? ORDER BY start LIMIT 500',(s['id'],int(time.time())-86400))]
    if owner:
        out['external_url']=s['external_url']
        out['programs']=[dict(p) for p in c.execute('SELECT * FROM station_programs WHERE station_id=? ORDER BY start LIMIT 500',(s['id'],))]
    return out

def can_preview(c,s,user):
    return s['owner_id']==user or bool(c.execute("SELECT id FROM users WHERE id=? AND active=1 AND role IN ('admin','superadmin')",(user,)).fetchone())

def public(c,public_id,user=None):
    s=c.execute('SELECT * FROM stations WHERE public_id=?',(public_id,)).fetchone()
    if not s or not active(c,s['id']): raise LookupError('Station unavailable')
    if not can_preview(c,s,user) and not s['approved']: raise LookupError('Station is off air or awaiting review')
    return public_data(c,s)

def authorize(c,body):
    name=body.get('name',[''])[0]; key=body.get('key',[''])[0]
    if not re.fullmatch(r'station-[1-9][0-9]*',name): raise PermissionError('Invalid stream')
    s=active(c,int(name[8:]))
    if not s or s['source']!='encoder' or not s['broadcasting'] or not s['key_hash'] or not hmac.compare_digest(s['key_hash'],hashlib.sha256(key.encode()).hexdigest()):
        raise PermissionError('Publishing disabled or invalid key')
    return {'ok':True}

def access(c,name,user):
    match=re.fullmatch(r'/station-hls/station-([1-9][0-9]*)/(?:index\.m3u8|[0-9]+\.ts)',name)
    if not match: raise PermissionError('Invalid stream path')
    s=active(c,int(match[1]))
    if not s or not s['broadcasting'] or s['source']!='encoder' or (not s['approved'] and not can_preview(c,s,user)):
        raise PermissionError('Station unavailable')
    return {'ok':True}

def handle(c,user,path,method,b,q,audit):
    if path=='/api/stations' and method=='GET':
        return {'stations':[public_data(c,s,True) for s in c.execute('SELECT * FROM stations WHERE owner_id=? ORDER BY id DESC',(user,))], 'engine':engine()}
    if path!='/api/stations' or method!='POST': raise ValueError('Unsupported station request')
    action=b.get('action')
    if action=='create':
        if c.execute('SELECT count(*) FROM stations WHERE owner_id=?',(user,)).fetchone()[0]>=5: raise ValueError('Maximum five stations per account')
        cursor=c.execute('INSERT INTO stations(owner_id,public_id,name,created) VALUES(?,?,?,?)',(user,secrets.token_hex(16),text(b,'name',100,True),int(time.time())))
        audit(c,user,'Created station '+str(cursor.lastrowid))
        return {'id':cursor.lastrowid}
    sid=int(b.get('id',0))
    s=c.execute('SELECT * FROM stations WHERE id=? AND owner_id=?',(sid,user)).fetchone()
    if not s: raise LookupError('Station unavailable')
    if action=='save':
        source=b.get('source','encoder')
        if source not in ('encoder','external'): raise ValueError('Invalid source')
        ext=url(text(b,'external_url',2000),True)
        if source=='external' and not ext: raise ValueError('External HLS URL required')
        # Changing the public identity/source requires a fresh moderation review.
        values=(text(b,'name',100,True),text(b,'description',2000),text(b,'category',60,True),url(text(b,'logo',2000)),source,ext)
        changed=values!=tuple(s[k] for k in ('name','description','category','logo','source','external_url'))
        c.execute('''UPDATE stations SET name=?,description=?,category=?,logo=?,source=?,external_url=?,
            approved=CASE WHEN ? THEN 0 ELSE approved END,broadcasting=CASE WHEN ? THEN 0 ELSE broadcasting END WHERE id=?''',(*values,changed,changed,sid))
    elif action=='graphics':
        c.execute('UPDATE stations SET lower_third=?,ticker=?,overlay_enabled=? WHERE id=?',(text(b,'lower_third',160),text(b,'ticker',500),int(b.get('overlay_enabled') is True),sid))
    elif action=='rotate_key':
        key=secrets.token_urlsafe(32)
        c.execute('UPDATE stations SET key_hash=?,broadcasting=0 WHERE id=?',(hashlib.sha256(key.encode()).hexdigest(),sid))
        audit(c,user,'Rotated station stream key '+str(sid))
        return {'stream_key':'station-'+str(sid)+'?key='+key,'message':'Save this key in OBS. It will only be shown once. Output is now off air.'}
    elif action in ('start','stop'):
        if action=='start':
            if s['suspended']: raise PermissionError('Station suspended by an administrator')
            if s['source']=='encoder' and (not engine() or not s['key_hash']): raise ValueError('Install station streaming service and generate an encoder key first')
            if s['source']=='external' and not s['external_url']: raise ValueError('Configure external HLS first')
        c.execute('UPDATE stations SET broadcasting=? WHERE id=?',(int(action=='start'),sid))
        if action=='start':
            from community import notify_start
            notify_start(c,sid)
    elif action=='delete':
        c.execute('DELETE FROM stations WHERE id=?',(sid,))
    elif action=='program':
        title=text(b,'title',200,True); start=int(b.get('start',0)); end=int(b.get('end',0)); kind=b.get('kind')
        if end<=start or end-start>86400 or start<0 or end>4102444800: raise ValueError('Program must last between one second and 24 hours')
        if kind not in ('live','prerecorded','break'): raise ValueError('Invalid program type')
        pid=int(b.get('program_id',0))
        if pid and not c.execute('SELECT id FROM station_programs WHERE id=? AND station_id=?',(pid,sid)).fetchone(): raise LookupError('Program unavailable')
        if c.execute('SELECT id FROM station_programs WHERE station_id=? AND id!=? AND start<? AND end>?',(sid,pid,end,start)).fetchone(): raise ValueError('Program overlaps another schedule entry')
        if not pid and c.execute('SELECT count(*) FROM station_programs WHERE station_id=?',(sid,)).fetchone()[0]>=500: raise ValueError('Maximum 500 schedule entries. Remove past programs to continue.')
        fields=(title,text(b,'description',2000),start,end,kind,url(text(b,'media_url',2000)),text(b,'notes',2000))
        if pid: c.execute('UPDATE station_programs SET title=?,description=?,start=?,end=?,kind=?,media_url=?,notes=? WHERE id=? AND station_id=?',(*fields,pid,sid))
        else: c.execute('INSERT INTO station_programs(title,description,start,end,kind,media_url,notes,station_id) VALUES(?,?,?,?,?,?,?,?)',(*fields,sid))
    elif action in ('program_status','remove_program'):
        pid=int(b.get('program_id',0))
        if not c.execute('SELECT id FROM station_programs WHERE id=? AND station_id=?',(pid,sid)).fetchone(): raise LookupError('Program unavailable')
        if action=='remove_program': c.execute('DELETE FROM station_programs WHERE id=? AND station_id=?',(pid,sid))
        else:
            state=b.get('status')
            if state not in ('planned','ready','done','skipped'): raise ValueError('Invalid rundown state')
            c.execute('UPDATE station_programs SET status=? WHERE id=? AND station_id=?',(state,pid,sid))
    else: raise ValueError('Unknown station action')
    audit(c,user,'Station '+str(sid)+': '+str(action))
    return {'ok':True}

def moderate(c,user,method,b,audit):
    if method=='GET': return [dict(s) for s in c.execute('SELECT s.id,s.public_id,s.name,s.description,s.logo,s.source,s.external_url,s.approved,s.suspended,s.broadcasting,u.email FROM stations s JOIN users u ON u.id=s.owner_id ORDER BY s.id DESC LIMIT 500')]
    if method!='POST' or b.get('action') not in ('approve','suspend','restore'): raise ValueError('Invalid moderation action')
    sid=int(b.get('id',0))
    if not c.execute('SELECT id FROM stations WHERE id=?',(sid,)).fetchone(): raise LookupError('Station unavailable')
    if b['action']=='approve': c.execute('UPDATE stations SET approved=1 WHERE id=?',(sid,))
    elif b['action']=='suspend': c.execute('UPDATE stations SET suspended=1,broadcasting=0,approved=0 WHERE id=?',(sid,))
    else: c.execute('UPDATE stations SET suspended=0 WHERE id=?',(sid,))
    audit(c,user,'Station moderation '+str(sid)+': '+b['action'])
    return {'ok':True}
