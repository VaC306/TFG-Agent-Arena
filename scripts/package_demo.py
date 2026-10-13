"""Prepare a local static ZIP and an explicit file inventory, without Sites calls."""
import hashlib
import json
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / 'frontend/dist/sites/browser'
OUT = ROOT / 'frontend/dist'


def main():
    catalog = json.loads((BUILD / 'demo/catalog.json').read_text(encoding='utf-8'))
    selected = {'demo/catalog.json', 'demo/diagnostics.json', 'demo/manifest.json', 'demo/showcase.json', 'demo/fixtures.json', 'demo/replay.json'}
    selected |= {f'demo/exports/{e["id"]}/{f}' for e in catalog['experiments'] for f in ('metrics.csv','report.md','reproducibility.json')}
    files = []
    for path in sorted(BUILD.rglob('*')):
        if not path.is_file(): continue
        name = path.relative_to(BUILD).as_posix()
        if not (name in selected or name == 'index.html' or re.fullmatch(r'(main|styles)-[\w]+\.(js|css)',name) or name == 'assets/fonts/Manrope-LICENSE.txt' or re.fullmatch(r'media/Manrope-Variable-[\w]+\.ttf',name)):
            raise ValueError(f'Unreviewed publication file: {name}')
        if path.suffix != '.ttf':
            text = path.read_text(encoding='utf-8')
            if re.search(r'(?i)(@ucm\.es|@gmail\.com|ripursna|alramo03|password_hash|sk-[a-z0-9]{20}|C:[\\/]|/Users/|/home/)',text):
                raise ValueError(f'Private content in {name}')
        files.append((name,path.read_bytes()))
    names = {name for name,_ in files}
    assert selected <= names and 'index.html' in names
    inventory = [{'path':'dist/'+name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()} for name,raw in files]
    with zipfile.ZipFile(OUT / 'arena-demo-static.zip','w',compression=zipfile.ZIP_DEFLATED) as archive:
        for name,raw in files:
            info = zipfile.ZipInfo('dist/'+name, date_time=(2026,10,12,0,0,0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info,raw)
    (OUT / 'arena-demo-inventory.json').write_text(json.dumps(inventory,indent=2)+'\n',encoding='utf-8')
    print(f'Local static artifact: {len(files)} files, {sum(len(raw) for _,raw in files)} bytes; no Site ID, no deployment.')


if __name__ == '__main__': main()
