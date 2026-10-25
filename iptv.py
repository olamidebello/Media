"""Bounded imports from the configured IPTV-org playlist directory."""
import re, time, json, ipaddress
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, build_opener, HTTPRedirectHandler

BASE='https://iptv-org.github.io/iptv/'
SOURCES={'working':'bundled/Working_Channels.m3u',**{x:'countries/'+x+'.m3u' for x in ['ng','za','gh','ke','tz','ug','eg','ma','et','sn']},'all':'index.m3u',**{x:'categories/'+x+'.m3u' for x in ['animation', 'auto', 'business', 'classic', 'comedy', 'cooking', 'culture', 'documentary', 'education', 'entertainment', 'family', 'general', 'interactive', 'kids', 'legislative', 'lifestyle', 'movies', 'music', 'news', 'outdoor', 'public', 'relax', 'religious', 'science', 'series', 'shop', 'sports', 'travel', 'weather', 'undefined']},**{x:'languages/'+x+'.m3u' for x in ['eng','fra','ara']}}
LIMIT=12*1024*1024

def stream_url(value):
    try:
        p=urlparse(value)
        if p.scheme!='https' or not p.hostname or p.username or p.password or p.port not in (None,443): return False
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
    if key=='working':
        return (Path(__file__).parent/'data/Working_Channels.m3u').read_text(encoding='utf-8')
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
            if stream_url(line):items.append({**metadata,'url':line})
            else:skipped+=1
            metadata=None
    return items,skipped

def refresh(c,key='all',text=None):
    if key not in SOURCES:raise ValueError('Unknown playlist source')
    items,skipped=parse(download(key) if text is None else text)
    if not items:raise ValueError('Playlist contained no usable HTTPS channels; existing channels were preserved')
    added=existing=0
    for item in items:
        if c.execute('SELECT id FROM channels WHERE url=?',(item['url'],)).fetchone():existing+=1;continue
        category=item['category'] if key in ('all','eng','fra','ara','working') else key.title()
        c.execute('INSERT INTO channels(name,url,category) VALUES(?,?,?)',(item['name'],item['url'],category));added+=1
    result={'source':key,'added':added,'existing':existing,'skipped':skipped,'updated':int(time.time())}
    c.execute('INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)',('iptv_last_refresh',json.dumps(result)))
    return result
