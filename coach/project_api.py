"""Session-scoped HTTP surface; the MCP bridge cannot confirm human requirements."""
import json
import os
import re
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, ConfigDict, Field

from .project_checks import Proposal
from .projects import snapshot
from .settings import ROOT, public_model, settings


class Connect(BaseModel):
    model_config = ConfigDict(extra='forbid')
    root: str = Field(max_length=1000)
    url: str = Field(max_length=300)
    name: str = Field(default='', max_length=80)


class Prepare(BaseModel):
    goal: str = Field(min_length=3, max_length=1200)
    language: Literal['zh', 'en'] = 'zh'


class Confirm(BaseModel):
    digest: str = Field(min_length=64, max_length=64)


class Watch(BaseModel):
    enabled: bool


class ManualDraft(BaseModel):
    goal: str = Field(min_length=3, max_length=1200)
    proposal: Proposal


def router(service):
    api = APIRouter(prefix='/api/projects')

    def fail(exc): raise HTTPException(409, str(exc))

    @api.get('')
    def state(request: Request):
        owner = request.state.owner
        return {'projects': [service.public(p) for p in service.list(owner, 'project')],
                'runs': [service.public(r) for r in service.list(owner, 'run')[:30]],
                'busy': bool(service.active), 'model': public_model(), 'public': os.environ.get('APP_PUBLIC') == 'true',
                'budget': service.store.budget(), 'budget_limit_cny': settings()['budget_cny']}

    @api.post('')
    def connect(payload: Connect, request: Request):
        try: return service.public(service.connect(request.state.owner, payload.root, payload.url, payload.name))
        except (ValueError, OSError) as exc: fail(exc)

    @api.post('/sample')
    def sample(request: Request):
        port = os.environ.get('PORT', '8791')
        try:
            return service.public(service.connect(request.state.owner, ROOT / 'examples/budget',
                f'http://127.0.0.1:{port}/samples/budget/', 'Pocket Budget', sample=True))
        except (ValueError, OSError) as exc: fail(exc)

    @api.get('/runs/{run_id}')
    def run(run_id: str, request: Request):
        try: return service.public(service.get(request.state.owner, run_id, 'run'))
        except ValueError as exc: fail(exc)

    @api.post('/runs/{run_id}/cancel')
    def cancel(run_id: str, request: Request):
        try: return service.cancel(request.state.owner, run_id)
        except ValueError as exc: fail(exc)

    @api.get('/runs/{run_id}/evidence/{phase}/{filename}')
    def evidence(run_id: str, phase: str, filename: str, request: Request):
        try: service.get(request.state.owner, run_id, 'run')
        except ValueError: raise HTTPException(404)
        if phase not in {'checks', 'observe'} or not re.fullmatch(r'(page|flow-\d+)\.png', filename): raise HTTPException(404)
        target = service.store.root / 'project-artifacts' / run_id / phase / filename
        if not target.is_file(): raise HTTPException(404)
        return FileResponse(target, media_type='image/png')

    @api.get('/runs/{run_id}/report')
    def report(run_id: str, request: Request):
        try: run = service.get(request.state.owner, run_id, 'run')
        except ValueError: raise HTTPException(404)
        return Response(run.get('repair_brief', 'Still running'), media_type='text/markdown',
                        headers={'Content-Disposition': 'attachment; filename="acceptance-evidence.md"'})

    @api.get('/drafts/{draft_id}')
    def draft(draft_id: str, request: Request):
        try: return service.public(service.get(request.state.owner, draft_id, 'draft'))
        except ValueError as exc: fail(exc)

    @api.post('/drafts/{draft_id}/confirm')
    def confirm(draft_id: str, payload: Confirm, request: Request):
        try: return service.public(service.confirm(request.state.owner, draft_id, payload.digest))
        except (ValueError, OSError) as exc: fail(exc)

    @api.get('/{project_id}/requirements')
    def requirements(project_id: str, request: Request):
        try:
            p = service.get(request.state.owner, project_id, 'project')
            return service.public(service.get(request.state.owner, p['contract_id'], 'contract')) if p['contract_id'] else {'flows': []}
        except ValueError as exc: fail(exc)

    @api.post('/{project_id}/prepare')
    def prepare(project_id: str, payload: Prepare, request: Request):
        try: return service.public(service.submit(request.state.owner, project_id, 'prepare', payload.goal, payload.language))
        except (ValueError, OSError) as exc: fail(exc)

    @api.post('/{project_id}/draft')
    def manual_draft(project_id: str, payload: ManualDraft, request: Request):
        try:
            p = service.get(request.state.owner, project_id, 'project')
            if os.environ.get('APP_PUBLIC') == 'true': raise ValueError('Manual contracts are available only in the local edition')
            return service.public(service.draft(request.state.owner, project_id, payload.goal,
                payload.proposal.model_dump()['flows'], snapshot(p['root'])['hash']))
        except (ValueError, OSError) as exc: fail(exc)

    @api.post('/{project_id}/check')
    def check(project_id: str, request: Request):
        try: return service.public(service.submit(request.state.owner, project_id))
        except (ValueError, OSError) as exc: fail(exc)

    @api.post('/{project_id}/watch')
    def watch(project_id: str, payload: Watch, request: Request):
        try: return service.watch(request.state.owner, project_id, payload.enabled)
        except ValueError as exc: fail(exc)

    @api.post('/{project_id}/bridge-config')
    def bridge_config(project_id: str, request: Request):
        try:
            p = service.get(request.state.owner, project_id, 'project')
            if os.environ.get('APP_PUBLIC') == 'true': raise ValueError('Install the local edition to connect your coding AI')
            path = service.store.root / 'bridges' / (project_id + '.json')
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({'url': f'http://127.0.0.1:{os.environ.get("PORT", "8791")}',
                'project_id': project_id, 'key': p['bridge_key']}), encoding='utf-8')
            try: path.chmod(0o600)
            except OSError: pass
            import sys
            arguments = [str(ROOT / 'mcp_server.py'), '--config', str(path)]
            toml = '[mcp_servers.loopcheck]\ncommand = ' + json.dumps(sys.executable, ensure_ascii=False) + '\nargs = ' + json.dumps(arguments, ensure_ascii=False) + '\nstartup_timeout_sec = 20\ntool_timeout_sec = 60\n'
            return {'command': sys.executable, 'args': arguments, 'codex_toml': toml,
                    'note': 'Local credential file. Do not publish it. MCP cannot confirm requirements.'}
        except ValueError as exc: fail(exc)

    def bridge_auth(project_id, request):
        try: return service.bridge_owner(project_id, request.headers.get('x-loopcheck-key', ''))
        except ValueError: raise HTTPException(403, 'Invalid local bridge credential')

    @api.post('/bridge/{project_id}/prepare')
    def bridge_prepare(project_id: str, payload: Prepare, request: Request):
        owner = bridge_auth(project_id, request)
        try: return service.public(service.submit(owner, project_id, 'prepare', payload.goal, payload.language))
        except (ValueError, OSError) as exc: fail(exc)

    @api.post('/bridge/{project_id}/check')
    def bridge_check(project_id: str, request: Request):
        owner = bridge_auth(project_id, request)
        try: return service.public(service.submit(owner, project_id))
        except (ValueError, OSError) as exc: fail(exc)

    @api.get('/bridge/{project_id}/runs/{run_id}')
    def bridge_result(project_id: str, run_id: str, request: Request):
        owner = bridge_auth(project_id, request)
        try:
            r = service.get(owner, run_id, 'run')
            if r['project_id'] != project_id: raise ValueError('Run belongs to another project')
            result = service.public(r)
            result['evidence_files'] = [str((service.store.root / 'project-artifacts' / r['id'] / 'checks' / c['screenshot']).resolve())
                for c in r.get('checks', []) if c.get('screenshot') and c['status'] != 'passed']
            if r.get('draft_id'): result['draft'] = service.public(service.get(owner, r['draft_id'], 'draft'))
            return result
        except ValueError as exc: fail(exc)
    return api
