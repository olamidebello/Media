"""Africa Media Hub: dependency-free WSGI application."""
import os, sqlite3, json, secrets, hashlib, hmac, time, re
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from http.cookies import SimpleCookie
from wsgiref.simple_server import make_server

ROOT = Path(__file__).parent
DB = os.environ.get('MEDIA_DB', str(ROOT / 'media.db'))
SECURE = os.environ.get('MEDIA_SECURE_COOKIE', '1') == '1'

def db():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    c.execute('PRAGMA foreign_keys=ON')
    return c

def init():
    Path(DB).parent.mkdir(parents=True, exist_ok=True)
    with db() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,email TEXT UNIQUE NOT NULL,password TEXT NOT NULL,role TEXT DEFAULT 'viewer',active INTEGER DEFAULT 1);
        CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,csrf TEXT,expires INTEGER);
        CREATE TABLE IF NOT EXISTS profiles(id INTEGER PRIMARY KEY,user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,name TEXT,kids INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS videos(id INTEGER PRIMARY KEY,owner_id INTEGER REFERENCES users(id),title TEXT,description TEXT,kind TEXT,category TEXT,url TEXT,visibility TEXT DEFAULT 'draft',kids INTEGER DEFAULT 0,created INTEGER);
        CREATE TABLE IF NOT EXISTS channels(id INTEGER PRIMARY KEY,name TEXT,url TEXT,category TEXT,enabled INTEGER DEFAULT 1);
        CREATE TABLE IF NOT EXISTS programs(id INTEGER PRIMARY KEY,channel_id INTEGER REFERENCES channels(id) ON DELETE CASCADE,title TEXT,start INTEGER,end INTEGER,recordable INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS saved(profile_id INTEGER REFERENCES profiles(id) ON DELETE CASCADE,video_id INTEGER REFERENCES videos(id) ON DELETE CASCADE,PRIMARY KEY(profile_id,video_id));
        CREATE TABLE IF NOT EXISTS history(profile_id INTEGER REFERENCES profiles(id) ON DELETE CASCADE,video_id INTEGER REFERENCES videos(id) ON DELETE CASCADE,position REAL,updated INTEGER,PRIMARY KEY(profile_id,video_id));
        CREATE TABLE IF NOT EXISTS reactions(profile_id INTEGER REFERENCES profiles(id) ON DELETE CASCADE,video_id INTEGER REFERENCES videos(id) ON DELETE CASCADE,value INTEGER,PRIMARY KEY(profile_id,video_id));
        CREATE TABLE IF NOT EXISTS comments(id INTEGER PRIMARY KEY,user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,video_id INTEGER REFERENCES videos(id) ON DELETE CASCADE,body TEXT,created INTEGER);
        CREATE TABLE IF NOT EXISTS playlists(id INTEGER PRIMARY KEY,profile_id INTEGER REFERENCES profiles(id) ON DELETE CASCADE,name TEXT);
        CREATE TABLE IF NOT EXISTS playlist_items(playlist_id INTEGER REFERENCES playlists(id) ON DELETE CASCADE,video_id INTEGER REFERENCES videos(id) ON DELETE CASCADE,PRIMARY KEY(playlist_id,video_id));
        CREATE TABLE IF NOT EXISTS reports(id INTEGER PRIMARY KEY,user_id INTEGER REFERENCES users(id),video_id INTEGER REFERENCES videos(id),reason TEXT,status TEXT DEFAULT 'open');
        CREATE TABLE IF NOT EXISTS recording_requests(id INTEGER PRIMARY KEY,profile_id INTEGER REFERENCES profiles(id) ON DELETE CASCADE,program_id INTEGER REFERENCES programs(id) ON DELETE CASCADE,status TEXT DEFAULT 'awaiting_recorder',UNIQUE(profile_id,program_id));
        CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY,user_id INTEGER,action TEXT,created INTEGER);
        ''')

def password(p, salt=None):
    salt = salt or secrets.token_hex(16)
    return salt + ':' + hashlib.scrypt(p.encode(), salt=salt.encode(), n=16384, r=8, p=1).hex()

def rows(c, sql, args=()): return [dict(r) for r in c.execute(sql, args)]
def audit(c,u,action): c.execute('INSERT INTO audit(user_id,action,created) VALUES(?,?,?)',(u,action,int(time.time())))
def valid_url(s):
    p = urlparse(s)
    if p.scheme != 'https' or not p.hostname or p.username or p.password: raise ValueError('Use a public HTTPS media URL')
    return s

def app(env, respond):
    status = '200 OK'; headers = [('Content-Type','application/json; charset=utf-8'),('X-Content-Type-Options','nosniff'),('Referrer-Policy','same-origin'),('Cache-Control','no-store')]
    path, method = env.get('PATH_INFO','/'), env['REQUEST_METHOD']
    try:
        if not path.startswith('/api/'):
            name = {'/':'index.html','/app.js':'app.js','/style.css':'style.css','/assets/africa-media-logo.png':'assets/africa-media-logo.png','/assets/africa-media-hero.png':'assets/africa-media-hero.png'}.get(path)
            if not name: raise LookupError('Not found')
            data = (ROOT/'static'/name).read_bytes()
            headers[0] = ('Content-Type',{'html':'text/html; charset=utf-8','js':'text/javascript; charset=utf-8','css':'text/css','png':'image/png'}[name.split('.')[-1]])
            headers.append(('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; media-src https: blob:; img-src 'self' https: data:; connect-src 'self' https://nominatim.openstreetmap.org; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"))
        else:
            with db() as c:
                cookie = SimpleCookie(); cookie.load(env.get('HTTP_COOKIE',''))
                token = cookie['media_session'].value if 'media_session' in cookie else ''
                sess = c.execute('SELECT s.*,u.email,u.role,u.active FROM sessions s JOIN users u ON u.id=s.user_id WHERE token=? AND expires>?',(hashlib.sha256(token.encode()).hexdigest(),int(time.time()))).fetchone()
                if sess and not sess['active']: sess = None
                user = sess['user_id'] if sess else None
                body = {}
                if method in ('POST','PUT','DELETE'):
                    length = int(env.get('CONTENT_LENGTH') or 0)
                    if length > 100000: raise ValueError('Request too large')
                    origin = env.get('HTTP_ORIGIN')
                    if origin and urlparse(origin).netloc != env.get('HTTP_HOST'): raise PermissionError('Cross-origin request rejected')
                    body = json.loads(env['wsgi.input'].read(length) or '{}')
                    if path not in ('/api/register','/api/login'):
                        if not sess: raise PermissionError('Sign in required')
                        if not hmac.compare_digest(env.get('HTTP_X_CSRF_TOKEN',''),sess['csrf']): raise PermissionError('Refresh and try again')
                def need():
                    if not sess: raise PermissionError('Sign in required')
                def admin():
                    need()
                    if sess['role'] != 'admin': raise PermissionError('Administrator required')
                q = parse_qs(env.get('QUERY_STRING',''))
                profile = int(body.get('profile_id') or q.get('profile_id',[0])[0])
                def owned_profile():
                    need()
                    p = c.execute('SELECT * FROM profiles WHERE id=? AND user_id=?',(profile,user)).fetchone()
                    if not p: raise PermissionError('Select your profile')
                    return p
                def video_access(vid):
                    v = c.execute('SELECT * FROM videos WHERE id=?',(vid,)).fetchone()
                    if not v or (v['visibility']!='public' and v['owner_id']!=user and (not sess or sess['role']!='admin')): raise LookupError('Video unavailable')
                    if profile and owned_profile()['kids'] and not v['kids']: raise PermissionError('Unavailable in Kids profile')
                    return v
                if path == '/api/health': result = {'ok': True,'service':'Africa Media Hub'}
                elif path in ('/api/register','/api/login') and method=='POST':
                    email = str(body.get('email','')).strip().lower(); pw = str(body.get('password',''))
                    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email) or len(pw)<12: raise ValueError('Valid email and a password of at least 12 characters required')
                    if path.endswith('register'):
                        if any(r[0]=='off' for r in c.execute("SELECT value FROM settings WHERE key='registration'")): raise PermissionError('Registration disabled')
                        try:
                            cur=c.execute('INSERT INTO users(email,password) VALUES(?,?)',(email,password(pw)))
                        except sqlite3.IntegrityError: raise ValueError('Account cannot be created with this email')
                        uid=cur.lastrowid
                        c.execute('INSERT INTO profiles(user_id,name) VALUES(?,?)',(uid,'My profile'))
                    else:
                        u=c.execute('SELECT * FROM users WHERE email=? AND active=1',(email,)).fetchone()
                        stored=u['password'] if u else password('dummy password')
                        if not hmac.compare_digest(stored,password(pw,stored.split(':')[0])): raise PermissionError('Invalid login')
                        uid=u['id']
                    raw=secrets.token_urlsafe(32); csrf=secrets.token_urlsafe(32)
                    c.execute('DELETE FROM sessions WHERE expires<?',(int(time.time()),))
                    c.execute('INSERT INTO sessions VALUES(?,?,?,?)',(hashlib.sha256(raw.encode()).hexdigest(),uid,csrf,int(time.time())+86400))
                    headers.append(('Set-Cookie','media_session='+raw+'; HttpOnly; SameSite=Lax; Path=/; Max-Age=86400'+('; Secure' if SECURE else '')))
                    audit(c,uid,'account '+path.rsplit('/',1)[-1]); result={'ok':True}
                elif path=='/api/logout' and method=='POST':
                    c.execute('DELETE FROM sessions WHERE token=?',(sess['token'],)); headers.append(('Set-Cookie','media_session=; Max-Age=0; Path=/; HttpOnly; SameSite=Lax')); result={'ok':True}
                elif path=='/api/me':
                    result={'user':{'id':user,'email':sess['email'],'role':sess['role']} if sess else None,'csrf':sess['csrf'] if sess else None,'profiles':rows(c,'SELECT id,name,kids FROM profiles WHERE user_id=?',(user,))}
                elif path=='/api/profiles' and method=='POST':
                    need(); name=str(body.get('name','')).strip()[:50]
                    if not name: raise ValueError('Profile name required')
                    if c.execute('SELECT count(*) FROM profiles WHERE user_id=?',(user,)).fetchone()[0]>=6: raise ValueError('Six profile limit')
                    c.execute('INSERT INTO profiles(user_id,name,kids) VALUES(?,?,?)',(user,name,int(bool(body.get('kids'))))); result={'ok':True}
                elif path=='/api/catalog':
                    args=[]; sql="SELECT id,title,description,kind,category,url,kids FROM videos WHERE visibility='public'"
                    if profile and owned_profile()['kids']: sql+=' AND kids=1'
                    search=q.get('q',[''])[0]
                    if search: sql+=' AND (title LIKE ? OR category LIKE ?)'; args += ['%'+search+'%']*2
                    result=rows(c,sql+' ORDER BY created DESC',args)
                elif path=='/api/admin/iptv' and method=='GET':
                    admin()
                    from iptv import SOURCES, BASE
                    last=c.execute("SELECT value FROM settings WHERE key='iptv_last_refresh'").fetchone()
                    result={'sources':[{'key':k,'url':('Bundled Working_Channels.m3u' if k=='working' else BASE+v)} for k,v in SOURCES.items()], 'last':json.loads(last[0]) if last else None}
                elif path=='/api/admin/iptv' and method=='POST':
                    admin()
                    from iptv import refresh as refresh_channels
                    result=refresh_channels(c,str(body.get('source','all')))
                    audit(c,user,'playlist refresh '+result['source']+' added '+str(result['added']))
                elif path=='/api/location/countries':
                    from location_channels import COUNTRIES
                    result=COUNTRIES
                elif path=='/api/location/channels':
                    from location_channels import country_channels
                    result=country_channels(q.get('country',[''])[0])
                elif path=='/api/guide': result={'channels':rows(c,'SELECT * FROM channels WHERE enabled=1'),'programs':rows(c,'SELECT * FROM programs WHERE end>? ORDER BY start',(int(time.time())-86400,))}
                elif path=='/api/studio' and method=='GET':
                    need(); result=rows(c,'SELECT * FROM videos WHERE owner_id=? ORDER BY created DESC',(user,))
                elif path=='/api/studio' and method=='POST':
                    need(); title=str(body.get('title','')).strip()[:200]
                    if not title: raise ValueError('Title required')
                    kind=body.get('kind','video')
                    if kind not in ('video','movie','tv','short','podcast','live'): raise ValueError('Invalid content type')
                    c.execute('INSERT INTO videos(owner_id,title,description,kind,category,url,kids,created) VALUES(?,?,?,?,?,?,?,?)',(user,title,str(body.get('description',''))[:5000],kind,str(body.get('category','Entertainment'))[:80],valid_url(str(body.get('url',''))),int(bool(body.get('kids'))),int(time.time())))
                    audit(c,user,'submitted content for moderation'); result={'ok':True,'status':'draft'}
                elif path=='/api/library':
                    owned_profile(); result={'saved':rows(c,'SELECT v.* FROM saved s JOIN videos v ON v.id=s.video_id WHERE s.profile_id=? AND v.visibility="public"'+(' AND v.kids=1' if owned_profile()['kids'] else ''),(profile,)), 'history':rows(c,'SELECT v.*,h.position FROM history h JOIN videos v ON v.id=h.video_id WHERE h.profile_id=? AND v.visibility="public"'+(' AND v.kids=1' if owned_profile()['kids'] else '')+' ORDER BY h.updated DESC',(profile,)), 'recordings':rows(c,'SELECT r.*,p.title FROM recording_requests r JOIN programs p ON p.id=r.program_id WHERE r.profile_id=?',(profile,)), 'playlists':rows(c,'SELECT * FROM playlists WHERE profile_id=?',(profile,))}
                elif path=='/api/playlist' and method=='POST':
                    owned_profile(); name=str(body.get('name','')).strip()[:100]
                    if not name: raise ValueError('Name required')
                    c.execute('INSERT INTO playlists(profile_id,name) VALUES(?,?)',(profile,name)); result={'ok':True}
                elif path=='/api/playlist/item' and method=='POST':
                    owned_profile(); pid=int(body['playlist_id']); vid=int(body['video_id']); video_access(vid)
                    if not c.execute('SELECT id FROM playlists WHERE id=? AND profile_id=?',(pid,profile)).fetchone(): raise PermissionError('Playlist unavailable')
                    c.execute('INSERT OR IGNORE INTO playlist_items VALUES(?,?)',(pid,vid)); result={'ok':True}
                elif path=='/api/action' and method=='POST':
                    owned_profile(); vid=int(body['video_id']); video_access(vid); action=body.get('action')
                    if action=='save': c.execute('INSERT OR IGNORE INTO saved VALUES(?,?)',(profile,vid))
                    elif action=='unsave': c.execute('DELETE FROM saved WHERE profile_id=? AND video_id=?',(profile,vid))
                    elif action=='progress': c.execute('INSERT OR REPLACE INTO history VALUES(?,?,?,?)',(profile,vid,max(0,min(float(body.get('position',0)),10000000)),int(time.time())))
                    elif action in ('like','dislike'): c.execute('INSERT OR REPLACE INTO reactions VALUES(?,?,?)',(profile,vid,1 if action=='like' else -1))
                    elif action=='report':
                        reason=str(body.get('reason','')).strip()[:1000]
                        if not reason: raise ValueError('Reason required')
                        c.execute('INSERT INTO reports(user_id,video_id,reason) VALUES(?,?,?)',(user,vid,reason))
                    else: raise ValueError('Unknown action')
                    result={'ok':True}
                elif path=='/api/comments':
                    vid=int(body.get('video_id') or q.get('video_id',[0])[0]); v=video_access(vid)
                    if v['kids']: raise PermissionError('Comments disabled on children’s content')
                    if method=='POST':
                        need(); text=str(body.get('body','')).strip()[:2000]
                        if not text: raise ValueError('Comment required')
                        c.execute('INSERT INTO comments(user_id,video_id,body,created) VALUES(?,?,?,?)',(user,vid,text,int(time.time())))
                    result=rows(c,'SELECT id,body,created FROM comments WHERE video_id=? ORDER BY created DESC LIMIT 100',(vid,))
                elif path=='/api/record' and method=='POST':
                    owned_profile(); prog=c.execute('SELECT * FROM programs WHERE id=? AND recordable=1',(int(body['program_id']),)).fetchone()
                    if not prog: raise ValueError('Recording is not enabled for this program')
                    c.execute('INSERT OR IGNORE INTO recording_requests(profile_id,program_id) VALUES(?,?)',(profile,prog['id'])); result={'ok':True,'status':'awaiting_recorder','message':'Request saved. Recorder integration is required; no media has been recorded.'}
                elif path=='/api/admin/manage':
                    admin()
                    from admin_controls import manage
                    result=manage(c,user,method,body,password,valid_url,audit)
                elif path=='/api/admin' and method=='GET':
                    admin(); result={'users':rows(c,'SELECT id,email,role,active FROM users'),'videos':rows(c,'SELECT * FROM videos'),'channels':rows(c,'SELECT * FROM channels'),'reports':rows(c,'SELECT * FROM reports'),'audit':rows(c,'SELECT * FROM audit ORDER BY id DESC LIMIT 100'),'counts':{'users':c.execute('SELECT count(*) FROM users').fetchone()[0],'videos':c.execute('SELECT count(*) FROM videos').fetchone()[0]}}
                elif path=='/api/admin' and method=='POST':
                    admin(); action=body.get('action')
                    if action=='publish': c.execute("UPDATE videos SET visibility='public' WHERE id=?",(int(body['id']),))
                    elif action=='unpublish': c.execute("UPDATE videos SET visibility='draft' WHERE id=?",(int(body['id']),))
                    elif action=='delete_video': c.execute('DELETE FROM videos WHERE id=?',(int(body['id']),))
                    elif action=='user':
                        uid=int(body['id']); active=int(bool(body.get('active'))); role=body.get('role','viewer')
                        if role not in ('viewer','creator','admin'): raise ValueError('Invalid role')
                        if uid==user and (not active or role!='admin'): raise ValueError('Cannot remove your own administrator access')
                        c.execute('UPDATE users SET active=?,role=? WHERE id=?',(active,role,uid))
                    elif action=='channel':
                        name=str(body.get('name','')).strip()[:100]
                        if not name: raise ValueError('Channel name required')
                        c.execute('INSERT INTO channels(name,url,category) VALUES(?,?,?)',(name,valid_url(str(body.get('url',''))),str(body.get('category','Entertainment'))[:80]))
                    elif action=='program':
                        start,end=int(body['start']),int(body['end'])
                        if end<=start: raise ValueError('End must follow start')
                        c.execute('INSERT INTO programs(channel_id,title,start,end,recordable) VALUES(?,?,?,?,0)',(int(body['channel_id']),str(body['title'])[:200],start,end))
                    elif action=='resolve_report': c.execute("UPDATE reports SET status='resolved' WHERE id=?",(int(body['id']),))
                    else: raise ValueError('Unknown admin action')
                    audit(c,user,action); result={'ok':True}
                else: raise LookupError('Not found')
                data=json.dumps(result).encode()
    except PermissionError as e: status='403 Forbidden'; data=json.dumps({'error':str(e)}).encode()
    except LookupError as e: status='404 Not Found'; data=json.dumps({'error':str(e)}).encode()
    except (ValueError,TypeError,KeyError,sqlite3.IntegrityError) as e: status='400 Bad Request'; data=json.dumps({'error':str(e)}).encode()
    except Exception:
        import traceback; traceback.print_exc(); status='500 Internal Server Error'; data=b'{"error":"Internal server error"}'
    respond(status,headers); return [data]

if __name__=='__main__':
    import argparse, getpass
    parser=argparse.ArgumentParser(); parser.add_argument('command',choices=['serve','init','admin','refresh-channels'],nargs='?',default='serve'); parser.add_argument('--email'); parser.add_argument('--source',default='all'); args=parser.parse_args(); init()
    if args.command=='admin':
        if not args.email: parser.error('--email required')
        pw=getpass.getpass('Administrator password (12+ characters): ')
        if len(pw)<12: parser.error('Password too short')
        with db() as c:
            c.execute("INSERT INTO users(email,password,role) VALUES(?,?,'admin') ON CONFLICT(email) DO UPDATE SET password=excluded.password,role='admin',active=1",(args.email.lower(),password(pw)))
            uid=c.execute('SELECT id FROM users WHERE email=?',(args.email.lower(),)).fetchone()[0]
            if not c.execute('SELECT id FROM profiles WHERE user_id=?',(uid,)).fetchone(): c.execute('INSERT INTO profiles(user_id,name) VALUES(?,?)',(uid,'Administrator'))
        print('Administrator configured')
    elif args.command=='refresh-channels':
        from iptv import refresh as refresh_channels
        with db() as c: print(json.dumps(refresh_channels(c,args.source)))
    elif args.command=='serve': make_server('127.0.0.1',int(os.environ.get('PORT','18840')),app).serve_forever()

