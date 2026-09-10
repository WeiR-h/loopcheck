"""First real-project gate: inject a disclosed regression in a temporary COPY only."""
import functools
import http.server
import json
from pathlib import Path
import shutil
import sys
import threading
import time
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests'))
from project_fixtures import BUDGET_FLOWS
from coach.project_browser import run_browser

def main(record_video=False):
    directory = ROOT / '.test-data' / ('project-gate-' + str(int(time.time())))
    project = directory / 'budget'
    shutil.copytree(ROOT / 'examples/budget', project)
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args): pass
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Quiet, directory=str(project)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f'http://127.0.0.1:{server.server_port}/'
    source = project / 'app.js'
    original = source.read_text(encoding='utf-8')
    try:
        before = run_browser(url, BUDGET_FLOWS, directory / 'before', record_video=record_video)
        source.write_text(original.replace('(i - e).toFixed(2)', '(i + e).toFixed(2)'), encoding='utf-8')
        regression = run_browser(url, BUDGET_FLOWS, directory / 'regression', record_video=record_video)
        source.write_text(original, encoding='utf-8')
        after = run_browser(url, BUDGET_FLOWS, directory / 'after', record_video=record_video)
        result = {'fixture': 'Original Pocket Budget; deliberately injected arithmetic fault in temporary copy',
                  'before': before, 'regression': regression, 'after': after, 'model_calls': 0}
        (directory / 'summary.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
        assert before['all_passed'], before
        assert not regression['all_passed'] and regression['checks'][0]['status'] == 'failed', regression
        assert after['all_passed'], after
        print(json.dumps({'gate': 'passed', 'flows': 3, 'cycles': 3, 'model_calls': 0, 'evidence': str(directory / 'summary.json')}))
    finally: server.shutdown()

if __name__ == '__main__': main('--record-video' in sys.argv)
