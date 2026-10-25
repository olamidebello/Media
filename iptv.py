"""Bounded imports from the configured IPTV-org playlist directory."""
import re, time, json, ipaddress
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, build_opener, HTTPRedirectHandler

BASE='https://iptv-org.github.io/iptv/'
SOURCES={'roku':'bundled/Roku_Supplied.m3u','samsung':'bundled/Samsung_TV_Plus_Supplied.m3u','uploaded':'bundled/Uploaded_Channels.m3u','aljazeera':'bundled/Al_Jazeera_Sources.m3u','working':'bundled/Working_Channels.m3u',**{x:'countries/'+x+'.m3u' for x in ['dz', 'ao', 'bj', 'bw', 'bf', 'bi', 'cv', 'cm', 'cf', 'td', 'km', 'cg', 'cd', 'ci', 'dj', 'eg', 'gq', 'er', 'sz', 'et', 'ga', 'gm', 'gh', 'gn', 'gw', 'ke', 'ls', 'lr', 'ly', 'mg', 'mw', 'ml', 'mr', 'mu', 'ma', 'mz', 'na', 'ne', 'ng', 'rw', 'st', 'sn', 'sc', 'sl', 'so', 'za', 'ss', 'sd', 'tz', 'tg', 'tn', 'ug', 'zm', 'zw', 'us', 'gb', 'ca', 'fr', 'de', 'es', 'pt', 'it', 'au', 'in', 'br', 'jp']},'all':'index.m3u',**{x:'categories/'+x+'.m3u' for x in ['animation', 'auto', 'business', 'classic', 'comedy', 'cooking', 'culture', 'documentary', 'education', 'entertainment', 'family', 'general', 'interactive', 'kids', 'legislative', 'lifestyle', 'movies', 'music', 'news', 'outdoor', 'public', 'relax', 'religious', 'science', 'series', 'shop', 'sports', 'travel', 'weather', 'undefined']},**{x:'languages/'+x+'.m3u' for x in ['eng','fra','ara']}}
LIMIT=12*1024*1024

def normalize_media_url(value):
    """Accept HTTP input and store HTTPS, preserving path and signed query."""
    from media_urls import https_url
    value=https_url(value)
    if not stream_url(value):
        raise ValueError('Use a public HTTP or HTTPS media URL')
    return value

def stream_url(value):
    try:
        p=urlparse(value)
        if p.scheme!='https' or not p.hostname or p.username or p.password or (p.port is not None and not 1<=p.port<=65535): return False
        if p.hostname.lower() in ('localhost','localhost.localdomain') or p.hostname.lower().endswith(('.local','.internal')): return False
        try:
            if not ipaddress.ip_address(p.hostname).is_global:return False
        except ValueError:pass
        return True
    except ValueError:return False

class SameHostRedirect(HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        if not newurl.startswith(BASE):raise ValueError('Playlist redirected outside the configured source')
        return super().redirect_request(req,fp,code,msg,headers,newurl)

def download(key):
    if key not in SOURCES:raise ValueError('Unknown playlist source')
    if key in ('working','aljazeera','uploaded','samsung','roku'):
        filename={'roku':'Roku_Supplied.m3u','samsung':'Samsung_TV_Plus_Supplied.m3u','working':'Working_Channels.m3u','aljazeera':'Al_Jazeera_Sources.m3u','uploaded':'Uploaded_Channels.m3u'}[key]
        return (Path(__file__).parent/'data'/filename).read_text(encoding='utf-8')
    req=Request(BASE+SOURCES[key],headers={'User-Agent':'AfricaMediaHub/1.0'})
    try:
        with build_opener(SameHostRedirect()).open(req,timeout=20) as response:
            data=response.read(LIMIT+1)
    except OSError as e:raise ValueError('Playlist fetch failed; existing channels were preserved') from e
    if len(data)>LIMIT:raise ValueError('Playlist exceeds size limit')
    text=data.decode('utf-8-sig')
    if not text.lstrip().startswith('#EXTM3U'):raise ValueError('Source did not return an M3U playlist')
    return text

def parse(text):
    metadata=None; items=[]; skipped=0
    for line in text.splitlines():
        line=line.strip()
        if line.startswith('#EXTINF:'):
            match=re.search(r',([^\r\n]*)$',line)
            attrs=dict(re.findall(r'([\w-]+)="([^"]*)"',line))
            metadata={'name':(match.group(1) if match else attrs.get('tvg-id','Channel'))[:200],'category':attrs.get('group-title','General')[:100] or 'General'}
        elif line and not line.startswith('#') and metadata:
            try:items.append({**metadata,'url':normalize_media_url(line)})
            except ValueError:skipped+=1
            metadata=None
    return items,skipped

def refresh(c,key='all',text=None):
    if key not in SOURCES:raise ValueError('Unknown playlist source')
    items,skipped=parse(download(key) if text is None else text)
    if not items:raise ValueError('Playlist contained no usable HTTPS channels; existing channels were preserved')
    added=existing=0
    for item in items:
        if c.execute('SELECT id FROM channels WHERE url=?',(item['url'],)).fetchone():existing+=1;continue
        category=item['category'] if key in ('all','eng','fra','ara','working','aljazeera','uploaded','samsung','roku') else key.title()
        c.execute('INSERT INTO channels(name,url,category,enabled) VALUES(?,?,?,?)',(item['name'],item['url'],category,0 if key=='uploaded' else 1));added+=1
    result={'source':key,'added':added,'existing':existing,'skipped':skipped,'updated':int(time.time())}
    c.execute('INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)',('iptv_last_refresh',json.dumps(result)))
    return result

