#!/usr/bin/env python3
"""Verify enabled channel streams; back up before removing repeat hard failures."""
import argparse,concurrent.futures,datetime,ipaddress,json,os,socket,sqlite3,ssl,time,uuid
from pathlib import Path
from urllib.parse import urlsplit,urljoin
from urllib.request import Request,build_opener,HTTPRedirectHandler
from urllib.error import HTTPError,URLError

class InvalidStream(ValueError):pass

def public_url(url):
 p=urlsplit(url)
 if p.scheme!='https' or not p.hostname or p.username is not None or p.password is not None:raise InvalidStream('Not a public HTTPS URL')
 addresses=socket.getaddrinfo(p.hostname,p.port or 443,type=socket.SOCK_STREAM)
 if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):raise InvalidStream('Private or local stream address')
 return url

class Redirects(HTTPRedirectHandler):
 def redirect_request(self,req,fp,code,msg,headers,newurl):
  public_url(newurl)
  return super().redirect_request(req,fp,code,msg,headers,newurl)

def fetch(url,timeout):
 public_url(url)
 with build_opener(Redirects()).open(Request(url,headers={'User-Agent':'AfricaMediaHub/1.0 channel check','Range':'bytes=0-262143'}),timeout=timeout) as r:
  return r.read(262144),r.geturl()

def probe(channel,timeout=5):
 result={'id':channel['id'],'name':channel['name'],'url':channel['url']}
 try:
  url=channel['url']
  for depth in range(5):
   data,final=fetch(url,timeout)
   if data.lstrip().startswith(b'#EXTM3U'):
    lines=data.decode(errors='replace').splitlines()
    if any(line.startswith('#EXT-X-KEY:') and 'METHOD=NONE' not in line for line in lines):
     return {**result,'status':'inconclusive','detail':'Encrypted stream requires playback validation'}
    refs=[line.strip() for line in lines if line.strip() and not line.startswith('#')]
    if not refs:raise InvalidStream('Empty playlist')
    url=urljoin(final,refs[0]);continue
   media=(len(data)>376 and data[0]==71 and data[188]==71) or (len(data)>12 and data[4:8] in (b'ftyp',b'styp',b'moof',b'sidx')) or data.startswith((b'ID3',b'\xff\xf1',b'\xff\xf9'))
   if not media:raise InvalidStream('Response has no recognizable media bytes')
   return {**result,'status':'verified','detail':'Manifest traversal and media bytes received; decoding not tested'}
  raise InvalidStream('Playlist nesting limit exceeded')
 except HTTPError as e:
  return {**result,'status':'unavailable' if e.code in (404,410) else 'inconclusive','detail':'HTTP '+str(e.code)}
 except InvalidStream as e:return {**result,'status':'unavailable','detail':str(e)}
 except Exception as e:return {**result,'status':'inconclusive','detail':type(e).__name__}

def scan(channels,workers=16,timeout=5):
 with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
  first=list(pool.map(lambda c:probe(c,timeout),channels))
  repeat={r['id'] for r in first if r['status']=='unavailable'}
  second={r['id']:r for r in pool.map(lambda c:probe(c,timeout),[c for c in channels if c['id'] in repeat])}
 for r in first:
  if r['id'] in second:
   again=second[r['id']]
   if again['status']!='unavailable':r.update(status=again['status'],detail='Recheck: '+again['detail'])
   else:r['detail']='Failed twice: '+r['detail']+'; '+again['detail']
 return first

def apply(c,results,folder):
 counts={status:sum(r['status']==status for r in results) for status in ('verified','unavailable','inconclusive')}
 if results and not counts['verified']:raise ValueError('No stream passed verification; database unchanged to avoid a network-wide outage purge')
 folder=Path(folder);folder.mkdir(parents=True,exist_ok=True,mode=0o700)
 stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:8]
 backup=folder/('before-prune-'+stamp+'.db')
 # SQLite backup uses a separate connection so no live application transaction is blocked by our writes.
 with sqlite3.connect(backup) as dst:
  c.backup(dst)
  if dst.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Backup integrity check failed; channels unchanged')
 os.chmod(backup,0o600)
 report=folder/('channel-checks-'+stamp+'.json');report.write_text(json.dumps({'checked_at':stamp,'counts':counts,'channels':results},indent=2));os.chmod(report,0o600)
 removed=disabled=0
 with c:
  for r in results:
   # Do not alter a channel edited or disabled by an administrator during the scan.
   if r['status']=='unavailable':removed+=c.execute('DELETE FROM channels WHERE id=? AND url=? AND enabled=1',(r['id'],r['url'])).rowcount
   elif r['status']=='inconclusive':disabled+=c.execute('UPDATE channels SET enabled=0 WHERE id=? AND url=? AND enabled=1',(r['id'],r['url'])).rowcount
  c.execute('INSERT INTO audit(user_id,action,created) VALUES(NULL,?,?)',('channel cleanup removed='+str(removed)+' disabled='+str(disabled),int(time.time())))
 return {**counts,'removed':removed,'disabled':disabled,'backup':str(backup),'report':str(report)}

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--database',default='/var/lib/africa-media/media.db');parser.add_argument('--backup-dir',default='/var/lib/africa-media/channel-backups');parser.add_argument('--workers',type=int,default=16);parser.add_argument('--timeout',type=int,default=5);parser.add_argument('--apply',action='store_true');args=parser.parse_args()
 if not 1<=args.workers<=32 or not 1<=args.timeout<=20:parser.error('Workers must be 1–32; timeout 1–20 seconds')
 c=sqlite3.connect('file:'+str(Path(args.database).resolve())+'?mode=rw',uri=True);c.row_factory=sqlite3.Row;c.execute('PRAGMA foreign_keys=ON');channels=[dict(r) for r in c.execute('SELECT id,name,url FROM channels WHERE enabled=1')]
 results=scan(channels,args.workers,args.timeout)
 output=apply(c,results,args.backup_dir) if args.apply else {'channels':results,'dry_run':True}
 print(json.dumps(output));c.close()
if __name__=='__main__':main()
