"""Transactional state, append-only events, and kernel-held identity-aware leases."""
from __future__ import annotations
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import socket
import sqlite3
import time
import uuid
from .common import Blocked, canonical

STATES = {'CREATED', 'PREFLIGHT', 'PLANNING', 'IMPLEMENTING', 'SNAPSHOTTING', 'VERIFYING', 'REVIEWING', 'GATING',
          'READY', 'AWAITING_HUMAN', 'COMMITTING', 'LOCAL_COMMITTED', 'PUSHING', 'COMPLETED', 'BLOCKED', 'RECOVERING', 'CANCELLED', 'PARTIAL_DELIVERY'}


def process_identity(pid):
    try:
        # comm may contain spaces or ')'. starttime is field 22.
        fields = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()
        return {'host': socket.gethostname(), 'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                'pid': pid, 'start': fields[19], 'state': fields[0], 'pgid': int(fields[2]), 'sid': int(fields[3])}
    except (OSError, IndexError, ValueError):
        return None


def alive(record):
    now = process_identity(record['pid']) if record else None
    return bool(now and now['state'] != 'Z' and all(now[k] == record[k] for k in ('host', 'boot_id', 'pid', 'start')))


@contextmanager
def lease(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a+') as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise Blocked('live lease held') from None
        stream.seek(0)
        stream.truncate()
        stream.write(canonical(process_identity(os.getpid())).decode())
        stream.flush()
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


class Store:
    def __init__(self, directory, readonly=False):
        self.directory = Path(directory).resolve()
        if not readonly:
            self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        db = self.directory / 'state.sqlite'
        self.db = sqlite3.connect(f'file:{db}?mode=ro', uri=True) if readonly else sqlite3.connect(db)
        self.db.row_factory = sqlite3.Row
        if not readonly:
            self.db.execute('PRAGMA journal_mode=WAL')
            self.db.execute('PRAGMA synchronous=FULL')
            self.db.executescript('''
              CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY, state TEXT NOT NULL, data TEXT NOT NULL);
              CREATE TABLE IF NOT EXISTS events(seq INTEGER PRIMARY KEY, run TEXT, at REAL, kind TEXT, data TEXT);
              CREATE TABLE IF NOT EXISTS operations(id TEXT PRIMARY KEY, run TEXT, kind TEXT, status TEXT, data TEXT);
            ''')

    def create(self, data):
        run = uuid.uuid4().hex
        with self.db:
            self.db.execute('INSERT INTO runs VALUES(?,?,?)', (run, 'CREATED', canonical(data).decode()))
            self._event(run, 'CREATED', {})
        return run

    def _event(self, run, kind, data):
        self.db.execute('INSERT INTO events(run,at,kind,data) VALUES(?,?,?,?)',
                        (run, time.time(), kind, canonical(data).decode()))

    def get(self, run):
        row = self.db.execute('SELECT * FROM runs WHERE id=?', (run,)).fetchone()
        if row is None:
            raise Blocked('unknown run')
        return {'id': row['id'], 'state': row['state'], 'data': json.loads(row['data'])}

    def transition(self, run, state, **updates):
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            current = self.get(run)
            state = current['state'] if state is None else state
            if state not in STATES:
                raise Blocked('unknown run state')
            if current['state'] in ('CANCELLED', 'COMPLETED') and state != current['state']:
                raise Blocked('terminal run')
            data = dict(current['data'], **updates)
            if state in ('READY', 'COMMITTING') and data.get('cancel_requested') and state != current['state']:
                state = 'CANCELLED'
            self.db.execute('UPDATE runs SET state=?,data=? WHERE id=?', (state, canonical(data).decode(), run))
            self._event(run, state, updates)

    def intent(self, run, kind, data):
        op = uuid.uuid4().hex
        with self.db:
            self.db.execute('INSERT INTO operations VALUES(?,?,?,?,?)', (op, run, kind, 'INTENT', canonical(data).decode()))
            self._event(run, 'INTENT', {'operation': op, 'kind': kind})
        return op

    def finish(self, op, status, **updates):
        with self.db:
            row = self.db.execute('SELECT * FROM operations WHERE id=?', (op,)).fetchone()
            data = dict(json.loads(row['data']), **updates)
            self.db.execute('UPDATE operations SET status=?,data=? WHERE id=?', (status, canonical(data).decode(), op))
            self._event(row['run'], status, {'operation': op, **updates})

    def operations(self, run):
        return [{**dict(r), 'data': json.loads(r['data'])} for r in self.db.execute('SELECT * FROM operations WHERE run=? ORDER BY rowid', (run,))]

    def audit(self, run, after=0, limit=50):
        return [{**dict(r), 'data': json.loads(r['data'])} for r in self.db.execute(
            'SELECT * FROM events WHERE run=? AND seq>? ORDER BY seq LIMIT ?', (run, after, min(max(limit, 1), 200)))]
