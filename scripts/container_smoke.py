"""Verify a built public container at 768 MiB, without credentials or model calls."""
import json
from pathlib import Path
import subprocess
import sys
import time
import urllib.request
import urllib.error
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tests'))
from project_fixtures import BUDGET_FLOWS
NAME='loopcheck-ci'

def docker(*args,input=None):
    return subprocess.run(['docker',*args],input=input,text=True,check=True,capture_output=True).stdout

def request(path,body=None):
    data=json.dumps(body).encode() if body is not None else None
    req=urllib.request.Request('http://127.0.0.1:8794'+path,data=data,headers={'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(req,timeout=5) as r:return r.status,json.loads(r.read())
    except urllib.error.HTTPError as e:return e.code,None

def main():
    docker('run','-d','--name',NAME,'--memory','768m','--memory-swap','768m','--cpus','2','--shm-size','256m',
        '-p','127.0.0.1:8794:8765','-e','APP_PUBLIC=true','-e','DASHSCOPE_API_KEY=',
        '-v','loopcheck-ci-data:/app/data','loopcheck:ci')
    report={}
    try:
        for _ in range(60):
            try:
                status,health=request('/health')
                if status==200:break
            except (OSError,ValueError):pass
            time.sleep(.5)
        else:raise AssertionError('Container did not become healthy')
        assert health['version']=='0.5.2'
        _,state=request('/api/projects');assert state['public'] and not state['model']['configured']
        assert request('/api/projects',{'root':'/app','url':'http://127.0.0.1:8765/'})[0]==409
        assert request('/api/versions',{'expected_version':'test','action':'import','code':'alert(1)'})[0]==403
        program="import json,sys; from coach.project_browser import run_browser; print(json.dumps(run_browser('http://127.0.0.1:8765/samples/budget/',json.load(sys.stdin),'/app/data/container-check')))"
        baseline=json.loads(docker('exec','-i',NAME,'python','-c',program,input=json.dumps(BUDGET_FLOWS)))
        assert baseline['all_passed'],baseline
        mutate="from pathlib import Path; p=Path('/app/examples/budget/app.js'); s=p.read_text(); assert s.count('(i - e).toFixed(2)')==1; p.write_text(s.replace('(i - e).toFixed(2)','(i + e).toFixed(2)'))"
        docker('exec',NAME,'python','-c',mutate)
        failure=json.loads(docker('exec','-i',NAME,'python','-c',program,input=json.dumps(BUDGET_FLOWS)))
        assert failure['checks'][0]['status']=='failed' and not failure['all_passed'],failure
        restore="from pathlib import Path; p=Path('/app/examples/budget/app.js'); p.write_text(p.read_text().replace('(i + e).toFixed(2)','(i - e).toFixed(2)'))"
        docker('exec',NAME,'python','-c',restore)
        repaired=json.loads(docker('exec','-i',NAME,'python','-c',program,input=json.dumps(BUDGET_FLOWS)))
        assert repaired['all_passed'],repaired
        peak=int(docker('exec',NAME,'cat','/sys/fs/cgroup/memory.peak').strip())
        inspect=json.loads(docker('inspect',NAME))[0]
        assert not inspect['State']['OOMKilled']
        report={'version':'0.5.2','status':'passed','scope':'Fresh Linux Docker build, public-mode boundaries, three real browser flows across baseline/injected-fault/restoration',
                'memory_limit_mib':768,'peak_memory_mib':round(peak/1024/1024,2),'oom_killed':False,'model_calls':0,
                'baseline':baseline,'injected_fault':failure,'restored':repaired,
                'limitation':'Container memory measurement on a CI host; not an AWS 1 GB instance or a live-provider load test.'}
        print(json.dumps({k:v for k,v in report.items() if k not in {'baseline','injected_fault','restored'}}))
    finally:
        (ROOT/'docs/evidence/v052-container-check.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        docker('rm','-f',NAME)

if __name__=='__main__':main()
