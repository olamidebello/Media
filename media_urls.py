"""Platform URL normalization; no proxying or HTTP fallback."""
from urllib.parse import urlsplit, urlunsplit

def https_url(value):
    value = str(value).strip()
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in value) or "\\" in value:
        raise ValueError('Use an HTTP or HTTPS URL without control characters')
    p = urlsplit(value)
    if p.scheme not in ('http', 'https') or not p.hostname or p.username is not None or p.password is not None:
        raise ValueError('Use an HTTP or HTTPS URL without credentials')
    port = p.port  # Validate malformed ports before storing a URL.
    host = '[' + p.hostname + ']' if ':' in p.hostname else p.hostname
    if port is not None and port != 443 and not (p.scheme == 'http' and port == 80):
        host += ':' + str(port)
    return urlunsplit(('https', host, p.path, p.query, p.fragment))
