from urllib.parse import urlparse

def safe_url(value):
    value=str(value or '').strip()
    if len(value)>2000: return ''
    try:
        parsed=urlparse(value)
        if parsed.scheme=='https' and parsed.hostname and not parsed.username and not parsed.password:return value
    except ValueError:pass
    return ''

def init(c):
    for table in ('videos','channels'):
        columns={row[1] for row in c.execute('PRAGMA table_info('+table+')')}
        if columns and 'thumbnail' not in columns:
            c.execute('ALTER TABLE '+table+" ADD COLUMN thumbnail TEXT NOT NULL DEFAULT ''")
