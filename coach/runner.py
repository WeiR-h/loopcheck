"""Isolated browser worker. Receives only demo source and bounded declarative checks."""
import json
import os
from pathlib import Path
import secrets
import sys
import time

from playwright.sync_api import sync_playwright, expect
from .checks import BASELINE_LABELS, Requirement
from .settings import ROOT, FIXTURES

ORIGIN = 'https://loopcheck.invalid'


def execute(payload):
    code = payload['code']
    if len(code.encode()) > 16_000:
        raise ValueError('Source limit exceeded')
    specs = [Requirement.model_validate(x).model_dump() for x in payload.get('requirements', [])]
    if len(specs) > 12:
        raise ValueError('Requirement limit exceeded')
    artifacts = Path(payload['artifacts']).resolve()
    artifacts.mkdir(parents=True, exist_ok=True)
    html = (FIXTURES / 'index.html').read_text(encoding='utf-8')
    css = (FIXTURES / 'style.css').read_text(encoding='utf-8')
    resources = {'/': ('text/html', html), '/app.js': ('text/javascript', code), '/style.css': ('text/css', css)}
    results = []
    os.environ.setdefault('PLAYWRIGHT_BROWSERS_PATH', str(ROOT / '.browsers'))
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, args=['--disable-dev-shm-usage'])

        def run_one(test_id, label, fn):
            started = time.monotonic()
            context = browser.new_context(viewport={'width': 920, 'height': 720},
                                          service_workers='block', accept_downloads=False)
            context.route_web_socket('**/*', lambda ws: ws.close())
            blocked = []
            def route_request(route):
                url = route.request.url
                path = url.removeprefix(ORIGIN)
                if url.startswith(ORIGIN + '/') and path in resources and route.request.method == 'GET':
                    mime, body = resources[path]
                    route.fulfill(status=200, content_type=mime, body=body,
                        headers={'Content-Security-Policy': "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'none'; object-src 'none'; base-uri 'none'; frame-src 'none'; form-action 'none'"})
                else:
                    blocked.append('external request blocked')
                    route.abort()
            context.route('**/*', route_request)
            page = context.new_page()
            page.set_default_timeout(1800)
            errors = []
            page.on('pageerror', lambda _: errors.append('页面脚本发生异常'))
            screenshot = f'{len(results):02d}-{test_id}.png'
            result = {'id': test_id, 'label': label, 'passed': False, 'expected': '', 'actual': '', 'screenshot': screenshot}
            try:
                page.goto(ORIGIN + '/', timeout=6000, wait_until='load')
                detail = fn(page)
                result.update(passed=not errors and not blocked, expected=detail,
                              actual=errors[0] if errors else '页面尝试访问外部资源，检查已拒绝' if blocked else detail)
            except Exception as exc:
                # Browser errors may echo arbitrary source. Retain only our bounded assertions.
                result['actual'] = str(exc)[:400] if type(exc) is AssertionError else '页面操作超时或脚本运行异常'
                result['expected'] = label
            try:
                page.screenshot(path=str(artifacts / screenshot), timeout=3000)
            except Exception:
                result['screenshot'] = None
            result['blocked_requests'] = len(blocked)
            result['seconds'] = round(time.monotonic() - started, 3)
            results.append(result)
            context.close()

        def add(page, title):
            page.get_by_test_id('new-task').fill(title)
            page.get_by_test_id('add-task').click()

        def rows(page):
            return page.get_by_test_id('task-row')

        def count(page, n):
            actual = rows(page).count()
            assert actual == n, f'预期 {n} 条任务，实际 {actual} 条'

        def basic(page):
            add(page, '整理今天的计划')
            count(page, 1)
            rows(page).first.locator('input').check()
            assert rows(page).first.get_attribute('data-completed') == 'true', '勾选后完成状态未保存'
            return '新增 1 条，勾选后状态为已完成'

        def duplicates(page):
            name = '复查-' + secrets.token_hex(3)
            add(page, name)
            add(page, name)
            identities = rows(page).evaluate_all('(rows) => rows.map(row => row.dataset.id)')
            assert len(identities) == 2 and identities[0] != identities[1], '每条记录应有独立标识'
            rows(page).first.locator('[data-action=delete]').click()
            count(page, 1)
            assert rows(page).first.get_attribute('data-id') == identities[1], '剩下的必须是原来第二条记录'
            return '删除第一条后，第二条的内容和标识保持不变'

        def mixed(page):
            name = '同名-' + secrets.token_hex(2)
            for title in [name, '保留的其他任务', name]:
                add(page, title)
            identities = rows(page).evaluate_all('(rows) => rows.map(row => row.dataset.id)')
            rows(page).nth(2).locator('[data-action=delete]').click()
            count(page, 2)
            actual = rows(page).evaluate_all('(rows) => rows.map(row => row.dataset.id)')
            assert actual == identities[:2], '删除第三条后，前两条的标识和顺序应不变'
            return '三条混排记录中只删除选中的第三条'

        def persistence(page):
            title = '明天还要做-' + secrets.token_hex(2)
            add(page, title)
            rows(page).first.locator('input').check()
            page.reload(wait_until='load')
            count(page, 1)
            assert rows(page).first.locator('span').inner_text() == title, '刷新后任务内容发生变化'
            assert rows(page).first.get_attribute('data-completed') == 'true', '刷新后完成状态丢失'
            return '刷新后，任务内容和勾选状态均保留'

        if payload.get('baseline', True):
            for name, fn in [('add_toggle', basic), ('duplicate_identity', duplicates), ('mixed_order', mixed), ('persistence', persistence)]:
                run_one(name, BASELINE_LABELS[name], fn)

        def custom(spec):
            def run(page):
                for step in spec['steps']:
                    action, idx = step['action'], step['index']
                    if action == 'add':
                        add(page, step['value'])
                    elif action == 'delete':
                        rows(page).nth(idx).locator('[data-action=delete]').click()
                    elif action == 'toggle':
                        rows(page).nth(idx).locator('input').set_checked(step['done'])
                    elif action == 'reload':
                        page.reload(wait_until='load')
                    elif action == 'expect_count':
                        count(page, step['count'])
                    elif action == 'expect_title':
                        actual = rows(page).nth(idx).locator('span').inner_text()
                        assert actual == step['value'], f'第 {idx + 1} 条预期 {step["value"]}，实际 {actual}'
                    elif action == 'expect_done':
                        assert rows(page).nth(idx).get_attribute('data-completed') == str(step['done']).lower(), '完成状态与预期不符'
                return f'保存的 {len(spec["steps"])} 个操作与断言已执行'
            return run
        for i, spec in enumerate(specs):
            run_one(f'requirement_{i}', spec['title'], custom(spec))
        browser.close()
    return {'checks': results, 'all_passed': bool(results) and all(r['passed'] for r in results),
            'passed': sum(r['passed'] for r in results), 'total': len(results), 'source': 'real_playwright_chromium'}


def main():
    payload = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
    output = Path(sys.argv[2])
    try:
        result = execute(payload)
    except Exception as exc:
        result = {'checks': [], 'all_passed': False, 'error': f'浏览器运行器未完成（{type(exc).__name__}）', 'source': 'real_playwright_chromium'}
    output.write_text(json.dumps(result, ensure_ascii=False), encoding='utf-8')


if __name__ == '__main__':
    main()
