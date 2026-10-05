"""Extract actually printed delivery and rollback commands from a dry-run job."""
from history_ops import GH,command
import argparse
from pathlib import Path
import re

def main():
    p=argparse.ArgumentParser();p.add_argument('--run-id',type=int,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    raw=command([GH,'run','view',str(a.run_id),'--repo','Kirill-Erofeev/development-and-integration-labs','--log']).stdout
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('xb') as f:f.write(raw)
    lines=raw.decode('utf-8').splitlines()
    print('Учебная доставка: команды ниже действительно напечатаны workflow, но не исполнялись на сервере.')
    print('Run:',a.run_id)
    for step in ('Print deploy commands','Print smoke test commands','Print rollback commands'):
        matches=[]
        for line in lines:
            if '\t'+step+'\t' not in line:continue
            value=line.split('\t',2)[-1]
            value=re.sub(r'^\S+\s+','',value,count=1)
            if value.startswith(('docker ','curl ','Dry run:')): matches.append(value)
        if not matches: raise ValueError('Missing real printed commands: '+step)
        print('\n'+step+':')
        print('\n'.join(matches))
    print('\nПолный журнал:',a.output)

if __name__=='__main__':main()
