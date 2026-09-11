from contextlib import asynccontextmanager
import csv
import io
import json
import re
import os
from urllib.parse import urlparse
from typing import Literal

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, ConfigDict, Field

from .engine import Engine
from .settings import ROOT, FIXTURES, public_model, settings
from .store import Store
from .guard import Guard
from .scenarios import SCENARIOS, scenario_code
from .reports import report_markdown, project_zip
from .projects import Projects
from .project_api import router as project_router

store = Store()
engine = Engine(store)
guard = Guard(store, engine)
projects = Projects(store)


@asynccontextmanager
async def lifespan(app):
    guard.start()
    projects.start()
    yield
    guard.stop()
    projects.stop()
    engine.pool.shutdown(wait=False, cancel_futures=True)


app = FastAPI(title='LoopCheck', docs_url=None, redoc_url=None, lifespan=lifespan)
allowed_hosts = ['localhost', '127.0.0.1'] + [h.strip() for h in os.environ.get('APP_ALLOWED_HOSTS', '').split(',') if h.strip()]
if os.environ.get('RENDER_EXTERNAL_HOSTNAME'):
    allowed_hosts.append(os.environ['RENDER_EXTERNAL_HOSTNAME'])
app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)


@app.middleware('http')
async def isolation(request: Request, call_next):
    if request.method not in ('GET', 'HEAD', 'OPTIONS'):
        if request.headers.get('sec-fetch-site') == 'cross-site':
            return Response('Cross-site request rejected', status_code=403)
        origin = request.headers.get('origin')
        if origin and urlparse(origin).netloc != request.headers.get('host'):
            return Response('Origin rejected', status_code=403)
        try:
            if int(request.headers.get('content-length', '0')) > 30_000:
                return Response('Request too large', status_code=413)
        except ValueError:
            return Response('Invalid length', status_code=400)
        chunks, size = [], 0
        async for chunk in request.stream():
            size += len(chunk)
            if size > 30_000:
                return Response('Request too large', status_code=413)
            chunks.append(chunk)
        request._body = b''.join(chunks)
    owner = store.session(request.cookies.get('loopcheck_session'))
    request.state.owner = owner
    response = await call_next(request)
    if owner != request.cookies.get('loopcheck_session'):
        response.set_cookie('loopcheck_session', owner, httponly=True, samesite='strict',
                            secure=request.url.scheme == 'https', max_age=60 * 60 * 24 * 40)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'"
    if request.url.path.startswith('/api/'):
        response.headers['Cache-Control'] = 'no-store'
    elif request.url.path in ('/', '/judge') or request.url.path.startswith('/static/'):
        response.headers['Cache-Control'] = 'no-cache'
    return response


def clean_run(run):
    return {k: v for k, v in run.items() if k not in {'owner', 'candidate_code'}}


def bad_request(exc):
    raise HTTPException(status_code=409, detail=str(exc))


class RunInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    mode: Literal['diagnose', 'repair', 'recheck']
    symptom: str = Field(default='', max_length=1200)
    expected_version: str
    language: Literal['zh', 'en'] = 'zh'


class AdoptInput(BaseModel):
    expected_version: str


class VersionInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    expected_version: str
    action: Literal['regression', 'switch', 'import', 'scenario']
    scenario_id: str = ''
    language: Literal['zh', 'en'] = 'zh'
    version_id: str = ''
    code: str = Field(default='', max_length=16_000)
    name: str = Field(default='导入的 app.js', max_length=100)


class TimingInput(BaseModel):
    human_seconds: float = Field(ge=0, le=86_400)
    note: str = Field(default='', max_length=500)
    baseline_seconds: float | None = Field(default=None, ge=0, le=86400)


class GuardInput(BaseModel):
    enabled: bool
    auto_repair: bool = False
    language: Literal['zh', 'en'] = 'zh'


class GuardChangeInput(BaseModel):
    scenario_id: str


@app.get('/')
@app.get('/judge')
def index():
    return FileResponse(ROOT / 'web' / 'projects.html')


@app.get('/legacy')
def legacy():
    return FileResponse(ROOT / 'web' / 'index.html')


@app.get('/health')
def health():
    return {'status': 'ok', 'version': '0.5.0'}


@app.get('/api/state')
def state(request: Request):
    owner = request.state.owner
    version = store.version(owner)
    return {'model': public_model(), 'version': {k: v for k, v in version.items() if k != 'owner'},
            'versions': store.versions(owner), 'requirements': [
                {k: v for k, v in r.items() if k != 'owner'} for r in store.requirements(owner)],
            'runs': [clean_run(r) for r in store.runs(owner)], 'busy': bool(engine.active),
            'budget': store.budget(), 'budget_limit_cny': settings()['budget_cny'],
            'guard': guard.status(owner), 'scenarios': SCENARIOS,
            'scope': '原创任务清单；仅修改 app.js；新增、删除、勾选及刷新行为'}


@app.post('/api/runs')
def create_run(payload: RunInput, request: Request):
    if payload.mode == 'repair' and not payload.symptom.strip():
        raise HTTPException(422, '请描述你遇到的问题')
    try:
        return clean_run(engine.submit(request.state.owner, payload.mode, payload.symptom, payload.expected_version,
                                       language=payload.language))
    except ValueError as exc:
        bad_request(exc)


@app.get('/api/runs/{run_id}')
def get_run(run_id: str, request: Request):
    try:
        return clean_run(store.run(request.state.owner, run_id))
    except ValueError:
        raise HTTPException(404, '运行记录不存在')


