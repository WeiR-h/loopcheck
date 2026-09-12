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
    stage: Literal['intent', 'bind'] = 'intent'
    requirement_ids: list[str] = Field(default_factory=list, max_length=10)


class Confirm(BaseModel):
    digest: str = Field(min_length=64, max_length=64)


class Watch(BaseModel):
    enabled: bool


class RequirementDraft(BaseModel):
    goal: str = Field(min_length=3, max_length=1200)
    operations: list[dict] = Field(min_length=1, max_length=20)
    parent: str | None = None
    source_hash: str = Field(min_length=64, max_length=64)


class ManualDraft(BaseModel):
    goal: str = Field(min_length=3, max_length=1200)
    proposal: Proposal


class DemoAction(BaseModel):
    model_config = ConfigDict(extra='forbid')
    action: Literal['future', 'feature', 'repair']
    source_hash: str = Field(min_length=64, max_length=64)
    contract_id: str | None = None


def router(service):
    api = APIRouter(prefix='/api/projects')

    def fail(exc): raise HTTPException(409, str(exc))

    def source_hash(p):
        try: return snapshot(p['root'])['hash']
        except (OSError, ValueError): return None

    @api.get('/{project_id}/readiness')
    def readiness(project_id: str, request: Request):
        from .readiness import inspect
        try: return inspect(service, request.state.owner, project_id)
        except (ValueError, OSError) as exc: fail(exc)

    @api.post('/guided-demo')
    def guided_start(request: Request):
        from .guided_demo import start
        try: return start(service, request.state.owner)
        except (ValueError, OSError) as exc: fail(exc)

    @api.post('/{project_id}/guided-demo')
    def guided_advance(project_id: str, payload: DemoAction, request: Request):
        from .guided_demo import advance
        try: return advance(service, request.state.owner, project_id, payload.action, payload.source_hash, payload.contract_id)
        except (ValueError, OSError) as exc: fail(exc)

    @api.get('')
    def state(request: Request):
        owner = request.state.owner
        projects = service.list(owner, 'project')
        runs = service.list(owner, 'run')
        contexts = {p['id']: {'project': p, 'source_hash': source_hash(p),
                    'latest_activity': next((r['id'] for r in runs if r['project_id']==p['id']), None),
                    'latest_check': next((r['id'] for r in runs if r['project_id']==p['id'] and r['mode']=='check'), None)} for p in projects}
        from .readiness import preview_link
        public = os.environ.get('APP_PUBLIC') == 'true'
        return {'projects': [{**service.public(p), 'preview_url': preview_link(p, public), 'current_source_hash': contexts[p['id']]['source_hash']} for p in projects],
                'runs': [service.result_view(r, contexts[r['project_id']]) for r in runs[:30]],
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
        try: return service.result_view(service.get(request.state.owner, run_id, 'run'))
        except ValueError as exc: fail(exc)

    @api.post('/sample/cart')
    def cart_sample(request: Request):
        port = os.environ.get('PORT', '8791')
        try:
            return service.public(service.connect(request.state.owner, ROOT / 'examples/cart',
                f'http://127.0.0.1:{port}/samples/cart/', 'Everyday Cart', sample=True))
        except (ValueError, OSError) as exc: fail(exc)

    @api.post('/sample/public/{name}')
    def public_sample(name: str, request: Request):
        names = {'shopping': 'MDN Shopping List', 'dialog': 'MDN Dialog'}
        if name not in names: raise HTTPException(404)
        port = os.environ.get('PORT', '8791')
        try:
            return service.public(service.connect(request.state.owner, ROOT / 'examples/public' / name,
                f'http://127.0.0.1:{port}/samples/public/{name}/', names[name], sample=True))
        except (ValueError, OSError) as exc: fail(exc)

    @api.post('/runs/{run_id}/cancel')
    def cancel(run_id: str, request: Request):
        try: return service.cancel(request.state.owner, run_id)
        except ValueError as exc: fail(exc)

    @api.get('/runs/{run_id}/evidence/{phase}/{filename}')
    def evidence(run_id: str, phase: str, filename: str, request: Request):
        try: service.get(request.state.owner, run_id, 'run')
        except ValueError: raise HTTPException(404)
        if not re.fullmatch(r'checks|observe(?:-[1-3])?', phase) or not re.fullmatch(r'(page|flow-\d+)\.png', filename): raise HTTPException(404)
        target = service.store.root / 'project-artifacts' / run_id / phase / filename
        if not target.is_file(): raise HTTPException(404)
        return FileResponse(target, media_type='image/png')

    @api.get('/runs/{run_id}/report')
    def report(run_id: str, request: Request):
        try: run = service.get(request.state.owner, run_id, 'run')
        except ValueError: raise HTTPException(404)
        return Response(service.result_view(run)['repair_brief'], media_type='text/markdown',
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
        try: return service.public(service.submit(request.state.owner, project_id, 'prepare', payload.goal, payload.language, stage=payload.stage, requirement_ids=payload.requirement_ids))
        except (ValueError, OSError) as exc: fail(exc)

    @api.post('/{project_id}/requirement-draft')
    def requirement_draft(project_id: str, payload: RequirementDraft, request: Request):
        try:
            if any(o.get('action') == 'bind' for o in payload.operations) and os.environ.get('APP_PUBLIC') == 'true':
                raise ValueError('Manual browser bindings are local-only')
            p = service.get(request.state.owner, project_id, 'project')
            if snapshot(p['root'])['hash'] != payload.source_hash: raise ValueError('Source changed; refresh and review again')
            return service.public(service.requirement_draft(request.state.owner, project_id, payload.goal,
                payload.operations, payload.source_hash, payload.parent, check_parent=True))
        except (ValueError, OSError, KeyError, TypeError) as exc: fail(exc)

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
        try: return service.public(service.submit(owner, project_id, 'prepare', payload.goal, payload.language, stage=payload.stage, requirement_ids=payload.requirement_ids))
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
            result = service.result_view(r)
            result['evidence_files'] = [str((service.store.root / 'project-artifacts' / r['id'] / 'checks' / c['screenshot']).resolve())
                for c in r.get('checks', []) if c.get('screenshot') and c['status'] != 'passed']
            if r.get('draft_id'): result['draft'] = service.public(service.get(owner, r['draft_id'], 'draft'))
            return result
        except ValueError as exc: fail(exc)
    return api
