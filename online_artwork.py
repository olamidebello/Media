"""Conservative Commons image lookup; no keys, embedded HTML, or arbitrary server-side image fetches."""
import html,json,re,time,urllib.request
from urllib.parse import urlencode,urlparse

def plain(value):return html.unescape(re.sub('<[^>]+>','',str(value or ''))).strip()[:500]
def normalized(value):return re.sub(r'[^\w]+','',str(value).casefold(),flags=re.UNICODE)
def clean_name(name):
    return re.sub(r'\s+(?:HD|FHD|UHD|4K|TV)$','',re.sub(r'\([^)]*\)|\[[^]]*\]','',name),flags=re.I).strip()[:120]
def choose(name,pages):
    needle=normalized(clean_name(name))
    if len(needle)<3:return None
    for page in sorted(pages,key=lambda p:p.get('index',999)):
        title=str(page.get('title',''))
        if needle not in normalized(title):continue
        if re.search(r'\b(?:19\d\d|200\d|201\d)\b',title):continue
        infos=page.get('imageinfo',[])
        if not infos:continue
        info=infos[0];meta=info.get('extmetadata',{})
        if not re.search('logo|channel|television',title+' '+plain(meta.get('ImageDescription',{}).get('value','')),re.I):continue
        license_name=plain(meta.get('LicenseShortName',{}).get('value',''))
        if not re.search(r'public domain|^CC0|^CC BY(?:-SA)?(?: |$)',license_name,re.I):continue
        image=info.get('thumburl') or info.get('url','');source=info.get('descriptionurl','')
        if urlparse(image).scheme!='https' or urlparse(image).hostname!='upload.wikimedia.org':continue
        if urlparse(source).scheme!='https' or urlparse(source).hostname!='commons.wikimedia.org':continue
        if info.get('mime') not in ('image/png','image/jpeg','image/svg+xml','image/webp'):continue
        artist=plain(meta.get('Artist',{}).get('value','')) or 'Wikimedia Commons contributor'
        return {'url':image,'source':source,'credit':artist,'license':license_name,'title':plain(title)}
    return None

def lookup(name):
    query={'action':'query','format':'json','generator':'search','gsrsearch':'"'+clean_name(name)+'" logo','gsrnamespace':6,'gsrlimit':5,'prop':'imageinfo','iiprop':'url|mime|extmetadata','iiurlwidth':640}
    request=urllib.request.Request('https://commons.wikimedia.org/w/api.php?'+urlencode(query),headers={'User-Agent':'AfricaMediaHubArtwork/1.0 (https://media.africandroid.world/legal/contact)'})
    with urllib.request.urlopen(request,timeout=12) as response:raw=response.read(2000001)
    if len(raw)>2000000:raise ValueError('Artwork search response too large')
    data=json.loads(raw)
    if 'error' in data:raise ValueError('Artwork search unavailable')
    return choose(name,list(data.get('query',{}).get('pages',{}).values()))
