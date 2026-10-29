from pathlib import Path
import os
ROOT=Path(os.environ.get('MEDIA_DOWNLOAD_DIR','/var/lib/africa-media/downloads'))
PACKAGES={'roku':('africa-media-roku.zip','Roku development channel ZIP','application/zip'),'android':('africa-media-android-debug.apk','Android / Fire TV development APK','application/vnd.android.package-archive'),'windows':('africa-media-windows.exe','Windows installer (unsigned)','application/octet-stream'),'macos':('africa-media-macos.dmg','macOS disk image (unsigned)','application/octet-stream'),'linux':('africa-media-linux.AppImage','Linux AppImage','application/octet-stream'),'samsung':('africa-media-samsung.wgt','Samsung TV package','application/widget'),'lg':('africa-media-lg.ipk','LG TV package','application/octet-stream')}
def available():
 return [{'id':key,'label':v[1],'url':'/downloads/'+key,'size':(ROOT/v[0]).stat().st_size} for key,v in PACKAGES.items() if (ROOT/v[0]).is_file() and (ROOT/v[0]).stat().st_size>0]
