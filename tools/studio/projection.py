"""Read-only, bounded projections of the v0.2-A SQLite contract.

No Store writer is imported. No raw logs, argv, prompt, authorization, session
transcripts or arbitrary artifact paths are exposed to a browser. WAL remains
visible (mode=ro, not immutable=1). A recorded RUNNING is not proof of liveness.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import re
import socket
import sqlite3
import time
from .graph import digest, from_task

STATES = {'CREATED', 'PREFLIGHT', 'IMPLEMENTING', 'SNAPSHOTTING', 'VERIFYING', 'REVIEWING', 'GATING',
          'READY', 'COMMITTING', 'LOCAL_COMMITTED', 'PUSHING', 'COMPLETED', 'BLOCKED', 'RECOVERING', 'CANCELLED', 'PARTIAL_DELIVERY'}
PHASE = {'CREATED': 'authorization', 'PREFLIGHT': 'authorization', 'IMPLEMENTING': 'implementer',
         'SNAPSHOTTING': 'freeze', 'VERIFYING': 'verification', 'REVIEWING': 'reviewer',
         'GATING': 'gate', 'READY': 'gate', 'COMMITTING': 'delivery', 'PUSHING': 'delivery',
         'LOCAL_COMMITTED': 'delivery', 'COMPLETED': 'delivery', 'PARTIAL_DELIVERY': 'delivery'}
ACTIVE = {'IMPLEMENTING', 'REVIEWING', 'VERIFYING', 'COMMITTING', 'PUSHING'}
TOKEN = re.compile(r'[A-Za-z0-9_.:/@\[\]-]{1,160}\Z')
HASH = re.compile(r'[0-9a-f]{40}(?:[0-9a-f]{24})?\Z')
EVENT_KINDS = STATES | {'INTENT', 'RUNNING', 'EXITED', 'AGENT_COMPLETED', 'AGENT_FAILED', 'COMMITTED', 'PUSHED', 'PUSH_UNKNOWN', 'REMOTE_CONFLICT', 'RETRYING'}


class Unavailable(ValueError):
    pass


def token(value):
    return value if isinstance(value, str) and TOKEN.fullmatch(value) else 'unknown'


def sha(value):
    return value if isinstance(value, str) and HASH.fullmatch(value) else None


def counts(value):
    keys = ('tests', 'failures', 'errors', 'skipped')
    if not isinstance(value, dict) or any(type(value.get(k)) is not int or value[k] < 0 for k in keys):
        return None
    return {k: value[k] for k in keys}


def liveness(record):
    if not isinstance(record, dict) or type(record.get('pid')) is not int:
        return 'unconfirmed'
    try:
        if record['host'] != socket.gethostname() or record['boot_id'] != Path('/proc/sys/kernel/random/boot_id').read_text().strip():
            return 'unconfirmed'
        fields = Path(f'/proc/{record["pid"]}/stat').read_text().rsplit(')', 1)[1].split()
        return 'alive' if record['start'] == fields[19] and fields[0] != 'Z' else 'not_alive'
    except (OSError, KeyError, IndexError):
        return 'unconfirmed'


class Reader:
    def __init__(self, control):
        self.control = Path(control).resolve() if control else None

    def connect(self):
        if self.control is None:
            raise Unavailable('No control directory configured')
        path = self.control / 'state.sqlite'
        if path.is_symlink() or not path.is_file():
            raise Unavailable('Controller database is not available')
        for suffix in ('-wal', '-shm', '-journal'):
            if Path(str(path) + suffix).is_symlink():
                raise Unavailable('Database sidecar must not be a symlink')
        db = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=0.25)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA query_only=ON')
        db.execute('PRAGMA trusted_schema=OFF')
        db.execute('BEGIN')
        deadline = time.monotonic() + 1
        db.set_progress_handler(lambda: int(time.monotonic() > deadline), 1000)
        return db

    def list_runs(self):
        db = self.connect()
        try:
            # Only extract approved fields; never return full data from this endpoint.
            rows = db.execute('SELECT id,state,data FROM runs WHERE length(data)<8388608 ORDER BY rowid DESC LIMIT 100').fetchall()
            result = []
            for row in rows:
                data = json.loads(row['data']); config = data.get('config', {})
                result.append({'id': token(row['id']), 'state': row['state'] if row['state'] in STATES else 'UNKNOWN',
                               'project': token(config.get('project')), 'task_id': token(config.get('task_id')),
                               'round': data.get('round', 0), 'config_sha256': digest(config)})
            return result
        finally:
            db.close()

    def snapshot(self, run):
        if not isinstance(run, str) or not re.fullmatch(r'[a-f0-9]{32}', run):
            raise Unavailable('Invalid run ID')
        db = self.connect()
        try:
            row = db.execute('SELECT state,data FROM runs WHERE id=? AND length(data)<8388608', (run,)).fetchone()
            if row is None:
                raise Unavailable('Run not found or record exceeds the display budget')
            data = json.loads(row['data']); state = row['state'] if row['state'] in STATES else 'UNKNOWN'
            rows = db.execute('SELECT seq,at,kind,data FROM events WHERE run=? AND length(data)<8388608 ORDER BY seq DESC LIMIT 200', (run,)).fetchall()[::-1]
            events = [{**dict(r), 'data': json.loads(r['data'])} for r in rows]
            op = db.execute("SELECT status,data FROM operations WHERE run=? AND kind='PROCESS' AND length(data)<8388608 ORDER BY rowid DESC LIMIT 1", (run,)).fetchone()
            process = json.loads(op['data']) if op else {}
            live = liveness(process.get('process')) if op and op['status'] == 'RUNNING' else 'unconfirmed'
            active_test = None
            if state == 'VERIFYING' and live == 'alive':
                argv = process.get('argv', [])
                matches = [v.get('id') for v in data.get('config', {}).get('policy', {}).get('verification', [])
                           if len(argv) == len(v.get('argv', [])) and all(
                               '{result}' in a or '{artifacts}' in a or a == b for a, b in zip(v['argv'], argv))]
                if len(matches) == 1:
                    active_test = matches[0]
            return project(run, state, data, events, live, active_test)
        finally:
            db.close()


def project(run, state, data, events, live, active_test=None):
    config = data.get('config', {}); number = data.get('round', 0)
    graph = from_task(config)
    graph['limits'] = {k: v for k, v in graph['limits'].items() if k in ('max_review_rounds', 'max_infrastructure_retries', 'step_timeout_seconds', 'max_log_bytes') and type(v) is int}
    graph['goal'] = ''  # Never project raw prompts/source into the monitor.
    graph['name'] = token(config.get('task_id'))
    for node in graph['nodes']:
        node['label'] = token(node['config'].get('id')) if node['type'] == 'verification' else node['label']
        if node['type'] == 'verification':
            node['config'] = {'id': token(node['config'].get('id'))}
        elif node['type'] in ('implementer', 'reviewer'):
            node['config'] = {k: token(v) for k, v in node['config'].items()}
    stage = PHASE.get(state)
    if stage is None:
        stage = next((PHASE[e['kind']] for e in reversed(events) if e['kind'] in PHASE), None)
    sequence = ['authorization', 'implementer', 'freeze', 'verification', 'reviewer', 'gate', 'delivery']
    phase_index = sequence.index(stage) if stage in sequence else -1
    results = {token(v.get('id')): v for v in data.get('verification', []) if v.get('round') == number}
    review = data.get('review', {}).get('report', {})
    if review.get('round') != number:
        review = {}
    verdict = review.get('verdict') if review.get('verdict') in ('ACCEPT', 'ACCEPT_WITH_LIMITATIONS', 'NEEDS_CORRECTION', 'BLOCKED') else None
    for node in graph['nodes']:
        kind = node['type']; index = sequence.index(kind)
        status = 'completed' if 0 <= index < phase_index else 'pending'
        if kind == stage:
            if state in ('BLOCKED', 'RECOVERING', 'UNKNOWN'):
                status = 'blocked'
            elif state == 'CANCELLED':
                status = 'cancelled'
            elif state == 'PARTIAL_DELIVERY':
                status = 'partial'
            elif state in ('READY', 'LOCAL_COMMITTED', 'COMPLETED'):
                status = 'completed'
            else:
                status = 'running' if live == 'alive' else 'unconfirmed'
        if kind == 'verification':
            result = results.get(node['config']['id'])
            if state == 'VERIFYING' and not result:
                status = 'running' if active_test == node['config']['id'] and live == 'alive' else 'pending'
            node['counts'] = counts(result.get('counts')) if result else None
            if result:
                node['status'] = 'passed' if result.get('passed') is True else 'failed'
                status = node['status']
        if kind == 'reviewer' and verdict:
            status = {'ACCEPT': 'passed', 'NEEDS_CORRECTION': 'needs_correction', 'BLOCKED': 'blocked', 'ACCEPT_WITH_LIMITATIONS': 'blocked'}[verdict]
        if kind == 'delivery' and not config.get('policy', {}).get('delivery', {}).get('commit'):
            status = 'disabled'
        if kind in ('implementer', 'reviewer'):
            agent = data.get('implementation' if kind == 'implementer' else 'review', {})
            node['resolved_model'] = token(agent.get('resolved_model')) if (kind == 'reviewer' and verdict or kind == 'implementer' and phase_index >= 5) else 'unknown'
        node['status'] = status
    reports = {}
    for report in data.get('reviews', []) + data.get('history', []):
        if type(report.get('round')) is int:
            reports[(report['round'], report.get('candidate_sha256'))] = report
    rounds = [{'round': key[0], 'candidate': sha(key[1]), 'verdict': token(r.get('verdict')),
               'open_findings': sum(f.get('status') != 'CLOSED' for f in r.get('findings', []))}
              for key, r in sorted(reports.items(), key=lambda pair: pair[0][0])][-20:]
    timeline = [{'seq': e['seq'], 'at': e['at'], 'kind': e['kind'] if e['kind'] in EVENT_KINDS else 'OTHER',
                 'round': e['data'].get('round') if type(e['data'].get('round')) is int else None} for e in events]
    messages = {'READY': '候选通过门禁；交付仍需独立授权和 deliver。', 'BLOCKED': '运行被阻断；请在受控终端检查 audit，不要自动放宽验收。',
                'RECOVERING': '正在核验恢复前置条件。', 'CANCELLED': '运行已取消；不表示此前 Git 副作用已回滚。',
                'LOCAL_COMMITTED': '提交已持久保存到内部 ref；没有推送。', 'PARTIAL_DELIVERY': '部分交付；不得回滚已成功远端。'}
    return {'id': run, 'state': state, 'round': number, 'project': token(config.get('project')),
            'mode': config.get('policy', {}).get('mode') if config.get('policy', {}).get('mode') in ('A', 'B', 'C') else 'unknown',
            'candidate': sha(data.get('candidate', {}).get('sha256')), 'config_sha256': digest(config),
            'graph': graph, 'rounds': rounds, 'events': timeline, 'process_liveness': live,
            'observed_at': time.time(), 'message': messages.get(state, '状态来自 Controller；无进程身份时不宣称 Agent 正在工作。'),
            'delivery': [{'kind': token(r.get('kind')), 'commit': sha(r.get('commit')), 'pushed': r.get('pushed') is True}
                         for r in data.get('receipts', [])[:2]], 'verdict': verdict}
