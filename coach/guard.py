"""Watch a dedicated session file, check changes, and optionally prepare a repair.

Only application-created files under data/workspaces are watched. No arbitrary host paths.
User adoption is always separate from autonomous verification and patch preparation.
"""
import os
import re
import threading
import time

from .settings import public_model
from .store import digest


class Guard:
    def __init__(self, store, engine):
        self.store, self.engine = store, engine
        self.lock = threading.RLock()
        self.stop_event = threading.Event()
        self.thread = None

    def path(self, owner):
        if not re.fullmatch(r'[a-f0-9]{32}', owner):
            raise ValueError('Invalid workspace')
        return self.store.root / 'workspaces' / owner / 'app.js'

    def status(self, owner):
        result = self.store.preferences(owner).get('guard', {})
        return {'enabled': False, 'auto_repair': False, 'phase': 'off', **result,
                'path': str(self.path(owner).resolve()) if os.environ.get('APP_PUBLIC') != 'true' else None}

    def save(self, owner, value):
        prefs = self.store.preferences(owner)
        prefs['guard'] = value
        self.store.save_preferences(owner, prefs)

    def write(self, owner, code):
        if not code.strip() or len(code.encode()) > 16000:
            raise ValueError('app.js 必须为 1–16000 字节')
        path = self.path(owner)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix('.tmp')
        temporary.write_text(code, encoding='utf-8')
        temporary.replace(path)

    def configure(self, owner, enabled, auto_repair=False, language='zh'):
        with self.lock:
            cfg = self.status(owner)
            cfg.pop('path', None)
            if enabled and not self.store.requirements(owner):
                raise ValueError('请先采用一个通过验收的修复，再开启持续守护')
            if enabled and not self.path(owner).exists():
                code = self.store.version(owner)['code']
                self.write(owner, code)
                cfg['seen_hash'] = digest(code)
            cfg.update(enabled=enabled, auto_repair=auto_repair, language=language,
                       phase='watching' if enabled else 'off', message='', updated=time.time())
            self.save(owner, cfg)
            return self.status(owner)

    def publish(self, owner, code):
        """Sync an adopted/imported version without overwriting a pending local edit."""
        with self.lock:
            cfg = self.status(owner)
            cfg.pop('path', None)
            if not cfg.get('enabled'):
                return
            path = self.path(owner)
            if path.exists() and (path.stat().st_size > 16000 or
                    digest(path.read_text(encoding='utf-8')) != cfg.get('seen_hash')):
                cfg.update(enabled=False, phase='conflict', message='文件同时发生了变化，守护已暂停；你的文件未被覆盖。')
            else:
                self.write(owner, code)
                cfg.update(seen_hash=digest(code), phase='watching', message='', pending_hash=None)
            self.save(owner, cfg)

    def change(self, owner, code):
        with self.lock:
            if not self.status(owner)['enabled']:
                raise ValueError('请先开启持续守护')
            self.write(owner, code)

    def tick(self):
        with self.lock:
            for owner in self.store.guarded_owners():
                cfg = self.status(owner)
                cfg.pop('path', None)
                if not cfg.get('enabled'):
                    continue
                try:
                    path = self.path(owner)
                    if not path.exists() or path.stat().st_size > 16000:
                        cfg.update(phase='blocked', message='守护文件缺失或超过 16000 字节，请修正文件。')
                        self.save(owner, cfg)
                        continue
                    code = path.read_text(encoding='utf-8')
                    code_hash = digest(code)
                    if code_hash != cfg.get('seen_hash'):
                        if cfg.get('pending_hash') != code_hash:
                            cfg.update(pending_hash=code_hash, pending_since=time.time(), phase='changed')
                        elif time.time() - cfg.get('pending_since', 0) >= 1 and not self.engine.active:
                            with self.engine.gate:
                                if self.engine.active:
                                    continue
                                version = self.store.version(owner)
                                new_id = self.store.add_version(owner, '文件变化 · ' + time.strftime('%H:%M:%S'), code, version['id'])
                                run = self.engine.submit(owner, 'recheck', '文件保存后自动复查', new_id,
                                                         trigger='file_change', language=cfg.get('language', 'zh'))
                            cfg.update(seen_hash=code_hash, phase='checking', last_run=run['id'],
                                       pending_hash=None, repair_hash=None, changes=cfg.get('changes', 0) + 1, message='')
                    elif cfg.get('last_run') and cfg.get('phase') in ('checking', 'repairing'):
                        run = self.store.run(owner, cfg['last_run'])
                        if run['state'] in ('queued', 'running') or self.engine.active:
                            continue
                        current = self.store.version(owner)
                        if current['id'] != run['base_version']:
                            cfg.update(phase='watching')
                        elif (cfg['phase'] == 'checking' and run['state'] == 'issues_found'
                                and cfg.get('auto_repair') and public_model()['configured']
                                and cfg.get('repair_hash') != code_hash):
                            failures = [c['label'] for c in run['before']['checks'] if not c['passed']]
                            symptom = '后续改版出现回归，请恢复以下要求并保留其他功能：' + '；'.join(failures)
                            repair = self.engine.submit(owner, 'repair', symptom, current['id'],
                                trigger='guard_repair', language=cfg.get('language', 'zh'))
                            cfg.update(phase='repairing', last_run=repair['id'], repair_hash=code_hash)
                        else:
                            cfg.update(phase='watching' if run['state'] in ('passed', 'adopted') else 'review')
                    self.save(owner, cfg)
                except (ValueError, OSError, UnicodeError):
                    cfg.update(phase='blocked', message='文件暂时无法检查；请检查格式，或等待当前任务完成后重新开启守护。')
                    self.save(owner, cfg)

    def start(self):
        if self.thread and self.thread.is_alive():
            return
        self.stop_event.clear()
        def loop():
            while not self.stop_event.wait(1.5):
                try:
                    self.tick()
                except Exception:
                    # A temporary filesystem/database failure must not kill the watcher.
                    continue
        self.thread = threading.Thread(target=loop, name='loopcheck-guard', daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=2)
