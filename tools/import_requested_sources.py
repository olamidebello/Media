"""Import requested feeds independently; report errors without removing existing rows."""
import json,sys,os,sqlite3
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from iptv import REQUESTED_SOURCES,refresh
results=[]
for key in REQUESTED_SOURCES:
 try:
  with sqlite3.connect(os.environ.get('MEDIA_DB','/var/lib/africa-media/media.db')) as c:
   result=refresh(c,key)
 except Exception as e:result={'source':key,'error':str(e)}
 results.append(result)
 print(json.dumps(result),flush=True)
if all('error' in r for r in results):raise SystemExit('All sources failed; existing channels preserved')
