"""Exercise the actual stdio MCP transport; never print the local credential."""
import argparse
import asyncio
import json
from pathlib import Path
import sys
import time
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]

async def main(args):
    params = StdioServerParameters(command=sys.executable, args=[str(ROOT/'mcp_server.py'),'--config',str(Path(args.config).resolve())])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            names = [t.name for t in tools.tools]
            assert sorted(names) == ['check_change','get_result','prepare_change']
            result = await session.call_tool(args.tool, json.loads(args.arguments))
            def unpack(r):
                if r.isError: raise RuntimeError(str(r.content))
                return r.structuredContent or json.loads(r.content[0].text)
            value = unpack(result)
            deadline = time.monotonic()+150
            while args.wait and value.get('state') in {'queued','running'} and time.monotonic()<deadline:
                value = unpack(await session.call_tool('get_result',{'run_id':value['id'],'wait_seconds':20}))
            if args.output:
                Path(args.output).write_text(json.dumps({'tools':names,'result':value},ensure_ascii=False,indent=2),encoding='utf-8')
            if args.brief: print(value.get('repair_brief',''))
            else: print(json.dumps({'tools':names,'state':value.get('state'),'run_id':value.get('id'),'checks':len(value.get('checks',[])),'error':value.get('error')},ensure_ascii=True))

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--config',required=True)
    parser.add_argument('--tool',choices=['prepare_change','check_change','get_result'],default='check_change')
    parser.add_argument('--arguments',default='{}')
    parser.add_argument('--wait',action='store_true')
    parser.add_argument('--brief',action='store_true')
    parser.add_argument('--output')
    asyncio.run(main(parser.parse_args()))
