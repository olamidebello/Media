"""Country-specific directory lookup with bounded, temporary caching."""
import time, threading
from urllib.request import Request, build_opener
from iptv import BASE, LIMIT, SameHostRedirect, parse
COUNTRIES='DZ AO BJ BW BF BI CV CM CF TD KM CG CD CI DJ EG GQ ER SZ ET GA GM GH GN GW KE LS LR LY MG MW ML MR MU MA MZ NA NE NG RW ST SN SC SL SO ZA SS SD TZ TG TN UG ZM ZW US GB CA FR DE ES PT IT NL BE CH AT IE AU NZ IN PK BD CN JP KR ID MY SG PH TH VN BR MX AR CL CO PE AE SA QA KW TR IL JO LB IQ IR UA PL RO GR NO SE FI DK IS RU'.split()
_cache={};_lock=threading.Lock()
def country_channels(code):
 code=str(code).upper()
 if code not in COUNTRIES:raise ValueError('Choose a supported country')
 with _lock:
  cached=_cache.get(code)
  if cached and cached['expires']>time.time():return cached['result']
 try:
  with build_opener(SameHostRedirect()).open(Request(BASE+'countries/'+code.lower()+'.m3u',headers={'User-Agent':'AfricaMediaHub/1.0'}),timeout=15) as response:data=response.read(LIMIT+1)
 except OSError as e:raise ValueError('Country directory is unavailable. Try again or select another country.') from e
 if len(data)>LIMIT:raise ValueError('Country directory too large')
 text=data.decode('utf-8-sig')
 if not text.lstrip().startswith('#EXTM3U'):raise ValueError('Invalid country directory')
 items,skipped=parse(text)
 result={'country':code,'channels':[{**x,'id':'local-'+str(n)} for n,x in enumerate(items)],'skipped':skipped,'updated':int(time.time()),'source':'IPTV-org country directory'}
 with _lock:_cache[code]={'result':result,'expires':time.time()+3600}
 return result
