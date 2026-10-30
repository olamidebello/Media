"""Search online for missing channel artwork, retaining source/credit/license and lookup outcomes."""
import argparse,json,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import app,artwork
from online_artwork import lookup
p=argparse.ArgumentParser();p.add_argument('--limit',type=int,default=200);p.add_argument('--max-seconds',type=int,default=300);a=p.parse_args()
if not 1<=a.limit<=5000 or not 1<=a.max_seconds<=3600:p.error('Use a limit of 1–5000 and a time budget of 1–3600 seconds')
started=time.monotonic();matched=missing=errors=processed=0
with app.db() as c:
 artwork.init(c)
 rows=c.execute("SELECT id,name FROM channels WHERE enabled=1 AND thumbnail='' AND artwork_checked<? ORDER BY artwork_checked,id LIMIT ?",(int(time.time())-30*86400,a.limit)).fetchall()
 c.commit()
 for row in rows:
  if time.monotonic()-started>=a.max_seconds:break
  try:
   result=lookup(row['name'])
   if result:
    c.execute("UPDATE channels SET thumbnail=?,thumbnail_source=?,thumbnail_credit=?,thumbnail_license=?,artwork_checked=? WHERE id=? AND thumbnail=''",(result['url'],result['source'],result['credit'],result['license'],int(time.time()),row['id']));matched+=1
   else:
    c.execute('UPDATE channels SET artwork_checked=? WHERE id=?',(int(time.time()),row['id']));missing+=1
   c.commit()
  except Exception:errors+=1
  processed+=1;time.sleep(.3)
 remaining=c.execute("SELECT count(*) FROM channels WHERE enabled=1 AND thumbnail='' AND artwork_checked<?",(int(time.time())-30*86400,)).fetchone()[0]
print(json.dumps({'processed':processed,'matched':matched,'no_suitable_match':missing,'search_errors':errors,'remaining_unsearched':remaining,'fallback':'Unique name/category/description-based generated channel covers'}))
