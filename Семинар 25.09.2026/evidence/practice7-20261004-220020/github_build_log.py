"""Show labelled excerpts from an actual, completed GitHub Actions run."""
from history_ops import GH,command
import argparse
import re
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('--run-id',type=int,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    result=command([GH,'run','view',str(args.run_id),'--repo','Kirill-Erofeev/development-and-integration-labs','--log'])
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('xb') as stream: stream.write(result.stdout)
    lines=result.stdout.decode('utf-8').splitlines()
    print('GitHub Actions run:',args.run_id)
    print('Полный журнал сохранён:',args.output)
    for step in ('Run all tests','Build API image','Build client image'):
        selected=[line for line in lines if '\t'+step+'\t' in line]
        if not selected: raise ValueError('Missing executed step '+step)
        if step=='Run all tests':
            excerpt=[line for line in selected if re.search(r'\d+ passed',line)]
            if not excerpt: raise ValueError('Missing passed pytest summary')
        else:
            needle='ml-api:test-' if step=='Build API image' else 'ml-client:test-'
            excerpt=[line for line in selected if needle in line and ('naming to' in line or 'tagging to' in line)]
            if not excerpt: raise ValueError('Missing tagged Docker build output '+needle)
            excerpt+=selected[-2:]
        print('\n'+step+' — выборка из '+str(len(selected))+' строк:')
        for line in excerpt:
            print(line.split('\t',2)[-1])

if __name__=='__main__':main()
