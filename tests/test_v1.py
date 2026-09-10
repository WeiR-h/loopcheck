import test_support  # isolate storage before importing any application module
"""Real-browser verification and explicitly offline Strands protocol tests.

The scripted model below exists only in tests. The product has no scripted repair mode.
"""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from openai.types.chat import ChatCompletion
from strands.models.openai import OpenAIModel
from fastapi.testclient import TestClient

from coach.checks import Requirement
from coach.engine import Engine
from coach.guard import Guard
from coach.settings import FIXTURES
from coach.store import Store
from coach.validation import validate

SPEC = {'title': '删除同名任务时保留另一条', 'steps': [
    {'action': 'add', 'value': '买牛奶'}, {'action': 'add', 'value': '买牛奶'},
    {'action': 'delete', 'index': 0}, {'action': 'expect_count', 'count': 1},
    {'action': 'expect_title', 'index': 0, 'value': '买牛奶'}]}
OLD = 'tasks = tasks.filter(task => task.title !== selected.title);'
NEW = 'tasks = tasks.filter(task => task.id !== id);'


class ScriptedModel:
    """Fake provider replies exercise real Strands dispatch; not a live model evaluation."""
    def __init__(self):
        self.index = 0

    async def create(self, **request):
        self.index += 1
        steps = [('read_project', {}), ('run_checks', {}),
                 ('record_requirement', {'spec': SPEC}),
                 ('edit_app', {'old_text': OLD, 'new_text': NEW, 'reason': 'Offline test fixture patch'})]
        if self.index <= len(steps):
            name, args = steps[self.index - 1]
            message = {'role': 'assistant', 'content': None, 'tool_calls': [
                {'id': f'test-{self.index}', 'type': 'function', 'function': {'name': name, 'arguments': json.dumps(args)}}]}
            finish = 'tool_calls'
        else:
            message = {'role': 'assistant', 'content': 'Offline protocol test complete; not a real model result.'}
            finish = 'stop'
        return ChatCompletion.model_validate({'id': 'offline-test', 'created': 0, 'model': 'test-fixture',
            'object': 'chat.completion', 'choices': [{'index': 0, 'message': message, 'finish_reason': finish}],
            'usage': {'prompt_tokens': 10, 'completion_tokens': 10, 'total_tokens': 20}})


def fake_model(run, event):
    run['model'] = 'OFFLINE_PROTOCOL_TEST_ONLY'
    run['evidence_source'] = 'real_browser_with_scripted_test_model'
    return OpenAIModel(client=SimpleNamespace(chat=SimpleNamespace(completions=ScriptedModel())),
                       model_id='test-fixture', stream=False, params={'max_tokens': 2500})


def wait_run(store, owner, run_id):
    deadline = time.monotonic() + 160
    while time.monotonic() < deadline:
        run = store.run(owner, run_id)
        if run['state'] not in {'queued', 'running'}:
            return run
        time.sleep(.1)
    raise AssertionError('Worker did not complete in time')


class V1Tests(unittest.TestCase):
    def test_requirement_rejects_script_and_vacuous_check(self):
        with self.assertRaises(ValueError):
            Requirement.model_validate({'title': 'wrong', 'steps': [{'action': 'evaluate', 'value': 'fetch(...)'}] * 3})
        with self.assertRaises(ValueError):
            Requirement.model_validate({'title': 'wrong', 'steps': [{'action': 'add', 'value': 'x'}] * 3})

    def test_atomic_budget_survives_restart_and_counts_unknown_cost(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(tmp)
            def reserve(_):
                try:
                    store.reserve('test-run', 'test-model', .1, .51)
                    return 1
                except ValueError:
                    return 0
            with ThreadPoolExecutor(max_workers=12) as pool:
                self.assertEqual(sum(pool.map(reserve, range(20))), 5)
            again = Store(tmp)
            self.assertEqual(again.budget()['calls'], 5)
            self.assertAlmostEqual(again.budget()['unknown_reserved_cny'], .5)
            with self.assertRaises(ValueError):
                again.reserve('test-run', 'test-model', .1, .51)

    def test_versions_are_private_and_stale_writes_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(tmp)
            a, b = store.session(), store.session()
            av = store.version(a)
            with self.assertRaises(ValueError):
                store.version(b, av['id'])
            next_id = store.add_version(a, 'new', av['code'] + '\n', av['id'])
            with self.assertRaises(ValueError):
                store.add_version(a, 'stale', av['code'], av['id'])
            self.assertEqual(store.version(a)['id'], next_id)
            self.assertEqual(store.version(a, av['id'])['code'], av['code'])

    def test_real_browser_and_strands_repair_adopt_regression(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(tmp)
            owner = store.session()
            engine = Engine(store, fake_model)
            base = store.version(owner)
            run = engine.submit(owner, 'repair', '删除一个同名任务不应删除另一个', base['id'])
            done = wait_run(store, owner, run['id'])
            self.assertEqual(done['state'], 'ready', done.get('error', done))
            before = {c['id']: c['passed'] for c in done['before']['checks']}
            self.assertEqual(before, {'add_toggle': True, 'duplicate_identity': False, 'mixed_order': False, 'persistence': True})
            self.assertTrue(done['after']['all_passed'])
            self.assertEqual(done['after']['total'], 5)
            self.assertEqual(done['tool_calls'], ['read_project', 'run_checks', 'record_requirement', 'edit_app'])
            self.assertEqual(store.budget()['calls'], 0, 'Offline tests must not send any provider requests')
            adopted = engine.adopt(owner, done['id'], base['id'])
            self.assertEqual(len(store.requirements(owner)), 1)
            self.assertEqual(store.version(owner, base['id'])['code'], base['code'])
            with self.assertRaises(ValueError):
                engine.adopt(owner, done['id'], base['id'])
            store.switch(owner, base['id'], adopted)
            review = engine.submit(owner, 'recheck', expected=base['id'])
            result = wait_run(store, owner, review['id'])
            self.assertEqual(result['state'], 'issues_found')
            self.assertFalse(next(c for c in result['before']['checks'] if c['id'] == 'requirement_0')['passed'])
            for c in done['after']['checks']:
                self.assertTrue((store.root/'artifacts'/done['id']/'after-1'/c['screenshot']).is_file())
            engine.pool.shutdown(wait=True)

    def test_api_origin_validation_session_isolation_and_no_secret_leak(self):
        import coach.app as module
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(tmp)
            engine = Engine(store, fake_model)
            with patch.object(module, 'store', store), patch.object(module, 'engine', engine), patch.object(module, 'guard', Guard(store, engine)):
                with TestClient(module.app, base_url='http://localhost') as a, TestClient(module.app, base_url='http://localhost') as b:
                    sa = a.get('/api/state').json()
                    sb = b.get('/api/state').json()
                    self.assertNotEqual(sa['version']['id'], sb['version']['id'])
                    bad = a.post('/api/runs', headers={'Origin': 'https://evil.invalid'}, json={
                        'mode': 'diagnose', 'expected_version': sa['version']['id']})
                    self.assertEqual(bad.status_code, 403)
                    self.assertEqual(a.get('/api/state', headers={'host':'evil.invalid'}).status_code, 400)
                    self.assertEqual(a.post('/api/runs', content='x'*31000).status_code, 413)
                    reply = b.post('/api/versions', json={'action':'switch','version_id':sa['version']['id'],
                        'expected_version':sb['version']['id']})
                    self.assertEqual(reply.status_code, 409)
                    self.assertNotIn('DASHSCOPE_API_KEY=', json.dumps(sa))


if __name__ == '__main__':
    unittest.main()
