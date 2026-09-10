import test_support  # isolate storage before importing any application module
import copy
import functools
import http.server
from pathlib import Path
import shutil
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from coach.project_browser import run_browser
from coach.project_checks import Flow, local_url
from coach.projects import Projects, snapshot
from coach.settings import ROOT
from coach.store import Store
from project_fixtures import BUDGET_FLOWS


def wait(service, owner, ident):
    deadline = time.monotonic() + 150
    while time.monotonic() < deadline:
        run = service.get(owner, ident, 'run')
        if run['state'] not in {'queued', 'running'}:
            while service.active: time.sleep(.02)
            return run
        time.sleep(.05)
    raise AssertionError('Run timed out')


class ProjectTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.project = self.root / 'budget'
        shutil.copytree(ROOT / 'examples/budget', self.project)
        class Quiet(http.server.SimpleHTTPRequestHandler):
            def log_message(self, *args): pass
        self.server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Quiet, directory=str(self.project)))
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.store = Store(self.root / 'state')
        self.owner = self.store.session()
        self.service = Projects(self.store)
        self.p = self.service.connect(self.owner, self.project, f'http://127.0.0.1:{self.server.server_port}/')

    def tearDown(self):
        self.service.stop()
        self.service.pool.shutdown(wait=True)
        self.server.shutdown()
        self.server.server_close()
        self.tmp.cleanup()

    def draft(self, flows=None):
        return self.service.draft(self.owner, self.p['id'], 'Preserve budget behavior', flows or BUDGET_FLOWS,
                                  snapshot(self.project)['hash'])

    def approve(self):
        d = self.draft()
        r = self.service.confirm(self.owner, d['id'], d['digest'])
        return wait(self.service, self.owner, r['id'])

    def test_real_baseline_regression_recheck_and_persistence(self):
        baseline = self.approve()
        self.assertEqual(baseline['state'], 'passed', baseline)
        original = (self.project / 'app.js').read_text()
        self.service.watch(self.owner, self.p['id'], True)
        (self.project / 'app.js').write_text(original.replace('(i - e)', '(i + e)'))
        self.service.tick()
        self.service.pending[self.p['id']] = (snapshot(self.project)['hash'], time.monotonic() - 2)
        self.service.tick()
        regression = wait(self.service, self.owner, self.service.active)
        self.assertEqual(regression['state'], 'failed')
        self.assertEqual(regression['checks'][0]['classification'], 'regression')
        self.assertIn('Failed step', regression['repair_brief'])
        self.assertIn('app.js', regression['changed_files'])
        self.service.tick()
        self.assertIsNone(self.service.active)
        (self.project / 'app.js').write_text(original)
        result = wait(self.service, self.owner, self.service.submit(self.owner, self.p['id'])['id'])
        self.assertEqual(result['state'], 'passed')
        self.assertEqual(self.store.budget()['calls'], 0)
        restarted = Projects(Store(self.root / 'state'))
        try:
            p = restarted.get(self.owner, self.p['id'], 'project')
            self.assertEqual(len(restarted.get(self.owner, p['contract_id'], 'contract')['flows']), 3)
        finally: restarted.stop()

    def test_schema_blocks_script_external_navigation_and_vacuous_checks(self):
        for url in ['https://example.com:443/', 'http://127.0.0.1.evil:80/', 'http://user:secret@localhost:80/', 'file:///tmp/a']:
            with self.assertRaises(ValueError): local_url(url)
        for steps in [[{'action':'evaluate','value':'fetch()'}], [{'action':'navigate','value':'//evil.com'}], [{'action':'reload'}]]:
            with self.assertRaises(ValueError): Flow.model_validate({'title':'Invalid flow','expectation':'No bypass','steps':steps})

    def test_snapshot_ignores_secrets_and_dependencies_but_tracks_source(self):
        before = snapshot(self.project)
        (self.project / '.env').write_text('SECRET=do-not-read')
        (self.project / 'node_modules').mkdir()
        (self.project / 'node_modules' / 'secret.js').write_text('private')
        self.assertEqual(before, snapshot(self.project))
        (self.project / 'app.js').write_text('// changed source')
        self.assertNotEqual(before['hash'], snapshot(self.project)['hash'])

    def test_confirm_rejects_changed_source_wrong_digest_and_cross_session(self):
        d = self.draft()
        with self.assertRaises(ValueError): self.service.confirm(self.owner, d['id'], '0'*64)
        other = self.store.session()
        with self.assertRaises(ValueError): self.service.get(other, d['id'])
        with self.assertRaises(ValueError): self.service.bridge_owner(self.p['id'], 'wrong-key')
        self.assertEqual(self.service.bridge_owner(self.p['id'], self.p['bridge_key']), self.owner)
        (self.project / 'app.js').write_text('// changed')
        with self.assertRaises(ValueError): self.service.confirm(self.owner, d['id'], d['digest'])

    def test_flow_limit_cannot_replace_existing_requirements(self):
        flows = []
        for i in range(10):
            flow = copy.deepcopy(BUDGET_FLOWS[0]); flow['title'] = f'Check {i}'; flow['steps'][0]['value'] = str(i)
            flows.append(flow)
        d = self.draft(flows)
        with patch('coach.projects.run_browser', return_value={'all_passed':False,'checks':[],'error':'test environment unavailable'}):
            wait(self.service, self.owner, self.service.confirm(self.owner, d['id'], d['digest'])['id'])
        before = self.service.get(self.owner, self.p['id'], 'project')['contract_id']
        with self.assertRaises(ValueError): self.draft([BUDGET_FLOWS[1]])
        self.assertEqual(before, self.service.get(self.owner, self.p['id'], 'project')['contract_id'])

    def test_source_changed_during_run_never_reports_passed(self):
        def simulated_browser(*args, **kwargs):
            (self.project / 'app.js').write_text('// new revision during browser work')
            return {'all_passed':True,'checks':[]}
        d = self.draft()
        with patch('coach.projects.run_browser', side_effect=simulated_browser):
            result = wait(self.service, self.owner, self.service.confirm(self.owner, d['id'], d['digest'])['id'])
        self.assertEqual(result['state'], 'stale')
        stored = self.service.get(self.owner, result['id'], 'run')
        self.assertIn('followup_id', stored)
        fresh = self.service.get(self.owner, stored['followup_id'], 'run')
        self.assertEqual(fresh['source_hash'], snapshot(self.project)['hash'])
        self.assertEqual(fresh['state'], 'inconclusive', 'Empty runner output cannot approve a change')

    def test_new_requirement_remains_unmet_across_rechecks(self):
        flow = copy.deepcopy(BUDGET_FLOWS[0])
        flow['purpose'] = 'new'
        d = self.draft([flow])
        failed = {'all_passed':False,'checks':[{'title':flow['title'],'expectation':flow['expectation'],
                  'status':'failed','step':1,'expected':'850','actual':'not implemented'}]}
        with patch('coach.projects.run_browser', return_value=failed):
            first = wait(self.service,self.owner,self.service.confirm(self.owner,d['id'],d['digest'])['id'])
            second = wait(self.service,self.owner,self.service.submit(self.owner,self.p['id'])['id'])
        self.assertEqual(first['checks'][0]['classification'],'new_requirement_unmet')
        self.assertEqual(second['checks'][0]['classification'],'new_requirement_unmet')

    def test_missing_locator_is_inconclusive_not_passed(self):
        flow = copy.deepcopy(BUDGET_FLOWS[0]); flow['steps'][0]['target']['value'] = 'Missing field'
        result = run_browser(self.p['url'], [flow], self.root / 'missing')
        self.assertFalse(result['all_passed'])
        self.assertEqual(result['checks'][0]['status'], 'inconclusive')

    def test_external_resources_cannot_make_a_green_result(self):
        path = self.project / 'app.js'
        path.write_text(path.read_text() + "\nfetch('https://example.com/').catch(()=>{});\n")
        result = run_browser(self.p['url'], [BUDGET_FLOWS[0]], self.root / 'external')
        self.assertFalse(result['all_passed'])
        self.assertEqual(result['checks'][0]['status'], 'inconclusive')


if __name__ == '__main__': unittest.main()
