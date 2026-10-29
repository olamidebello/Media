"""Build a Roku development sideload ZIP, with manifest at archive root."""
from pathlib import Path
import zipfile
root = Path(__file__).resolve().parents[1]
source = root / 'apps/roku'
output = root / 'packages/africa-media-roku.zip'
output.parent.mkdir(exist_ok=True)
with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
    for file in sorted(source.rglob('*')):
        if file.is_file():
            archive.write(file, file.relative_to(source).as_posix())
with zipfile.ZipFile(output) as archive:
    assert 'manifest' in archive.namelist()
    assert archive.testzip() is None
print(output)
