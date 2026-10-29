"""Profile-private cameras with an outbound, token-paired LAN gateway."""
import base64
import hashlib
import hmac
import secrets
import time

def init(c):
    c.execute('''CREATE TABLE IF NOT EXISTS profile_cameras (
        id INTEGER PRIMARY KEY, profile_id INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
        name TEXT NOT NULL, device_hint TEXT NOT NULL DEFAULT '', token_hash TEXT,
        frame BLOB, last_seen INTEGER NOT NULL DEFAULT 0, created INTEGER NOT NULL)''')

def handle(c, profile, path, method, body, query):
    init(c)
    if path == '/api/my-streaming' and method == 'GET':
        now = int(time.time())
        return [dict(r, online=bool(r['last_seen'] and now-r['last_seen'] < 30)) for r in c.execute(
            'SELECT id,name,device_hint,last_seen,token_hash IS NOT NULL AS paired FROM profile_cameras WHERE profile_id=? ORDER BY id', (profile,))]
    camera_id = int(body.get('id') or query.get('id', [0])[0])
    if method == 'POST' and body.get('action') == 'add' and path == '/api/my-streaming':
        if c.execute('SELECT count(*) FROM profile_cameras WHERE profile_id=?', (profile,)).fetchone()[0] >= 20:
            raise ValueError('Maximum 20 cameras per profile')
        name = str(body.get('name', '')).strip()[:100]
        if not name: raise ValueError('Camera name required')
        hint = str(body.get('device_hint', '')).strip()[:200]
        if '://' in hint or '@' in hint: raise ValueError('Use a device name or private address, without URLs or credentials')
        cursor = c.execute('INSERT INTO profile_cameras(profile_id,name,device_hint,created) VALUES(?,?,?,?)', (profile,name,hint,int(time.time())))
        return {'id': cursor.lastrowid}
    camera = c.execute('SELECT * FROM profile_cameras WHERE id=? AND profile_id=?', (camera_id,profile)).fetchone()
    if not camera: raise LookupError('Camera unavailable')
    if method == 'GET' and path == '/api/my-streaming/frame':
        online = bool(camera['frame'] and int(time.time())-camera['last_seen'] < 30)
        return {'online': online, 'last_seen':camera['last_seen'], 'jpeg':base64.b64encode(camera['frame']).decode() if online else ''}
    if method != 'POST' or path != '/api/my-streaming': raise ValueError('Unsupported camera request')
    action = body.get('action')
    if action == 'pair':
        token = secrets.token_urlsafe(32)
        c.execute('UPDATE profile_cameras SET token_hash=?,frame=NULL,last_seen=0 WHERE id=?', (hashlib.sha256(token.encode()).hexdigest(),camera_id))
        return {'camera_id':camera_id,'gateway_token':token}
    if action == 'revoke':
        c.execute('UPDATE profile_cameras SET token_hash=NULL,frame=NULL,last_seen=0 WHERE id=?', (camera_id,))
    elif action == 'delete':
        c.execute('DELETE FROM profile_cameras WHERE id=?', (camera_id,))
    elif action == 'rename':
        name = str(body.get('name','')).strip()[:100]
        if not name: raise ValueError('Camera name required')
        c.execute('UPDATE profile_cameras SET name=? WHERE id=?', (name,camera_id))
    else: raise ValueError('Unknown camera action')
    return {'ok': True}

def ingest(c, token, body):
    if not isinstance(body,dict): raise ValueError("Invalid gateway payload")
    init(c)
    if len(token) < 32 or len(token) > 128: raise PermissionError('Gateway authentication required')
    camera = c.execute('''SELECT pc.* FROM profile_cameras pc JOIN profiles p ON p.id=pc.profile_id
        JOIN users u ON u.id=p.user_id WHERE pc.id=? AND u.active=1 AND p.kids=0''', (int(body.get('camera_id',0)),)).fetchone()
    digest = hashlib.sha256(token.encode()).hexdigest()
    if not camera or not camera['token_hash'] or not hmac.compare_digest(camera['token_hash'],digest):
        raise PermissionError('Gateway pairing unavailable or revoked')
    if int(time.time())-camera['last_seen'] < 1: raise ValueError('Wait before sending the next frame')
    try: frame = base64.b64decode(body.get('jpeg',''), validate=True)
    except Exception: raise ValueError('Invalid JPEG encoding') from None
    if not 4 <= len(frame) <= 60000 or not frame.startswith(b'\xff\xd8') or not frame.endswith(b'\xff\xd9'):
        raise ValueError('JPEG frame must be at most 60 KB')
    c.execute('UPDATE profile_cameras SET frame=?,last_seen=? WHERE id=?', (frame,int(time.time()),camera['id']))
    return {'ok':True}
