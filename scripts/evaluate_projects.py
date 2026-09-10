"""Frozen, disclosed mutation benchmark. No model sees mutations or reference patches."""
import functools
import hashlib
import http.server
import json
from pathlib import Path
import shutil
import sys
import threading
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / 'tests'))
from project_fixtures import BUDGET_FLOWS, label, button, step
from coach.project_browser import run_browser

COMMIT = 'ff43b02e59dfa604386bb382034b2cd07c2bcd8a'
SAMPLE_GOAL = '保留三项行为：收入 1200 减去支出 350，余额为 850.00；输入负数时显示校验错误；保存收入 2300 和支出 150 后，刷新页面仍保留数据。'
REACT_FLOWS = [
    {'title':'Create a named todo','expectation':'Adding Alpha displays Alpha', 'steps':[
        step('fill',label('New Todo Input'),value='Alpha'),step('press',label('New Todo Input'),value='Enter'),
        step('expect_text',{'by':'text','value':'Alpha'},value='Alpha')]},
    {'title':'Delete the created todo','expectation':'Deleting Alpha removes it from the list', 'steps':[
        step('fill',label('New Todo Input'),value='Alpha'),step('press',label('New Todo Input'),value='Enter'),
        step('hover',{'by':'text','value':'Alpha'}),step('click',button('Delete todo')),
        step('expect_count',{'by':'text','value':'Alpha'},count=0)]}
]
SELF_FLOWS = [
    {'title':'Switch the workspace language','expectation':'English toggles the main heading into English','steps':[
        step('click',button('English')),step('expect_text',{'by':'role','value':'heading','name':'Keep every change honest.'},value='Keep every change honest.')]},
    {'title':'Start with an actionable example','expectation':'The sample connects and pre-fills a concrete change goal','steps':[
        step('click',button('先试试：预算计算器 →')),step('expect_value',label('这次想改什么，哪些行为必须保留？'),value=SAMPLE_GOAL)]}
]
CASES = [
    {'app':'budget','id':'B1','kind':'fault','file':'app.js','old':'(i - e).toFixed(2)','new':'(i + e).toFixed(2)'},
    {'app':'budget','id':'B2','kind':'fault','file':'app.js','old':'!income.value || !expense.value || !Number.isFinite(i) || !Number.isFinite(e) || i < 0 || e < 0','new':'false'},
    {'app':'budget','id':'B3','kind':'feature','file':'index.html','old':'</select>','new':'<option value="books">Books</option></select>'},
    {'app':'budget','id':'B4','kind':'cosmetic','file':'style.css','old':'background:#edf5f1','new':'background:#f1f4fb'},
    {'app':'react','id':'R1','kind':'fault','file':'app.bundle.js','old':'case _t:return e.concat({id:$t(),title:t.payload.title,completed:!1});','new':'case _t:return e.concat({id:$t(),title:"Wrong item",completed:!1});'},
    {'app':'react','id':'R2','kind':'fault','file':'app.bundle.js','old':'case Tt:return e.filter(e=>e.id!==t.payload.id);','new':'case Tt:return e;'},
    {'app':'react','id':'R3','kind':'feature','file':'index.html','old':'</footer>','new':'<p>Tip: use Enter to add an item.</p></footer>'},
    {'app':'react','id':'R4','kind':'cosmetic','file':'index.html','old':'</head>','new':'<style>body{background:#f1f4fb}</style></head>'},
    {'app':'loopcheck','id':'L1','kind':'fault','file':'projects.js','old':"language=language==='zh'?'en':'zh'",'new':"language='zh'"},
    {'app':'loopcheck','id':'L2','kind':'fault','file':'projects.js','old':"$('goal').value=t('sampleGoal')",'new':"$('goal').value=''"},
    {'app':'loopcheck','id':'L3','kind':'feature','file':'projects.html','old':'<footer>','new':'<p>Local projects remain on your computer.</p><footer>'},
    {'app':'loopcheck','id':'L4','kind':'cosmetic','file':'projects.css','old':'background:#f5f6f2','new':'background:#f2f5f8'},
]