@app.post('/api/runs/{run_id}/adopt')
def adopt(run_id: str, payload: AdoptInput, request: Request):
    try:
        version = engine.adopt(request.state.owner, run_id, payload.expected_version)
        guard.publish(request.state.owner, store.version(request.state.owner)['code'])
        return {'version': version}
    except ValueError as exc:
        bad_request(exc)


@app.post('/api/versions')
def change_version(payload: VersionInput, request: Request):
    owner = request.state.owner
    if os.environ.get('APP_PUBLIC') == 'true' and payload.action == 'import':
        raise HTTPException(403, 'Public demo accepts bundled samples only; install the local edition to connect your own project')
    with guard.lock, engine.gate:
        if engine.active:
            raise HTTPException(409, '先等待当前任务完成，再切换版本')
        try:
            if payload.action == 'switch':
                store.switch(owner, payload.version_id, payload.expected_version)
            else:
                code = (scenario_code(payload.scenario_id) if payload.action == 'scenario' else
                        scenario_code('duplicates') if payload.action == 'regression' else payload.code)
                name = ('原创场景 · ' + SCENARIOS[payload.scenario_id]['name'] if payload.action == 'scenario' else
                        '模拟后续改版 · 再次引入误删' if payload.action == 'regression' else payload.name)
                store.add_version(owner, name, code, payload.expected_version)
            guard.publish(owner, store.version(owner)['code'])
        except ValueError as exc:
            bad_request(exc)
    # Version changes trigger saved-check execution without re-entering the original symptom.
    try:
        run = engine.submit(owner, 'recheck', '版本变化后自动复查已保存要求', language=payload.language)
        return {'run': clean_run(run)}
    except ValueError:
        return {'run': None, 'message': '版本已切换，请点击复查以执行保存的检查'}


@app.get('/api/runs/{run_id}/evidence/{phase}/{filename}')
def evidence(run_id: str, phase: str, filename: str, request: Request):
    try:
        store.run(request.state.owner, run_id)
    except ValueError:
        raise HTTPException(404)
    if not re.fullmatch(r'[a-f0-9]{32}', run_id) or not re.fullmatch(r'[a-z0-9-]+', phase) or not re.fullmatch(r'[a-z0-9_-]+\.png', filename):
        raise HTTPException(404)
    target = store.root / 'artifacts' / run_id / phase / filename
    if not target.is_file():
        raise HTTPException(404)
    return FileResponse(target, media_type='image/png')


@app.get('/api/runs/{run_id}/patch')
def patch(run_id: str, request: Request):
    try:
        run = store.run(request.state.owner, run_id)
    except ValueError:
        raise HTTPException(404)
    return Response(run.get('diff', ''), media_type='text/plain',
                    headers={'Content-Disposition': 'attachment; filename="loopcheck.patch"'})


@app.post('/api/runs/{run_id}/timing')
def timing(run_id: str, payload: TimingInput, request: Request):
    try:
        run = store.run(request.state.owner, run_id)
    except ValueError:
        raise HTTPException(404)
    if run['state'] in {'queued', 'running'}:
        raise HTTPException(409, '任务结束后再记录人工时间')
    run.update(human_seconds=payload.human_seconds, timing_note=payload.note, baseline_seconds=payload.baseline_seconds)
    store.save_run(run)
    return {'saved': True}


@app.get('/api/export')
def export(request: Request):
    runs = [clean_run(r) for r in store.runs(request.state.owner)]
    report = {'product': 'LoopCheck 0.3.0', 'notes': '原创模拟故障；人工时间为用户自报。没有基线实验时不能证明提效百分比。',
              'runs': runs, 'requirements': [{k: v for k, v in r.items() if k != 'owner'} for r in store.requirements(request.state.owner)],
              'budget': store.budget()}
    return Response(json.dumps(report, ensure_ascii=False, indent=2), media_type='application/json',
                    headers={'Content-Disposition': 'attachment; filename="loopcheck-evidence.json"'})


@app.post('/api/runs/{run_id}/cancel')
def cancel(run_id: str, request: Request):
    try:
        return engine.cancel(request.state.owner, run_id)
    except ValueError as exc:
        bad_request(exc)


@app.post('/api/guard')
def configure_guard(payload: GuardInput, request: Request):
    try:
        return guard.configure(request.state.owner, payload.enabled, payload.auto_repair, payload.language)
    except ValueError as exc:
        bad_request(exc)


@app.post('/api/guard/change')
def simulate_file_change(payload: GuardChangeInput, request: Request):
    try:
        guard.change(request.state.owner, scenario_code(payload.scenario_id))
        return {'saved': True}
    except ValueError as exc:
        bad_request(exc)


@app.get('/api/runs/{run_id}/report')
def run_report(run_id: str, request: Request):
    try:
        run = store.run(request.state.owner, run_id)
    except ValueError:
        raise HTTPException(404)
    return Response(report_markdown(run), media_type='text/markdown',
                    headers={'Content-Disposition': 'attachment; filename="loopcheck-report.md"'})


@app.get('/api/versions/{version_id}/download')
def download_version(version_id: str, request: Request):
    try:
        version = store.version(request.state.owner, version_id)
    except ValueError:
        raise HTTPException(404)
    return Response(project_zip(version, store.requirements(request.state.owner)), media_type='application/zip',
                    headers={'Content-Disposition': 'attachment; filename="loopcheck-task-app.zip"'})


app.include_router(project_router(projects))
app.mount('/static', StaticFiles(directory=ROOT / 'web'), name='static')
app.mount('/samples/budget', StaticFiles(directory=ROOT / 'examples' / 'budget', html=True), name='budget-demo')
app.mount('/samples/cart', StaticFiles(directory=ROOT / 'examples' / 'cart', html=True), name='cart-demo')
app.mount('/demo', StaticFiles(directory=FIXTURES, html=True), name='original-demo')
