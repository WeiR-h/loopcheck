import test_support  # isolate storage before importing any application module
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from coach.browser_slot import browser_slot
from coach.projects import Projects
from coach.store import Store

class DeliveryTests(unittest.TestCase):
    def test_shared_browser_slot_serializes_and_cancels_waiter(self):
        acquired = threading.Event()
        def waiter():
            with browser_slot(): acquired.set()
        with browser_slot():
            thread = threading.Thread(target=waiter)
            thread.start()
            self.assertFalse(acquired.wait(.2))
            with self.assertRaisesRegex(ValueError, 'Cancelled'):
                with browser_slot(lambda: True): pass
        thread.join(timeout=2)
        self.assertTrue(acquired.is_set())

    def test_public_mode_denies_local_paths_import_and_bridge(self):
        import coach.app as module
        with tempfile.TemporaryDirectory() as tmp, patch.dict('os.environ', {'APP_PUBLIC':'true'}):
            # No model or browser call: only boundary and ownership checks.
            with TestClient(module.app, base_url='http://localhost') as client:
                p = client.post('/api/projects/sample').json()
                self.assertIn('id', p)
                self.assertTrue(client.get('/api/projects').json()['public'])
                self.assertNotIn('bridge_key', p)
                self.assertNotIn('root', p)
                self.assertEqual(client.post('/api/projects', json={'root':tmp,'url':'http://127.0.0.1:1234'}).status_code,409)
                self.assertEqual(client.post('/api/projects/'+p['id']+'/bridge-config').status_code,409)
                self.assertEqual(client.post('/api/projects/bridge/'+p['id']+'/check').status_code,403)
                self.assertEqual(client.post('/api/versions',json={'expected_version':'x','action':'import','code':'alert(1)'}).status_code,403)
            # Requirements stay bound to the original browser session.
            with TestClient(module.app, base_url='http://localhost') as stranger:
                self.assertEqual(stranger.get('/api/projects/'+p['id']+'/requirements').status_code,409)
