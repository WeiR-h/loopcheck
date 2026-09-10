"""Persistent, session-scoped versions and reports; global conservative API budget."""
from contextlib import closing, contextmanager
import hashlib
import json
from pathlib import Path
import sqlite3
import threading
import time
import uuid

from .settings import DATA, FIXTURES


def uid():
    return uuid.uuid4().hex


def digest(code):
    return hashlib.sha256(code.encode()).hexdigest()


class Store:
    def __init__(self, root=DATA):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / 'loopcheck.sqlite3'
        self.lock = threading.RLock()
        with self.db() as db:
            db.executescript('''
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, active TEXT, created REAL);
                CREATE TABLE IF NOT EXISTS versions (id TEXT PRIMARY KEY, owner TEXT, name TEXT, code TEXT,
                    hash TEXT, parent TEXT, created REAL);
                CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, owner TEXT, state TEXT, payload TEXT, created REAL);
                CREATE TABLE IF NOT EXISTS requirements (id TEXT PRIMARY KEY, owner TEXT, title TEXT, spec TEXT,
                    run_id TEXT, created REAL, UNIQUE(owner, spec));
                CREATE TABLE IF NOT EXISTS calls (id TEXT PRIMARY KEY, run_id TEXT, model TEXT, reserved REAL,
                    cost REAL, input_tokens INTEGER, output_tokens INTEGER, state TEXT, created REAL);
                CREATE TABLE IF NOT EXISTS preferences (owner TEXT PRIMARY KEY, payload TEXT);
            ''')

    @contextmanager
    def db(self):
        with closing(sqlite3.connect(self.path, timeout=10)) as db:
            db.row_factory = sqlite3.Row
            with db:
                yield db

    def session(self, session_id=None):
        with self.lock, self.db() as db:
            row = db.execute('SELECT * FROM sessions WHERE id=?', (session_id,)).fetchone()
            if row:
                return row['id']
            owner, version = uid(), uid()
            code = (FIXTURES / 'app.js').read_text(encoding='utf-8')
            db.execute('INSERT INTO sessions VALUES (?,?,?)', (owner, version, time.time()))
            db.execute('INSERT INTO versions VALUES (?,?,?,?,?,?,?)',
                       (version, owner, '初始示例 · 含同名误删', code, digest(code), None, time.time()))
            return owner

    def version(self, owner, version_id=None):
        with self.db() as db:
            if not version_id:
                row = db.execute('SELECT active FROM sessions WHERE id=?', (owner,)).fetchone()
                version_id = row['active'] if row else None
            row = db.execute('SELECT * FROM versions WHERE owner=? AND id=?', (owner, version_id)).fetchone()
            if not row:
                raise ValueError('版本不存在')
            return dict(row)

    def versions(self, owner):
        with self.db() as db:
            return [dict(r) for r in db.execute(
                'SELECT id,name,hash,parent,created FROM versions WHERE owner=? ORDER BY created DESC', (owner,))]

    def switch(self, owner, version_id, expected):
        with self.lock, self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT active FROM sessions WHERE id=?', (owner,)).fetchone()
            if not row or row['active'] != expected:
                raise ValueError('版本已经变化，请刷新后重试')
            if not db.execute('SELECT id FROM versions WHERE id=? AND owner=?', (version_id, owner)).fetchone():
                raise ValueError('版本不存在')
            db.execute('UPDATE sessions SET active=? WHERE id=?', (version_id, owner))

    def add_version(self, owner, name, code, expected, requirement=None, run_id=None):
        if len(code.encode()) > 16_000 or not code.strip():
            raise ValueError('app.js 必须为 1–16000 字节')
        with self.lock, self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT active FROM sessions WHERE id=?', (owner,)).fetchone()
            if not row or row['active'] != expected:
                raise ValueError('代码已更新，旧补丁未被采用；请针对当前版本重新检查')
            version_id = uid()
            db.execute('INSERT INTO versions VALUES (?,?,?,?,?,?,?)',
                       (version_id, owner, name[:100], code, digest(code), expected, time.time()))
            db.execute('UPDATE sessions SET active=? WHERE id=?', (version_id, owner))
            if requirement:
                spec = json.dumps(requirement, ensure_ascii=False, sort_keys=True)
                db.execute('INSERT OR IGNORE INTO requirements VALUES (?,?,?,?,?,?)',
                           (uid(), owner, requirement['title'], spec, run_id, time.time()))
            return version_id

    def requirements(self, owner):
        with self.db() as db:
            return [dict(r) | {'spec': json.loads(r['spec'])} for r in db.execute(
                'SELECT * FROM requirements WHERE owner=? ORDER BY created', (owner,))]

    def preferences(self, owner):
        with self.db() as db:
            row = db.execute('SELECT payload FROM preferences WHERE owner=?', (owner,)).fetchone()
            return json.loads(row['payload']) if row else {}

    def save_preferences(self, owner, value):
        with self.lock, self.db() as db:
            db.execute('INSERT INTO preferences VALUES (?,?) ON CONFLICT(owner) DO UPDATE SET payload=excluded.payload',
                       (owner, json.dumps(value, ensure_ascii=False)))

    def guarded_owners(self):
        with self.db() as db:
            return [r['owner'] for r in db.execute('SELECT owner FROM preferences')]

    def save_run(self, run):
        with self.lock, self.db() as db:
            db.execute('INSERT INTO runs VALUES (?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET state=excluded.state,payload=excluded.payload',
                       (run['id'], run['owner'], run['state'], json.dumps(run, ensure_ascii=False), run['created']))

    def run(self, owner, run_id):
        with self.db() as db:
            row = db.execute('SELECT payload FROM runs WHERE owner=? AND id=?', (owner, run_id)).fetchone()
            if not row:
                raise ValueError('运行记录不存在')
            return json.loads(row['payload'])

    def runs(self, owner):
        with self.db() as db:
            return [json.loads(r['payload']) for r in db.execute(
                'SELECT payload FROM runs WHERE owner=? ORDER BY created DESC LIMIT 30', (owner,))]

    def interrupt_old_runs(self):
        with self.db() as db:
            rows = list(db.execute("SELECT payload FROM runs WHERE state IN ('queued','running')"))
        for row in rows:
            run = json.loads(row['payload'])
            run.update(state='interrupted', error='服务重启，任务已中断；原版本保持可恢复，重新检查后再采用', finished=time.time())
            self.save_run(run)

    def reserve(self, run_id, model, amount, limit):
        with self.lock, self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            total = db.execute('SELECT COALESCE(SUM(COALESCE(cost,reserved)),0) FROM calls').fetchone()[0]
            count = db.execute('SELECT COUNT(*) FROM calls WHERE run_id=?', (run_id,)).fetchone()[0]
            if count >= 8:
                raise ValueError('本次已达到 8 次模型请求上限')
            if total + amount > limit:
                raise ValueError('已达到本项目模型费用上限，请先核对账单与预留预算')
            call = uid()
            db.execute('INSERT INTO calls VALUES (?,?,?,?,?,?,?,?,?)',
                       (call, run_id, model, amount, None, None, None, 'reserved', time.time()))
            return call

    def settle(self, call, usage, input_price, output_price):
        inp, out = usage.get('inputTokens'), usage.get('outputTokens')
        if inp is None or out is None:
            return
        cost = (inp * input_price + out * output_price) / 1_000_000
        with self.db() as db:
            db.execute('UPDATE calls SET cost=?,input_tokens=?,output_tokens=?,state=? WHERE id=?',
                       (cost, inp, out, 'reported', call))

    def budget(self, run_id=None):
        where, args = (' WHERE run_id=?', (run_id,)) if run_id else ('', ())
        with self.db() as db:
            r = db.execute('SELECT COUNT(*) calls,COALESCE(SUM(cost),0) reported_cny, '
                'COALESCE(SUM(CASE WHEN cost IS NULL THEN reserved ELSE 0 END),0) unknown_reserved_cny, '
                'COALESCE(SUM(input_tokens),0) input_tokens,COALESCE(SUM(output_tokens),0) output_tokens FROM calls' + where, args).fetchone()
            return dict(r)
