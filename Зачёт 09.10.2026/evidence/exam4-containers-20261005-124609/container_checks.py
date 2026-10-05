"""Bounded checks of the task-owned runtime and its synthetic JSON output."""
import argparse
import hashlib
import json
from pathlib import Path
import time
from live_checks import http_request,show_response

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['wait','save-result','check-result'])
    parser.add_argument('--url',default='http://127.0.0.1:8080')
    args=parser.parse_args()
    if args.action=='wait':
        deadline=time.monotonic()+75
        while time.monotonic()<deadline:
            try:
                response=http_request(args.url,'/health')
                data=response['json']
                if response['status']==200 and data.get('status')=='ok' and (data.get('model_ready') is True or data.get('model_loaded') is True):
                    show_response(response);return
            except OSError: pass
            time.sleep(.5)
        raise TimeoutError('API not ready after 75 seconds')
    path=Path('results/prediction.json')
    raw=path.read_bytes()
    data=json.loads(raw)
    assert data.get('class_name')=='setosa' and data.get('prediction',data.get('class_id'))==0
    digest=hashlib.sha256(raw).hexdigest()
    snapshot=Path('.verification/compose-result.sha256')
    if args.action=='save-result':
        snapshot.parent.mkdir(parents=True,exist_ok=True)
        snapshot.write_text(digest,encoding='ascii')
    else:
        assert snapshot.read_text(encoding='ascii')==digest,'Persistent result changed after compose down'
    print('results/prediction.json:',json.dumps(data,ensure_ascii=False,sort_keys=True))
    print('SHA256:',digest)
    print('Saved baseline' if args.action=='save-result' else 'Result preserved after compose down')

if __name__=='__main__': main()
