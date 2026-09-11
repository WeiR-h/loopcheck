"""Build a source-only release and reject local credentials or workspace cookies."""
from pathlib import Path
import hashlib, json, sqlite3, zipfile
from dotenv import dotenv_values
ROOT=Path(__file__).resolve().parents[1]
patterns=['.github/workflows/*.yml','coach/*.py','web/*','examples/tasks/*','examples/budget/*','examples/cart/*','examples/public/*/*','tests/*.py','scripts/*.py','scripts/*.ps1',
          'docs/*.md','docs/evidence/*.json','docs/evidence/*.md','docs/audit-v1/*.png','docs/audit-v04/*.png','docs/video/*.json','docs/video/*.webm']
names=['README.md','README.en.md','CHANGELOG.md','LICENSE','requirements.txt','Dockerfile','compose.yaml',
       'run.py','mcp_server.py','install.ps1','启动应用.cmd','.env.example','.gitignore','.gitattributes','.dockerignore']
files={ROOT/n for n in names}
for pattern in patterns: files.update(ROOT.glob(pattern))
files={p for p in files if p.is_file() and p.name not in {'source-manifest.json','一等奖竞争力复审-2026-09-10.md'}}
private=[str(v).encode() for k,v in dotenv_values(ROOT/'.env',interpolate=False).items()
         if v and ('KEY' in k or 'TOKEN' in k) and len(str(v))>=16 and not str(v).startswith('PASTE_')]
dbpath=ROOT/'data/app/loopcheck.sqlite3'
if dbpath.exists():
    with sqlite3.connect(dbpath) as db:
        private += [row[0].encode() for row in db.execute('SELECT id FROM sessions')]
for folder in [ROOT/'data/app/bridges']:
    for file in folder.glob('*.json'):
        key=json.loads(file.read_text(encoding='utf-8')).get('key')
        if key: private.append(key.encode())
manifest={}
for p in sorted(files):
    data=p.read_bytes()
    if any(secret in data for secret in private):
        raise SystemExit('Private data detected in '+p.relative_to(ROOT).as_posix())
    manifest[p.relative_to(ROOT).as_posix()]=hashlib.sha256(data).hexdigest()
path=ROOT/'docs/evidence/source-manifest.json'
path.write_text(json.dumps({'version':'0.5.0','files':manifest},indent=2,ensure_ascii=False),encoding='utf-8')
files.add(path)
(ROOT/'dist').mkdir(exist_ok=True)
archive=ROOT/'dist/loopcheck-v0.5.0-source.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
    for p in sorted(files): z.write(p,p.relative_to(ROOT).as_posix())
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    assert '.env' not in z.namelist() and not any(n.startswith(('data/','.venv/','.browsers/')) for n in z.namelist())
checksum=hashlib.sha256(archive.read_bytes()).hexdigest()
(ROOT/'dist/SHA256SUMS.txt').write_text(checksum+'  '+archive.name+'\n',encoding='utf-8')
print(json.dumps({'archive':archive.name,'files':len(files),'bytes':archive.stat().st_size,'sha256':checksum,'private_values_found':0}))

