"""Browser subprocess for explicitly connected local previews, with a hard deadline."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from urllib.parse import urlsplit

from .project_checks import Flow, Exploration, local_url
from .settings import ROOT


def execute(payload):
    from playwright.sync_api import sync_playwright, expect
    url = local_url(payload['url'])
    parsed = urlsplit(url)
    origin = f'{parsed.scheme}://{parsed.netloc}'
    directory = Path(payload['directory'])
    directory.mkdir(parents=True, exist_ok=True)
    flows = [Flow.model_validate(f) for f in payload.get('flows', [])]
    if len(flows) > 10:
        raise ValueError('At most 10 flows')
    os.environ.setdefault('PLAYWRIGHT_BROWSERS_PATH', str(ROOT / '.browsers'))
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, args=['--disable-dev-shm-usage'])

        def context_page():
            recording = {'record_video_dir': str(directory / 'video'), 'record_video_size': {'width':1100,'height':760}} if payload.get('record_video') else {}
            ctx = browser.new_context(viewport={'width': 1100, 'height': 760}, service_workers='block', accept_downloads=False, **recording)
            blocked = []
            def route(r):
                p = urlsplit(r.request.url)
                if p.scheme in {'http', 'https'} and f'{p.scheme}://{p.netloc}' == origin:
                    r.continue_()
                else:
                    blocked.append('Cross-origin request blocked')
                    r.abort()
            ctx.route('**/*', route)
            def websocket(ws):
                p = urlsplit(ws.url)
                if p.scheme == 'ws' and p.netloc == parsed.netloc:
                    ws.connect_to_server()
                else:
                    blocked.append('Cross-origin WebSocket blocked')
                    ws.close()
            ctx.route_web_socket('**/*', websocket)
            page = ctx.new_page()
            page.set_default_timeout(1800)
            return ctx, page, blocked

        def locate(page, target):
            if target.by == 'role':
                return page.get_by_role(target.value, name=target.name, exact=True) if target.name else page.get_by_role(target.value)
            if target.by == 'label': return page.get_by_label(target.value, exact=True)
            if target.by == 'text': return page.get_by_text(target.value, exact=True)
            if target.by == 'placeholder': return page.get_by_placeholder(target.value, exact=True)
            return page.get_by_test_id(target.value)

        if payload.get('observe'):
            ctx, page, blocked = context_page()
            try:
                response = page.goto(url, wait_until='domcontentloaded', timeout=10000)
                if response and response.status >= 400: raise ValueError('Preview returned HTTP error')
                exploration = Exploration.model_validate({'steps': payload.get('exploration', [])})
                for step in exploration.steps:
                    target = locate(page, step.target) if step.target else None
                    if target is not None and (target.count() != 1 or not target.is_visible()):
                        raise ValueError('Exploration target missing, hidden or ambiguous; observe the preceding page first')
                    if step.action == 'navigate': page.goto(origin + step.value, wait_until='domcontentloaded', timeout=10000)
                    elif step.action == 'click': target.click()
                    elif step.action == 'fill': target.fill(step.value)
                    elif step.action == 'select': target.select_option(step.value)
                    elif step.action == 'hover': target.hover()
                    elif step.action == 'press': target.press(step.value)
                page.screenshot(path=str(directory / 'page.png'))
                fields = page.locator('input,select,textarea,output,[role="alert"]').evaluate_all("els => els.slice(0,40).map(e=>({tag:e.tagName.toLowerCase(),type:e.getAttribute('type'),label:e.getAttribute('aria-label')||Array.from(e.labels||[]).map(x=>x.textContent.trim()).join(' '),role:e.getAttribute('role')}))")
                leaves = page.locator('body *').evaluate_all("els => els.filter(e=>!e.children.length && e.checkVisibility() && e.innerText && e.innerText.trim().length<=160).slice(0,60).map(e=>e.innerText.trim())")
                text_targets = [{'by':'text','value':value} for value in dict.fromkeys(leaves) if page.get_by_text(value,exact=True).count()==1]
                return {'text_targets': text_targets, 'title': page.title(), 'page': page.locator('body').aria_snapshot()[:7000], 'elements': fields,
                        'blocked_resources': bool(blocked), 'source': 'live_browser',
                        'truncated': len(page.locator('body').aria_snapshot()) > 7000,
                        'next_step': 'Narrow the page or remove external dependencies if observations are truncated or blocked',
                        'exploration': payload.get('exploration', [])}
            finally:
                ctx.close()
                browser.close()
        checks = []
        for n, flow in enumerate(flows):
            started = time.monotonic()
            ctx, page, blocked = context_page()
            row = {'title': flow.title, 'expectation': flow.expectation, 'status': 'passed', 'step': 0,
                   'expected': '', 'actual': '', 'screenshot': f'flow-{n}.png', 'steps_completed': 0}
            try:
                response = page.goto(url, wait_until='domcontentloaded', timeout=10000)
                if response and response.status >= 400: raise ValueError('Preview returned HTTP error')
                hidden_targets = {json.dumps(s.target.model_dump(), sort_keys=True): s.target for s in flow.steps if s.action == 'expect_hidden'}
                seen_visible = set()
                for index, step in enumerate(flow.steps):
                    for key, locator in hidden_targets.items():
                        candidate = locate(page, locator)
                        if candidate.count() == 1 and candidate.is_visible(): seen_visible.add(key)
                    row['step'] = index + 1
                    row['expected'] = step.model_dump(exclude_none=True)
                    a, target = step.action, locate(page, step.target) if step.target else None
                    if a == 'navigate': page.goto(origin + step.value, wait_until='domcontentloaded', timeout=10000)
                    elif a == 'reload': page.reload(wait_until='domcontentloaded', timeout=10000)
                    elif a == 'click': target.click()
                    elif a == 'hover': target.hover()
                    elif a == 'fill': target.fill(step.value)
                    elif a == 'select': target.select_option(step.value)
                    elif a == 'check': target.set_checked(step.checked)
                    elif a == 'press': target.press(step.value)
                    elif a == 'expect_text': expect(target).to_have_text(step.value, timeout=2000)
                    elif a == 'expect_value': expect(target).to_have_value(step.value, timeout=2000)
                    elif a == 'expect_count': expect(target).to_have_count(step.count, timeout=2000)
                    elif a == 'expect_visible': expect(target).to_be_visible(timeout=2000)
                    elif a == 'expect_hidden':
                        if json.dumps(step.target.model_dump(), sort_keys=True) not in seen_visible:
                            raise ValueError('Hidden assertion target was never observed visible in this flow; verify the locator and opening steps')
                        expect(target).to_be_hidden(timeout=2000)
                    elif a == 'expect_checked': expect(target).to_be_checked(checked=step.checked, timeout=2000)
                    elif a == 'expect_url': expect(page).to_have_url(origin + step.value, timeout=2000)
                    row['steps_completed'] += 1
                if blocked:
                    row.update(status='inconclusive', actual='The preview requires blocked cross-origin resources')
                else:
                    row['actual'] = 'All declared browser assertions passed'
            except AssertionError as exc:
                row.update(status='failed', actual=str(exc)[:1400])
                try:
                    if step.action == 'expect_text' and step.value and page.get_by_text(step.value, exact=True).count()==1:
                        row['locator_hint'] = {'observed_exact_text_target': {'by':'text','value':step.value}, 'note':'This exact text exists as a unique element in the failing page; inspect before changing the target. Keep the expected value.'}
                    if step.action == 'expect_text': observed = target.all_text_contents()
                    elif step.action == 'expect_value': observed = target.input_value()
                    elif step.action == 'expect_count': observed = target.count()
                    elif step.action in {'expect_visible','expect_hidden'}: observed = target.is_visible()
                    elif step.action == 'expect_checked': observed = target.is_checked()
                    else: observed = page.url
                    row['observed_value'] = observed
                    row['business_summary'] = f"{flow.expectation} | Expected: {step.value if step.action not in {'expect_count','expect_hidden','expect_visible'} else step.count if step.action == 'expect_count' else step.action} | Actual: {observed}"
                except Exception: pass
            except Exception as exc:
                row.update(status='inconclusive', actual=f'{type(exc).__name__}: {str(exc)[:900]}')
            finally:
                try: page.screenshot(path=str(directory / row['screenshot']), timeout=3000)
                except Exception: row.pop('screenshot', None)
                ctx.close()
                if payload.get('record_video') and page.video:
                    row['video'] = str(Path(page.video.path()).relative_to(directory))
            row['seconds'] = round(time.monotonic() - started, 2)
            checks.append(row)
        browser.close()
    return {'checks': checks, 'source': 'real_playwright_chromium',
            'all_passed': bool(checks) and all(c['status'] == 'passed' for c in checks)}


def run_browser(url, flows, directory, *, observe=False, record_video=False, exploration=None, cancelled=lambda: False):
    from .browser_slot import browser_slot
    try:
        with browser_slot(cancelled):
            return _run_browser(url, flows, directory, observe=observe, record_video=record_video, exploration=exploration, cancelled=cancelled)
    except ValueError as exc:
        return {'error': str(exc), 'checks': [], 'all_passed': False}


def _run_browser(url, flows, directory, *, observe=False, record_video=False, exploration=None, cancelled=lambda: False):
    directory = Path(directory).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    inp, out = directory / 'input.json', directory / 'output.json'
    inp.write_text(json.dumps({'url': url, 'flows': flows, 'directory': str(directory), 'observe': observe, 'record_video':record_video, 'exploration':exploration or []}), encoding='utf-8')
    env = {k: v for k, v in os.environ.items() if k.upper() in {
        'SYSTEMROOT', 'WINDIR', 'PATH', 'PATHEXT', 'TEMP', 'TMP', 'USERPROFILE', 'LOCALAPPDATA', 'HOME'}}
    env.update(PYTHONUTF8='1', PLAYWRIGHT_BROWSERS_PATH=os.environ.get('PLAYWRIGHT_BROWSERS_PATH', str(ROOT / '.browsers')))
    opts = {'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {'start_new_session': True}
    process = subprocess.Popen([sys.executable, '-m', 'coach.project_browser', str(inp), str(out)],
        cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **opts)
    deadline = time.monotonic() + 120
    while process.poll() is None:
        if cancelled() or time.monotonic() > deadline:
            if os.name == 'nt': subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], capture_output=True, timeout=10)
            else: os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=10)
            return {'error': 'Cancelled' if cancelled() else 'Browser deadline exceeded (120s)', 'checks': [], 'all_passed': False}
        time.sleep(.1)
    if process.returncode or not out.is_file():
        return {'error': 'Browser unavailable or preview could not be inspected', 'checks': [], 'all_passed': False}
    return json.loads(out.read_text(encoding='utf-8'))


if __name__ == '__main__':
    try:
        result = execute(json.loads(Path(sys.argv[1]).read_text(encoding='utf-8')))
    except Exception as exc:
        result = {'error': f'{type(exc).__name__}: {str(exc)[:600]}', 'checks': [], 'all_passed': False}
    Path(sys.argv[2]).write_text(json.dumps(result, ensure_ascii=False), encoding='utf-8')
