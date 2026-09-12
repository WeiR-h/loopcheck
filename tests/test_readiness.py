import test_support
import http.server
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from coach.readiness import inspect, preview_link, probe_preview
from coach.projects import Projects
from coach.store import Store


class ReadinessTests(unittest.TestCase):
    def test_public_preview_and_private_diagnostics(self):
        import coach.app as module
        with patch.dict(os.environ, {'APP_PUBLIC': 'true', 'DASHSCOPE_API_KEY': ''}):
            with TestClient(module.app, base_url='http://localhost') as client:
                project = client.post('/api/projects/sample').json()
                before = client.get('/api/projects').json()
                p = next(p for p in before['projects'] if p['id'] == project['id'])
                self.assertEqual(p['preview_url'], '/samples/budget/')
                with patch('coach.readiness.probe_preview', return_value={'ready': True, 'reason': 'reachable'}):
                    readiness = client.get('/api/projects/'+p['id']+'/readiness').json()
                self.assertTrue(readiness['source']['ready'])
                self.assertFalse(readiness['model']['can_start'])
                self.assertFalse(readiness['can_plan'])
                self.assertFalse(readiness['can_recheck'])
                self.assertNotIn('root', readiness)
                self.assertEqual(before['budget'], client.get('/api/projects').json()['budget'])
                live = client.post('/api/projects/sample/public/shopping').json()
                self.assertEqual(live['name'], 'MDN Shopping List')
                self.assertIsNone(live['contract_id'])
                self.assertEqual(client.get('/samples/public/shopping/').status_code, 200)
                self.assertEqual(client.post('/api/projects/sample/public/not-a-sample').status_code, 404)
            with TestClient(module.app, base_url='http://localhost') as stranger:
                with patch('coach.readiness.probe_preview') as probe:
                    self.assertEqual(stranger.get('/api/projects/'+p['id']+'/readiness').status_code, 409)
                    probe.assert_not_called()

    def test_preview_probe_reachable_redirect_and_stopped(self):
        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_GET(self):
                self.send_response(302 if self.path == '/redirect' else 200)
                if self.path == '/redirect': self.send_header('Location', 'https://example.com/')
                self.end_headers()
        server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        url = f'http://127.0.0.1:{server.server_port}'
        try:
            self.assertTrue(probe_preview(url+'/')['ready'])
            self.assertEqual(probe_preview(url+'/redirect')['reason'], 'redirect')
        finally:
            server.shutdown(); server.server_close(); thread.join()
        self.assertFalse(probe_preview(url+'/')['ready'])

    def test_budget_exhaustion_does_not_disable_browser_recheck(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {'APP_PUBLIC':'false', 'DASHSCOPE_API_KEY':'test-only-placeholder', 'MODEL_BUDGET_CNY':'0'}):
            folder = Path(tmp)/'project'; folder.mkdir(); (folder/'index.html').write_text('<p>Demo</p>')
            store = Store(Path(tmp)/'state'); service = Projects(store)
            owner = store.session(); p = service.connect(owner, folder, 'http://127.0.0.1:12345/')
            with patch.object(service, 'current_requirements', return_value=[{'enabled':True, 'flow':None}]), patch('coach.readiness.probe_preview', return_value={'ready':True}):
                result = inspect(service, owner, p['id'])
            self.assertFalse(result['can_plan'])
            self.assertTrue(result['can_recheck'])
            self.assertEqual(result['uncovered_requirements'], 1)
            self.assertEqual(store.budget()['calls'], 0)
            service.pool.shutdown()

    def test_public_link_never_exposes_arbitrary_local_url(self):
        p = {'sample':False, 'url':'http://localhost:12345/private'}
        self.assertIsNone(preview_link(p, True))
        self.assertEqual(preview_link(p), p['url'])
        self.assertIsNone(preview_link({'sample':True,'url':'http://localhost:12345/private'}, True))
