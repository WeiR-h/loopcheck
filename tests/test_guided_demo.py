"""Real public HTTP/browser walkthrough, isolated storage and no provider key."""
import test_support
import hashlib
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest

import httpx

ROOT = Path(__file__).resolve().parents[1]


class GuidedDemoTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='loopcheck-guided-')
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            self.port = sock.getsockname()[1]
        self.env = {**os.environ, 'LOOPCHECK_DATA': self.temp.name, 'PORT': str(self.port), 'APP_PUBLIC': 'true', 'DASHSCOPE_API_KEY': ''}
        self.url = f'http://127.0.0.1:{self.port}'
        self.client = httpx.Client(base_url=self.url, trust_env=False, timeout=10)
        self.log = open(Path(self.temp.name)/'server.log', 'wb')
        self.launch()

    def launch(self):
        command = [sys.executable, 'run.py']
        if os.name == 'nt':
            # Start the interpreter directly, not Windows' venv redirector, so our
            # process handle owns the actual server and reliably closes its log.
            packages = str(Path(sys.executable).parent.parent / 'Lib/site-packages')
            bootstrap = f'import sys,runpy;sys.path.insert(0,{packages!r});sys.executable={sys.executable!r};runpy.run_path("run.py",run_name="__main__")'
            command = [sys._base_executable, '-c', bootstrap]
        self.proc = subprocess.Popen(command, cwd=ROOT, env=self.env, stdout=self.log, stderr=self.log)
        for _ in range(150):
            try:
                if self.client.get('/health').status_code == 200: return
            except httpx.TransportError: pass
            time.sleep(.1)
        self.fail('Isolated demo server failed to start')

    def tearDown(self):
        self.stop_server()
        self.client.close(); self.log.close(); self.temp.cleanup()

    def stop_server(self):
        self.proc.terminate()
        self.proc.wait(timeout=20)

    def post(self, path, data=None):
        r = self.client.post('/api/projects'+path, json=data)
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    def wait(self, run):
        for _ in range(600):
            current = self.client.get('/api/projects/runs/'+run['id']).json()
            if current['state'] not in {'queued', 'running'}: return current
            time.sleep(.1)
        self.fail('Demo browser run timed out')

    def confirm(self, draft):
        return self.wait(self.post('/drafts/'+draft['id']+'/confirm', {'digest':draft['digest']}))

    def state(self, ident):
        return next(p for p in self.client.get('/api/projects').json()['projects'] if p['id']==ident)

    def advance(self, ident, action):
        p = self.state(ident)
        return self.post('/'+ident+'/guided-demo', {'action':action,'source_hash':p['current_source_hash'],'contract_id':p['contract_id']})

    def test_zero_key_future_regression_repair_and_restart(self):
        original = hashlib.sha256((ROOT/'examples/cart/app.js').read_bytes()).hexdigest()
        value = self.post('/guided-demo'); p = value['project']
        self.assertIsNone(self.state(p['id'])['contract_id'])
        self.assertNotIn('root', p)
        self.assertIn('no model calls', value['disclosure'])
        self.assertEqual(self.confirm(value['draft'])['state'], 'passed')
        future = self.confirm(self.advance(p['id'], 'future')['draft'])
        self.assertEqual(future['state'], 'incomplete')
        self.assertEqual(future['coverage']['uncovered'], 1)
        self.assertFalse(future['can_accept'])
        self.stop_server(); self.launch()
        self.assertEqual(self.state(p['id'])['contract_id'], future['contract_id'])
        before = self.state(p['id'])
        feature = self.advance(p['id'], 'feature')['draft']
        stale = self.client.post('/api/projects/'+p['id']+'/guided-demo', json={'action':'feature','source_hash':before['current_source_hash'],'contract_id':before['contract_id']})
        self.assertEqual(stale.status_code, 409)
        failure = self.confirm(feature)
        self.assertEqual(failure['state'], 'failed')
        self.assertFalse(failure['can_accept'])
        self.assertTrue(any(c['status']=='failed' and c.get('screenshot') for c in failure['checks']))
        self.assertIn('All reproduction steps', failure['repair_brief'])
        repaired = self.wait(self.advance(p['id'], 'repair')['run'])
        self.assertTrue(repaired['can_accept'], repaired)
        self.assertEqual(repaired['coverage']['passed'], 4)
        self.assertFalse(self.client.get('/api/projects/runs/'+failure['id']).json()['can_accept'])
        self.assertEqual(self.client.get('/api/projects').json()['budget']['calls'], 0)
        self.assertEqual(hashlib.sha256((ROOT/'examples/cart/app.js').read_bytes()).hexdigest(), original)
        self.check_history_ui(failure['id'])

    def test_pinned_public_sample_inline_assets_work_under_csp(self):
        from playwright.sync_api import sync_playwright, expect
        os.environ.setdefault('PLAYWRIGHT_BROWSERS_PATH', str(ROOT / '.browsers'))
        home = self.client.get('/').headers['Content-Security-Policy']
        sample = self.client.get('/samples/public/shopping/').headers['Content-Security-Policy']
        self.assertNotIn('unsafe-inline', sample)
        self.assertNotIn('sha256-', home)
        self.assertIn('sha256-', sample)
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True, args=['--disable-dev-shm-usage'])
            page = browser.new_page()
            page.goto(self.url+'/samples/public/shopping/')
            page.get_by_label('Enter a new item:', exact=True).fill('Milk')
            page.get_by_role('button', name='Add item', exact=True).click()
            expect(page.get_by_text('Milk', exact=True)).to_have_text('Milk')
            expect(page.get_by_label('Enter a new item:', exact=True)).to_have_value('')
            page.get_by_role('button', name='Delete', exact=True).click()
            expect(page.get_by_role('listitem')).to_have_count(0)
            browser.close()

    def check_history_ui(self, failure_id):
        from playwright.sync_api import sync_playwright, expect
        os.environ.setdefault('PLAYWRIGHT_BROWSERS_PATH', str(ROOT / '.browsers'))
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True, args=['--disable-dev-shm-usage'])
            context = browser.new_context()
            context.add_cookies([{'name':c.name, 'value':c.value, 'url':self.url} for c in self.client.cookies.jar])
            page = context.new_page()
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.add_init_script("localStorage.setItem('loopcheck-language','en')")
            page.goto(self.url)
            expect(page.locator('#coverage-summary')).to_contain_text('Passed: 4', timeout=15000)
            page.locator('[data-run="'+failure_id+'"]').click()
            expect(page.locator('#result-summary')).to_contain_text('Historical result')
            expect(page.locator('#coverage-summary')).to_contain_text('Passed: 4')
            page.locator('#brief-details summary').click()
            expect(page.locator('#brief-preview')).to_be_visible()
            expect(page.locator('#brief-preview')).to_contain_text('All reproduction steps')
            expect(page.locator('#brief-preview')).to_contain_text('Actual value: 300.00')
            self.assertEqual(errors, [])
            browser.close()

    def test_owner_source_and_public_boundaries(self):
        value = self.post('/guided-demo'); p = value['project']
        with httpx.Client(base_url=self.url, trust_env=False) as other:
            r = other.post('/api/projects/'+p['id']+'/guided-demo', json={'action':'future','source_hash':'0'*64,'contract_id':None})
            self.assertEqual(r.status_code, 409)
            q = other.post('/api/projects/guided-demo').json()['project']
            self.assertNotEqual(q['guided_demo'], p['guided_demo'])
        self.assertEqual(self.post('/guided-demo')['project']['id'], p['id'])
        self.assertEqual(self.client.get('/samples/guided/'+p['guided_demo']+'/app.js').status_code, 200)
        self.assertEqual(self.client.get('/samples/guided/'+p['guided_demo']+'/.env').status_code, 404)
        self.assertEqual(self.client.get('/samples/guided/not-valid/app.js').status_code, 404)
        baseline = self.confirm(value['draft'])
        folder = Path(self.temp.name)/'guided-demos'/p['guided_demo']
        with (folder/'app.js').open('a') as stream: stream.write('\n// concurrent change\n')
        r = self.client.post('/api/projects/'+p['id']+'/guided-demo', json={'action':'future','source_hash':baseline['source_hash'],'contract_id':baseline['contract_id']})
        self.assertEqual(r.status_code, 409)
        regular = self.post('/sample')
        r = self.client.post('/api/projects/'+regular['id']+'/guided-demo', json={'action':'repair','source_hash':'0'*64,'contract_id':None})
        self.assertEqual(r.status_code, 409)
        self.assertFalse(self.client.get('/api/projects').json()['model']['configured'])
