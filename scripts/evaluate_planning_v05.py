"""Four frozen live-agent goals. All attempts retained; no reference checks reach the model."""
import functools
import hashlib
import http.server
import json
import os
from pathlib import Path
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
WORK = ROOT / '.test-data' / ('planning-v05-' + str(time.time_ns()))
os.environ['LOOPCHECK_DATA'] = str(WORK / 'state')
from coach.projects import Projects
from coach.store import Store

GOALS = [
    {'id':'shopping-add', 'fixture':'shopping', 'goal':'Add Milk to the shopping list. The list must contain Milk and the new item input must be empty after adding.', 'reference':['Milk appears as list item', 'input is empty']},
    {'id':'shopping-delete', 'fixture':'shopping', 'goal':'Add Milk, then delete that item. The shopping list must be empty afterwards.', 'reference':['add Milk first','delete item','empty list']},
    {'id':'dialog-cancel', 'fixture':'dialog', 'goal':'Open Update details. The dialog must be visible. Click Cancel. The dialog must be hidden.', 'reference':['dialog visible after opening','hidden after Cancel']},
    {'id':'dialog-confirm', 'fixture':'dialog', 'goal':'Open Update details. Select Red panda as Favorite animal and verify the selected value. Click Confirm. The dialog must close.', 'reference':['open dialog','select and verify Red panda','closed after Confirm']},
]


def wait(service, owner, run):
    deadline = time.monotonic() + 480
    while service.active and time.monotonic() < deadline: time.sleep(.1)
    if service.active:
        service.cancel(owner, run['id'])
        raise TimeoutError('Planning evaluation timeout')
    return service.get(owner, run['id'], 'run')


def main():
    WORK.mkdir(parents=True)
    frozen={'created':time.time(),'goals':GOALS,'planner_sha256':hashlib.sha256((ROOT/'coach/requirements.py').read_bytes()).hexdigest(),
            'fixtures':{name:hashlib.sha256((ROOT/f'examples/public/{name}/index.html').read_bytes()).hexdigest() for name in ['shopping','dialog']},
            'disclosure':'Reference outcomes stay in evaluator; model receives only the natural language goal and live page. Test harness confirms drafts to exercise execution; this is not human usability evidence.'}
    suffix = '-retry4' if '--retry4' in sys.argv else '-retry3' if '--retry3' in sys.argv else '-retry2' if '--retry2' in sys.argv else '-retry1' if '--retry1' in sys.argv else ''
    version = '0.5.2' if '--v052' in sys.argv else '0.5.0'
    prefix = 'v052' if '--v052' in sys.argv else 'v05'
    manifest=ROOT/('docs/evidence/'+prefix+'-planning-frozen'+suffix+'.json')
    if manifest.exists(): raise ValueError('Frozen evaluation exists; do not silently overwrite it')
    manifest.write_text(json.dumps(frozen,indent=2),encoding='utf-8')
    store=Store(WORK/'state');service=Projects(store);rows=[]
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self,*args): pass
    report={'version':version,'frozen_sha256':hashlib.sha256(manifest.read_bytes()).hexdigest(),'work_directory':WORK.relative_to(ROOT).as_posix(),
            'disclosure':frozen['disclosure'],'human_efficiency':'Not measured','goals':rows}
    path=ROOT/('docs/evidence/'+prefix+'-planning-results'+suffix+'.json')
    try:
        for case in GOALS:
            server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(ROOT/'examples/public'/case['fixture'])))
            threading.Thread(target=server.serve_forever,daemon=True).start()
            owner=store.session();p=service.connect(owner,ROOT/'examples/public'/case['fixture'],f'http://127.0.0.1:{server.server_port}/')
            row={'id':case['id'],'runs':[],'status':'incomplete'};rows.append(row)
            try:
                intent=wait(service,owner,service.submit(owner,p['id'],'prepare',case['goal'],'en'))
                row['runs'].append(service.public(intent))
                if intent.get('draft_id'):
                    d=service.get(owner,intent['draft_id'],'draft');row['intent_draft']=service.public(d)
                    row['runs'].append(service.public(wait(service,owner,service.confirm(owner,d['id'],d['digest']))))
                    binding=wait(service,owner,service.submit(owner,p['id'],'prepare',case['goal'],'en',stage='bind'))
                    row['runs'].append(service.public(binding))
                    if binding.get('draft_id'):
                        d=service.get(owner,binding['draft_id'],'draft');row['binding_draft']=service.public(d)
                        result=wait(service,owner,service.confirm(owner,d['id'],d['digest']))
                        row['runs'].append(service.result_view(result));row['status']=result['state']
                row['usage']=store.budget()
            except Exception as exc: row['error']=str(exc)
            finally:
                server.shutdown();server.server_close()
                report['total_usage']=store.budget()
                path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
                print(case['id'],row['status'],flush=True)
    finally: service.stop()
    print(json.dumps(report['total_usage']))


if __name__=='__main__': main()
