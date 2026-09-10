import json
import os
from pathlib import Path
import signal
import subprocess
import sys

from .settings import ROOT


def validate(code, directory, requirements=None, baseline=True):
    from .browser_slot import browser_slot
    try:
        with browser_slot():
            return _validate(code, directory, requirements, baseline)
    except ValueError as exc:
        return {'error': str(exc), 'checks': [], 'all_passed': False}


def _validate(code, directory, requirements=None, baseline=True):
    directory = Path(directory).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    source = directory / 'input.json'
    output = directory / 'result.json'
    source.write_text(json.dumps({'code': code, 'requirements': requirements or [], 'baseline': baseline,
                                 'artifacts': str(directory)}, ensure_ascii=False), encoding='utf-8')
    # Child browser process never inherits provider keys or the user's other environment secrets.
    env = {k: v for k, v in os.environ.items() if k.upper() in {
        'SYSTEMROOT', 'WINDIR', 'PATH', 'PATHEXT', 'TEMP', 'TMP', 'USERPROFILE', 'LOCALAPPDATA', 'HOME',
    }}
    env.update(PYTHONUTF8='1', PLAYWRIGHT_BROWSERS_PATH=os.environ.get('PLAYWRIGHT_BROWSERS_PATH', str(ROOT / '.browsers')))
    args = [sys.executable, '-m', 'coach.runner', str(source), str(output)]
    options = {'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {'start_new_session': True}
    process = subprocess.Popen(args, cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **options)
    try:
        process.wait(timeout=60)
    except subprocess.TimeoutExpired:
        if os.name == 'nt':
            subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], capture_output=True, timeout=10)
        else:
            os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=10)
        return {'checks': [], 'all_passed': False, 'error': '浏览器检查超过 60 秒，已停止本次隔离运行', 'source': 'real_playwright_chromium'}
    if process.returncode != 0 or not output.is_file():
        return {'checks': [], 'all_passed': False, 'error': '浏览器未能启动，请先运行安装脚本', 'source': 'real_playwright_chromium'}
    return json.loads(output.read_text(encoding='utf-8'))
