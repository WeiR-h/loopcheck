import test_support  # isolate storage before importing any application module
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
import io
import zipfile

from fastapi.testclient import TestClient
from coach.engine import Engine
from coach.guard import Guard
from coach.reports import project_zip, report_markdown
from coach.scenarios import scenario_code
from coach.store import Store, digest
from coach.validation import validate
from test_v1 import SPEC, fake_model, wait_run


class IterationTests(unittest.TestCase):
    def test_guard_detects_file_once_and_prepares_verified_patch(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(tmp)
            owner = store.session()
            initial = store.version(owner)
            good = scenario_code('duplicates').replace('tasks = tasks.filter(task => task.title !== selected.title);',
                                                       'tasks = tasks.filter(task => task.id !== id);')
            store.add_version(owner, 'Verified fixture', good, initial['id'], SPEC)
            engine = Engine(store, fake_model)
            guard = Guard(store, engine)
            guard.configure(owner, True, True)
            guard.change(owner, scenario_code('duplicates'))
            guard.tick()
            cfg = guard.status(owner); cfg['pending_since'] = time.time() - 2
            guard.save(owner, cfg)
            guard.tick()
            first = guard.status(owner)['last_run']
            self.assertEqual(wait_run(store, owner, first)['state'], 'issues_found')
            with patch('coach.guard.public_model', return_value={'configured': True}):
                guard.tick()
            second = guard.status(owner)['last_run']
            repaired = wait_run(store, owner, second)
            self.assertEqual(repaired['state'], 'ready', repaired.get('error'))
            self.assertEqual(repaired['trigger'], 'guard_repair')
            guard.tick(); guard.tick()
            self.assertEqual(len(store.runs(owner)), 2, 'An unchanged file must not trigger repeated model work')
            self.assertEqual(store.budget()['calls'], 0)
            engine.adopt(owner, second, store.version(owner)['id'])
            guard.publish(owner, store.version(owner)['code'])
            self.assertEqual(guard.status(owner)['phase'], 'watching')
            self.assertEqual(digest(guard.path(owner).read_text(encoding='utf-8')), store.version(owner)['hash'])
            # Publishing must not overwrite an edit arriving while a patch is being reviewed.
            guard.change(owner, good + '\n// New local edit\n')
            guard.publish(owner, good)
            self.assertFalse(guard.status(owner)['enabled'])
            self.assertIn('New local edit', guard.path(owner).read_text(encoding='utf-8'))
            engine.pool.shutdown(wait=True)

    def test_scenarios_reproduce_distinct_behaviors(self):
        with tempfile.TemporaryDirectory() as tmp:
            persistence = validate(scenario_code('persistence'), Path(tmp) / 'persistence')
            self.assertEqual([c['id'] for c in persistence['checks'] if not c['passed']], ['persistence'])
            toggle = validate(scenario_code('toggle'), Path(tmp) / 'toggle')
            self.assertIn('add_toggle', [c['id'] for c in toggle['checks'] if not c['passed']])

    def test_cancel_preserves_original_and_export_is_scoped(self):
        import coach.app as module
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(tmp); owner = store.session(); original = store.version(owner)
            engine = Engine(store, fake_model); guard = Guard(store, engine)
            with patch.object(module, 'store', store), patch.object(module, 'engine', engine), patch.object(module, 'guard', guard):
                with TestClient(module.app, base_url='http://localhost') as a, TestClient(module.app, base_url='http://localhost') as b:
                    a.cookies.set('loopcheck_session', owner)
                    a.get('/api/state'); b.get('/api/state')
                    self.assertEqual(b.get('/api/versions/' + original['id'] + '/download').status_code, 404)
                    response = a.get('/api/versions/' + original['id'] + '/download')
                    with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                        self.assertIn('app.js', z.namelist()); self.assertNotIn('.env', z.namelist())
                    self.assertEqual(a.post('/api/guard', json={'enabled': True}).status_code, 409)
                    job = a.post('/api/runs', json={'mode': 'diagnose', 'expected_version': original['id']}).json()
                    self.assertEqual(a.post('/api/runs/' + job['id'] + '/cancel', json={}).status_code, 200)
                    done = wait_run(store, owner, job['id'])
                    self.assertEqual(done['state'], 'cancelled')
                    self.assertEqual(store.version(owner)['code'], original['code'])
                    text = a.get('/api/runs/' + job['id'] + '/report').text
                    self.assertIn('cancelled', text)
                    self.assertIn('Self-reported', text)
                    self.assertEqual(b.get('/api/runs/' + job['id'] + '/report').status_code, 404)
