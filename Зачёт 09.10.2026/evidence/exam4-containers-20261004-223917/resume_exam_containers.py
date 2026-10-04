"""Capture the existing successful Compose log without repeating Docker commands."""
from capture_stage import BASE,REPO,BrowserSession
from history_ops import git
from scripts.evidence.render import load_manifest
import hashlib
import json
import shutil

folder=REPO/'Зачёт 09.10.2026/evidence/exam4-containers-20261004-223917'
manifest=folder/'manifest.json'
data,_=load_manifest(manifest)
sha='66fb85ac2b20e20b367717e4e0ce2770cd1bbb9c'
if git('rev-parse','HEAD')!=sha or git('status','--porcelain','--untracked-files=no'):
    raise ValueError('Expected unchanged exam source commit')
if data['status']!='succeeded' or len(data['commands'])!=9:
    raise ValueError('Expected nine completed Compose commands')
for command in data['commands']:
    if command['verified_sha']!=sha or command['returncode']!=0 or command['status']!='succeeded':
        raise ValueError('Unexpected command provenance/result')
html=folder/'exam4-containers.html'
kept={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in (manifest,folder/'commands.log',html)}
shot=REPO/'Зачёт 09.10.2026/screenshots/exam4-containers.png'
result=BASE/'result-exam4-containers.json'
if result.exists():raise FileExistsError(result)
with BrowserSession(profile_root=REPO/'.verification/browser') as browser:
    browser.capture(html.as_uri(),shot,cwd=REPO)
for path,digest in kept.items():
    if hashlib.sha256(path.read_bytes()).hexdigest()!=digest:raise ValueError('Original evidence changed')
for name in ('container_checks.py','live_checks.py','resume_exam_containers.py'):
    shutil.copy2(BASE/name,folder/name)
summary={'stage':10,'sha':sha,'manifest':str(manifest.relative_to(REPO)),
         'screenshots':[str(shot.relative_to(REPO))],
         'capture_note':'Возобновлена только съёмка готового HTML после таймаута Chrome; девять Docker-команд не повторялись.'}
result.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(summary,ensure_ascii=False))
