"""Restore thumbnail metadata from bundled playlists without changing channel visibility."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import app,artwork
from iptv import parse
with app.db() as c:
    artwork.init(c)
    updated=0
    for source in sorted((app.ROOT/'data').glob('*.m3u')):
        for item in parse(source.read_text(encoding='utf-8-sig'))[0]:
            if item.get('thumbnail'):
                updated+=c.execute("UPDATE channels SET thumbnail=? WHERE url=? AND thumbnail=''",(item['thumbnail'],item['url'])).rowcount
print('Channel artwork updated: '+str(updated))
