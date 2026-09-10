import test_support  # isolate storage before importing any application module
"""Exercise request serialization and budget settlement without provider traffic."""
import json
import tempfile
import unittest
from unittest.mock import patch

import httpx

from coach.models import BudgetModel
from coach.store import Store


class ModelAdapterTests(unittest.IsolatedAsyncioTestCase):
    async def test_qwen37_tool_request_and_persistent_cost(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(tmp)
            calls = []

            def respond(request):
                # Inspect the actual serialized HTTP body, including SDK extra_body.
                body = json.loads(request.content)
                calls.append(body)
                self.assertEqual(request.url.host, 'dashscope.aliyuncs.com')
                self.assertEqual(body['model'], 'qwen3.7-flash')
                self.assertIs(body['enable_thinking'], False)
                self.assertFalse(body['stream'])
                self.assertFalse(body['parallel_tool_calls'])
                self.assertEqual(body['max_tokens'], 2500)
                self.assertEqual(body['tools'][0]['function']['name'], 'read_project')
                self.assertAlmostEqual(store.budget()['unknown_reserved_cny'], .0084)
                return httpx.Response(200, json={
                    'id': 'adapter-test', 'created': 0, 'object': 'chat.completion',
                    'model': 'qwen3.7-flash', 'choices': [{'index': 0,
                        'message': {'role': 'assistant', 'content': None, 'tool_calls': [{
                            'id': 'call-1', 'type': 'function', 'function': {
                                'name': 'read_project', 'arguments': '{}'}}]},
                        'finish_reason': 'tool_calls'}],
                    'usage': {'prompt_tokens': 10000, 'completion_tokens': 2000,
                              'total_tokens': 12000}})

            config = {'provider': 'dashscope', 'model': 'qwen3.7-flash',
                      'key': 'test-only-not-a-real-key', 'budget_cny': 20}
            async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
                with patch('coach.models.settings', return_value=config):
                    model = BudgetModel(store, 'adapter-test')
                model.client_args['http_client'] = client
                events = [event async for event in model.stream(
                    [{'role': 'user', 'content': [{'text': 'Inspect the example'}]}],
                    [{'name': 'read_project', 'description': 'Read the example code',
                      'inputSchema': {'json': {'type': 'object', 'properties': {}}}}])]
            self.assertEqual(len(calls), 1)
            self.assertTrue(any('contentBlockStart' in e and
                e['contentBlockStart'].get('start', {}).get('toolUse', {}).get('name') == 'read_project'
                for e in events))
            budget = Store(tmp).budget()
            self.assertEqual(budget['calls'], 1)
            self.assertAlmostEqual(budget['reported_cny'], .0036)
            self.assertEqual(budget['unknown_reserved_cny'], 0)


if __name__ == '__main__':
    unittest.main()
