"""Same-origin media relay for platform-issued, user-bound playback URLs."""
import base64
import hashlib
import hmac
import http.client
import ipaddress
import json
import re
import socket
import ssl
import time
from urllib.parse import urlsplit, urljoin

LIMIT = 32 * 1024 * 1024
TTL = 12 * 3600


def sign(secret, url, user, scope):
    payload = base64.urlsafe_b64encode(json.dumps(
        [url, user, scope, int(time.time()) + TTL], separators=(',', ':')
    ).encode()).decode().rstrip('=')
    digest = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return '/api/playback/resource?token=' + payload + '.' + digest


def verify(secret, token, user):
    try:
        if len(token) > 12000:
            raise ValueError()
        payload, digest = token.rsplit('.', 1)
        expected = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(digest, expected):
            raise ValueError()
        url, owner, scope, expires = json.loads(base64.urlsafe_b64decode(payload + '=' * (-len(payload) % 4)))
        if owner != user or expires < time.time() or expires > time.time() + TTL + 5:
            raise ValueError()
        return url, scope
    except (ValueError, TypeError, KeyError, UnicodeError):
        raise PermissionError('Playback link expired or invalid') from None


def target(url):
    from iptv import normalize_media_url
    p = urlsplit(normalize_media_url(url))
    addresses = socket.getaddrinfo(p.hostname, p.port or (443 if p.scheme == 'https' else 80), type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
        raise ValueError('Media destination must resolve only to public addresses')
    return p, addresses[0]


def fetch(url, range_header=''):
    """Validate every redirect and connect to the validated IP, preserving TLS SNI."""
    for _ in range(5):
        p, address = target(url)
        cls = http.client.HTTPSConnection if p.scheme == 'https' else http.client.HTTPConnection
        kwargs = {'timeout': 10}
        if p.scheme == 'https':
            kwargs['context'] = ssl.create_default_context()
        conn = cls(p.hostname, p.port, **kwargs)
        def connect_pinned(addresses, timeout, source_address=None, **unused):
            sock = socket.socket(address[0], address[1], address[2])
            sock.settimeout(timeout)
            try:
                sock.connect(address[4])
                return sock
            except Exception:
                sock.close()
                raise
        conn._create_connection = connect_pinned
        headers = {'User-Agent': 'AfricaMediaHub/1.0', 'Accept-Encoding': 'identity'}
        if range_header:
            if not re.fullmatch(r'bytes=\d*-\d*', range_header) or range_header == 'bytes=-':
                raise ValueError('Unsupported media range')
            match=re.fullmatch(r'bytes=(\d+)-(\d*)',range_header)
            if match and (not match[2] or int(match[2])-int(match[1])>=8*1024*1024):
                range_header='bytes='+match[1]+'-'+str(int(match[1])+8*1024*1024-1)
            headers['Range'] = range_header
        try:
            conn.request('GET', (p.path or '/') + ('?' + p.query if p.query else ''), headers=headers)
            response = conn.getresponse()
            if response.status in (301, 302, 303, 307, 308):
                location = response.getheader('Location')
                if not location:
                    raise ValueError('Invalid media redirect')
                url = urljoin(url, location)
                continue
            if response.status not in (200, 206):
                raise ValueError('Media source returned HTTP ' + str(response.status))
            chunks = []
            size = 0
            deadline = time.monotonic() + 25
            while True:
                data = response.read1(min(65536, LIMIT + 1 - size))
                if not data:
                    break
                chunks.append(data)
                size += len(data)
                if size > LIMIT or time.monotonic() > deadline:
                    raise ValueError('Media response exceeds relay limits')
            fields = {key: response.getheader(key) for key in ('Content-Type', 'Content-Range', 'Accept-Ranges') if response.getheader(key)}
            return b''.join(chunks), url, response.status, fields
        except (OSError, http.client.HTTPException) as error:
            raise ValueError('Media source unavailable') from error
        finally:
            conn.close()
    raise ValueError('Too many media redirects')


def relay(url, secret, user, scope, range_header=''):
    data, final_url, status, fields = fetch(url, range_header)
    if data.lstrip().startswith(b'#EXTM3U'):
        if len(data) > 1024 * 1024:
            raise ValueError('Playlist too large')
        def child(value):
            return sign(secret, urljoin(final_url, value), user, scope)
        lines = []
        for line in data.decode('utf-8-sig').splitlines():
            # Do not silently misresolve HLS variable substitutions.
            if line.startswith('#EXT-X-DEFINE') or '{$' in line:
                raise ValueError('HLS variable playlists are not supported by this relay')
            if line and not line.startswith('#'):
                line = child(line.strip())
            elif line.startswith('#'):
                line = re.sub(r'\bURI="([^"]*)"', lambda m: 'URI="' + child(m[1]) + '"', line)
            lines.append(line)
        data = ('\n'.join(lines) + '\n').encode()
        fields = {'Content-Type': 'application/vnd.apple.mpegurl'}
        status = 200
    else:
        mime = fields.get('Content-Type', '').split(';')[0].lower()
        if mime in ('text/html', 'application/xhtml+xml', 'image/svg+xml'):
            raise ValueError('Source is not media')
    return data, status, fields