class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args): pass
    def proxy(self):
        data = self.rfile.read(int(self.headers.get('Content-Length',0))) if self.command == 'POST' else None
        req = urllib.request.Request('http://127.0.0.1:8791' + self.path, data=data,
            headers={k:self.headers[k] for k in ['Cookie','Content-Type'] if self.headers.get(k)}, method=self.command)
        try: response = urllib.request.urlopen(req, timeout=15)
        except urllib.error.HTTPError as exc: response = exc
        self.send_response(response.status)
        for k in ['Content-Type','Set-Cookie']:
            if response.headers.get(k): self.send_header(k,response.headers[k])
        self.end_headers(); self.wfile.write(response.read())
    def do_POST(self): self.proxy()
    def do_GET(self):
        if self.path.startswith('/api/'): return self.proxy()
        if self.path.startswith('/static/'): self.path = '/' + self.path.split('/static/',1)[1]
        if self.path == '/': self.path = '/projects.html' if (Path(self.directory)/'projects.html').exists() else '/index.html'
        super().do_GET()


def main():
    import httpx
    source = ROOT / '.test-data/todomvc-react'
    source.mkdir(parents=True, exist_ok=True)
    with httpx.Client(timeout=30, trust_env=False) as c:
        for name in ['app.bundle.js','app.bundle.js.LICENSE.txt','app.css','base.js','index.html','license.md']:
            if not (source/name).exists():
                path = 'license.md' if name=='license.md' else 'examples/react/dist/' + name
                (source/name).write_bytes(c.get(f'https://raw.githubusercontent.com/tastejs/todomvc/{COMMIT}/{path}').raise_for_status().content)
    work = ROOT / '.test-data' / ('evaluation-' + str(int(time.time())))
    work.mkdir()
    specs = {'budget':BUDGET_FLOWS,'react':REACT_FLOWS,'loopcheck':SELF_FLOWS}
    bases = {'budget':ROOT/'examples/budget','react':source,'loopcheck':ROOT/'web'}
    frozen = {'created':time.time(),'public_react_commit':COMMIT,'disclosure':'Artificial mutations; developer-defined (AI-assisted) frozen acceptance flows; no model calls. LoopCheck frontend uses its running backend through a local proxy.',
              'cases':CASES,'flows':specs,'source_hashes':{}}
    for app, path in bases.items():
        frozen['source_hashes'][app] = {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in path.iterdir() if p.is_file()}
    manifest = ROOT/'docs/evidence/v04-frozen-cases.json'
    manifest.write_text(json.dumps(frozen,ensure_ascii=False,indent=2),encoding='utf-8')
    rows, baseline = [], []
    for app, base in bases.items():
        project = work/app
        shutil.copytree(base,project)
        server = http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Handler,directory=str(project)))
        threading.Thread(target=server.serve_forever,daemon=True).start()
        url = f'http://127.0.0.1:{server.server_port}/'
        try:
            result = run_browser(url,specs[app],work/(app+'-baseline'))
            baseline.append({'app':app,**result})
            if not result['all_passed']:
                (work/'baseline-failure.json').write_text(json.dumps(baseline,indent=2),encoding='utf-8')
                raise AssertionError('Baseline failed: '+app+'; see '+str(work/'baseline-failure.json'))
            for case in [c for c in CASES if c['app']==app]:
                file = project/case['file']; original=file.read_text(encoding='utf-8')
                assert original.count(case['old'])==1, case['id']
                file.write_text(original.replace(case['old'],case['new'],1),encoding='utf-8')
                result=run_browser(url,specs[app],work/case['id'])
                detected=any(c['status']=='failed' for c in result['checks'])
                rows.append({'id':case['id'],'app':app,'kind':case['kind'],'detected_failure':detected,
                             'expected_outcome_met':detected if case['kind']=='fault' else result['all_passed'],**result})
                file.write_text(original,encoding='utf-8')
                print(case['id'],rows[-1]['expected_outcome_met'],flush=True)
        finally: server.shutdown();server.server_close()
    report={'version':'0.4.0','frozen_manifest_sha256':hashlib.sha256(manifest.read_bytes()).hexdigest(),
            'disclosure':frozen['disclosure'],'public_react_commit':COMMIT,'baseline':baseline,'cases':rows,
            'expected_outcomes_met':sum(r['expected_outcome_met'] for r in rows),'case_count':len(rows),
            'false_green_faults':sum(r['all_passed'] for r in rows if r['kind']=='fault'),
            'false_alarms':sum(not r['all_passed'] for r in rows if r['kind']!='fault'),'model_calls':0,
            'human_efficiency':'NOT MEASURED. Automated duration is not human time saved.'}
    (ROOT/'docs/evidence/v04-benchmark.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in {'baseline','cases'}},ensure_ascii=True))

if __name__=='__main__': main()
