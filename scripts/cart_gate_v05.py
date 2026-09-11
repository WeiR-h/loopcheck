"""Real browser development gate, with explicitly injected feature/regression and recording."""
import functools
import http.server
import json
import os
from pathlib import Path
import shutil
import sys
import threading
import time

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
WORK=ROOT/'.test-data'/('cart-v05-'+str(time.time_ns()))
os.environ['LOOPCHECK_DATA']=str(WORK/'state')
from coach.projects import Projects, snapshot
from coach.store import Store
import coach.projects as project_module
from coach.project_browser import run_browser


def step(action, role=None, name='', value='', **kw):
    return {'action':action,'value':value,**({'target':{'by':'role','value':role,'name':name}} if role else {}),**kw}


FLOWS=[
 {'title':'Quantity and total','expectation':'Set quantity to 2: cart total is 200.00','steps':[step('fill','spinbutton','Quantity','2'),step('click','button','Update cart'),step('expect_text','status','Cart total','200.00')]},
 {'title':'Quantity validation','expectation':'Quantity 0 is rejected with a validation message','steps':[step('fill','spinbutton','Quantity','0'),step('click','button','Update cart'),step('expect_text','alert',value='Enter a quantity from 1 to 20')]},
 {'title':'Persist quantity','expectation':'Quantity 3 remains after reload, total is 300.00','steps':[step('fill','spinbutton','Quantity','3'),step('click','button','Update cart'),step('reload'),step('expect_value','spinbutton','Quantity','3'),step('expect_text','status','Cart total','300.00')]},
]
COUPON={'title':'Coupon discount','expectation':'Quantity 2 with SAVE10 costs 180.00','purpose':'new','steps':[
 step('fill','spinbutton','Quantity','2'),step('click','button','Update cart'),step('fill','textbox','Coupon','SAVE10'),step('click','button','Apply coupon'),step('expect_text','status','Cart total','180.00')]}
FEATURE='''
const couponLabel=document.createElement('label');couponLabel.textContent='Coupon';couponLabel.htmlFor='coupon';
const coupon=document.createElement('input');coupon.id='coupon';
const apply=document.createElement('button');apply.textContent='Apply coupon';
document.querySelector('main').append(couponLabel,coupon,apply);
apply.onclick=()=>{if(coupon.value==='SAVE10')total.textContent=(Number(quantity.value)*100*.9).toFixed(2);};
'''


def main():
    WORK.mkdir(parents=True);folder=WORK/'cart';shutil.copytree(ROOT/'examples/cart',folder)
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self,*args):pass
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(folder)))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    store=Store(WORK/'state');service=Projects(store);owner=store.session()
    project_module.run_browser=functools.partial(run_browser,record_video=True)
    p=service.connect(owner,folder,f'http://127.0.0.1:{server.server_port}/','Everyday Cart')
    rows=[]
    def collect(r,label):
        while service.active: time.sleep(.1)
        result=service.get(owner,r['id'],'run');rows.append({'phase':label,**service.result_view(result)})
        print(label,result['state'],flush=True);return result
    def confirm(d,label):return collect(service.confirm(owner,d['id'],d['digest']),label)
    try:
        assert confirm(service.draft(owner,p['id'],'Preserve cart behavior',FLOWS,snapshot(folder)['hash']),'baseline')['state']=='passed'
        d=service.requirement_draft(owner,p['id'],'Add SAVE10 coupon while preserving quantity, totals and persistence',
            [{'action':'add','intent':{k:COUPON[k] for k in ('title','expectation','purpose')}}],snapshot(folder)['hash'])
        assert confirm(d,'new requirement without control')['state']=='incomplete'
        source=folder/'app.js';original=source.read_text(encoding='utf-8')
        source.write_text(original.replace('count*100','count*150')+FEATURE,encoding='utf-8')
        req=service.current_requirements(owner,p['id'])[-1]
        d=service.requirement_draft(owner,p['id'],'Bind implemented coupon',
            [{'action':'bind','id':req['id'],'revision':req['revision'],'flow':COUPON}],snapshot(folder)['hash'])
        failed=confirm(d,'feature implemented, injected total regression')
        assert failed['state']=='failed' and any(c['classification']=='regression' for c in failed['checks'])
        source.write_text(original+FEATURE,encoding='utf-8')
        assert collect(service.submit(owner,p['id']),'source repaired and rechecked')['state']=='passed'
    finally:
        report={'version':'0.5.0','disclosure':'Real browser runs. Test harness approves declared requirements. Feature and regression are explicitly injected by this script; not an autonomous coding-agent success claim. Video clips record browser execution, with cuts between runs. No human efficiency measurement.',
                'runs':rows,'model_calls':store.budget()['calls'],'artifacts_directory':str(WORK/'state/project-artifacts')}
        (ROOT/'docs/evidence/v05-cart-gate.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        service.stop();server.shutdown();server.server_close()


if __name__=='__main__': main()
