"""Actual MCP stdio check against an isolated copy of the cart gate evidence."""
import asyncio
import functools
import http.server
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import threading
import time
import httpx
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
WORK=ROOT/'.test-data'/('mcp-v05-'+str(time.time_ns()))
os.environ['LOOPCHECK_DATA']=str(WORK/'state')
from coach.projects import Projects
from coach.store import Store


async def main():
    gate=json.loads((ROOT/'docs/evidence/v05-cart-gate.json').read_text(encoding='utf-8'))
    original=Path(gate['artifacts_directory']).parent
    shutil.copytree(original,WORK/'state')
    store=Store(WORK/'state');service=Projects(store)
    with store.db() as db: project=json.loads(db.execute("SELECT payload FROM project_records WHERE kind='project'").fetchone()['payload'])
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self,*args):pass
    preview=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=project['root']))
    threading.Thread(target=preview.serve_forever,daemon=True).start()
    project['url']=f'http://127.0.0.1:{preview.server_port}/';service.save('project',project);service.stop()
    with socket.socket() as sock: sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    env={**os.environ,'PORT':str(port),'PYTHONUTF8':'1'}
    log=(WORK/'server.log').open('w',encoding='utf-8')
    process=subprocess.Popen([sys.executable,'run.py'],cwd=ROOT,env=env,stdout=log,stderr=log,
                             creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
    config=WORK/'bridge.json';config.write_text(json.dumps({'url':f'http://127.0.0.1:{port}','project_id':project['id'],'key':project['bridge_key']}),encoding='utf-8')
    try:
        with httpx.Client(trust_env=False,timeout=2) as client:
            for _ in range(80):
                try:
                    if client.get(f'http://127.0.0.1:{port}/health').status_code==200:break
                except httpx.HTTPError: pass
                await asyncio.sleep(.25)
            else:raise RuntimeError('Isolated service did not start')
        params=StdioServerParameters(command=sys.executable,args=[str(ROOT/'mcp_server.py'),'--config',str(config)])
        async with stdio_client(params) as (read,write), ClientSession(read,write) as session:
            await session.initialize();names=sorted(t.name for t in (await session.list_tools()).tools)
            assert names==['check_change','get_result','prepare_change']
            async def call(name,args):
                r=await session.call_tool(name,args)
                assert not r.isError,str(r.content)
                return r.structuredContent or json.loads(r.content[0].text)
            historical=await call('get_result',{'run_id':gate['runs'][0]['id']})
            assert not historical['can_accept']
            failed=await call('get_result',{'run_id':gate['runs'][2]['id']})
            assert failed['state']=='failed' and failed['checks'][0]['steps'] and failed['evidence_files']
            result=await call('check_change',{})
            for _ in range(15):
                result=await call('get_result',{'run_id':result['id'],'wait_seconds':20})
                if result['state'] not in {'queued','running'}:break
            assert result['can_accept'] and result['coverage']['passed']==4,result
            report={'version':'0.5.0','transport':'actual MCP stdio client/server','tools':names,
                    'historical_can_accept':historical['can_accept'],'failure_evidence':failed,'latest_result':result,
                    'disclosure':'Isolated copy of the scripted real-browser cart gate; no model call. Does not claim a running editor auto-loaded this server.'}
            (ROOT/'docs/evidence/v05-mcp.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
            print('Actual MCP: historical approval rejected, complete failure evidence returned, four current checks passed')
    finally:
        process.terminate();process.wait(timeout=15);log.close();preview.shutdown();preview.server_close()


if __name__=='__main__':asyncio.run(main())
