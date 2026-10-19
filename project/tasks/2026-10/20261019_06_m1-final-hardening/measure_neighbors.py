"""Reproducible local baseline; synthetic rows are NOT Clang semantic evidence."""
import argparse
import hashlib
import json
import os
import platform
from pathlib import Path
import shutil
import sqlite3
import statistics
import subprocess
import sys
import time
from unittest.mock import patch

from codeweave import index as kernel


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def synthetic(path, targets, repeats=1, cycle=False, filler=0, anchor_size=0):
    """One center, explicit distinct call instances, optional unrelated corpus."""
    connection = sqlite3.connect(path)
    connection.executescript(kernel.SCHEMA)
    connection.execute('PRAGMA foreign_keys=ON')
    connection.execute("INSERT INTO indexes VALUES ('synthetic','now','synthetic','hash','/owned','synthetic','',3,'{}')")
    content = b'// Synthetic scale rows; no C++ semantic claim.\n' * (2 * repeats * targets + filler + 10)
    connection.execute("INSERT INTO files VALUES ('synthetic','/owned/unit.cpp',?,?,'project')", (content, hashlib.sha256(content).hexdigest()))
    connection.execute("INSERT INTO units VALUES ('synthetic','/owned/unit.cpp','synthetic','ok','[]','{}')")
    size = max(targets + 1, filler // 5 + 2)
    anchor = json.dumps({'synthetic': True, 'payload': 'x' * anchor_size})
    connection.executemany("INSERT INTO symbols VALUES ('synthetic',?,?,'function','/owned/unit.cpp',1,1,'/owned/unit.cpp',1,1,?)",
                           ((f'n{i}', f'node{i}', anchor) for i in range(size)))
    connection.executemany("INSERT INTO symbol_units VALUES ('synthetic',?,'/owned/unit.cpp')", ((f'n{i}',) for i in range(size)))
    calls = []
    for repeat in range(repeats):
        for target in range(1, targets + 1):
            calls.append(('n0', f'n{target}', 'virtual' if target == 1 else 'direct'))
            if cycle:
                calls.append((f'n{target}', 'n0', 'direct'))
    # Filler is unrelated to n0, so growing the corpus does not change its oracle.
    calls += [(f'n{1 + i % (size - 1)}', f'n{1 + (i + 1) % (size - 1)}', 'direct') for i in range(filler)]
    connection.executemany("INSERT INTO calls(index_id,instance_id,caller_usr,target_usr,dispatch,file,line,column_number,anchors) VALUES ('synthetic',?,?,?,?,'/owned/unit.cpp',?,1,?)",
                           ((f'call{i}', a, b, dispatch, i + 1, '{}') for i, (a, b, dispatch) in enumerate(calls)))
    connection.executemany("INSERT INTO call_units VALUES ('synthetic',?,'/owned/unit.cpp')", ((f'call{i}',) for i in range(len(calls))))
    connection.commit()
    assert not connection.execute('PRAGMA foreign_key_check').fetchall()
    connection.close()
    return {'symbols': size, 'calls': len(calls), 'center': 'n0', 'index_id': 'synthetic', 'oracle': calls}


def measured(path, center, active, limit, samples):
    before = sha(path)
    sql = {'persistent': [], 'schema_memory': []}
    connects = {'persistent': 0, 'schema_memory': 0}
    write_attempts = []
    original = sqlite3.connect
    write_actions = {sqlite3.SQLITE_INSERT, sqlite3.SQLITE_UPDATE, sqlite3.SQLITE_DELETE,
                     sqlite3.SQLITE_CREATE_TABLE, sqlite3.SQLITE_DROP_TABLE, sqlite3.SQLITE_ALTER_TABLE,
                     sqlite3.SQLITE_CREATE_INDEX, sqlite3.SQLITE_DROP_INDEX, sqlite3.SQLITE_ATTACH, sqlite3.SQLITE_DETACH}

    def tracked(database, *args, **kwargs):
        kind = 'schema_memory' if database == ':memory:' else 'persistent'
        connects[kind] += 1
        if kind == 'persistent':
            assert kwargs.get('uri') and str(database).endswith('?mode=ro'), database
        conn = original(database, *args, **kwargs)
        conn.set_trace_callback(lambda statement: sql[kind].append(statement))
        if kind == 'persistent':
            def authorizer(action, arg1, arg2, db_name, trigger):
                if action in write_actions:
                    write_attempts.append([action, arg1, arg2])
                    return sqlite3.SQLITE_DENY
                return sqlite3.SQLITE_OK
            conn.set_authorizer(authorizer)
        return conn

    with patch.object(kernel.sqlite3, 'connect', tracked):
        result = kernel.query(path, 'neighbors', center, active, limit=limit)
    assert not write_attempts
    for _ in range(3):
        assert kernel.query(path, 'neighbors', center, active, limit=limit) == result
    milliseconds = []
    for _ in range(samples):
        start = time.perf_counter_ns()
        current = kernel.query(path, 'neighbors', center, active, limit=limit)
        milliseconds.append((time.perf_counter_ns() - start) / 1e6)
        assert current == result
    assert sha(path) == before
    byte_count = len((json.dumps(result, sort_keys=True) + '\n').encode())
    assert byte_count <= kernel.MAX_QUERY_BYTES
    stats = {'limit': limit, 'nodes': len(result['nodes']), 'call_instances': len(result['edges']),
             'pages': result['pages'], 'json_bytes': byte_count, 'database_bytes': path.stat().st_size,
             'connections': connects, 'sql_statements': {k: len(v) for k, v in sql.items()},
             'write_attempts': write_attempts, 'database_sha256_unchanged': True,
             'samples': samples, 'latency_ms': {'min': min(milliseconds), 'median': statistics.median(milliseconds),
                                              'p95': sorted(milliseconds)[int(.95 * (samples - 1))], 'max': max(milliseconds)},
             'raw_latency_ms': milliseconds}
    return result, stats


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--analyzer', type=Path, required=True)
    parser.add_argument('--resource-dir', type=Path, required=True)
    parser.add_argument('--samples', type=int, default=31)
    args = parser.parse_args()
    args.work.mkdir(exist_ok=False, parents=True)
    output = {'environment': {'os': platform.platform(), 'machine': platform.machine(), 'logical_cpus': os.cpu_count(),
                              'python': platform.python_version(), 'sqlite': sqlite3.sqlite_version},
              'method': '3 warmups then repeated uninstrumented warm-cache queries; one separate traced call counts persistent vs in-memory validation SQL. Local machine only, no cold-cache/large-project latency claim.',
              'source_index_py_sha256': sha(args.source_root / 'backend/codeweave/index.py'), 'cases': []}
    cases = [('small', 3, 1, False, 0, 12), ('shared_targets', 2, 60, False, 0, 50),
             *[(f'fanout_{n}', n, 1, False, 0, 50) for n in (1, 5, 12, 25, 50)],
             ('cycles_repeats', 2, 40, True, 0, 50), ('moderate_corpus', 100, 1, True, 50_000, 50),
             ('moderate_ui_limit', 100, 1, True, 50_000, 12)]
    for name, targets, repeats, cycle, filler, limit in cases:
        database = args.work / f'{name}.sqlite3'
        info = synthetic(database, targets, repeats, cycle, filler)
        result, stats = measured(database, info['center'], info['index_id'], limit, args.samples)
        expected = set()
        for direction in ('callers', 'callees'):
            slot = 1 if direction == 'callers' else 0
            rows = [(i, call) for i, call in enumerate(info['oracle']) if call[slot] == 'n0']
            expected.update(f'call{i}' for i, _ in rows[:limit])
            assert result['pages'][direction]['total_count'] == len(rows)
            assert result['pages'][direction]['has_more'] == (len(rows) > limit)
        assert {c['instance_id'] for c in result['edges']} == expected
        assert all(c['index_id'] == 'synthetic' and c['units'] == ['/owned/unit.cpp'] for c in result['edges'])
        output['cases'].append({'name': name, 'origin': 'explicitly synthetic SQLite scale rows',
                                'symbols': info['symbols'], 'calls': info['calls'], **stats})
        print(name, json.dumps({k: stats[k] for k in ('connections', 'sql_statements', 'latency_ms', 'nodes', 'call_instances', 'json_bytes')}), flush=True)

    oversized = args.work / 'oversized.sqlite3'
    synthetic(oversized, 1, anchor_size=150_000)
    before = sha(oversized)
    try:
        kernel.query(oversized, 'neighbors', 'n0', 'synthetic', limit=12)
        raise AssertionError('oversize graph was accepted')
    except kernel.IndexError as error:
        assert error.code == 'query_limit'
        assert sha(oversized) == before
        output['oversize_guard'] = {'code': error.code, 'database_unchanged': True}

    source = args.work / 'real-source'
    shutil.copytree(args.source_root / 'tests/fixtures/m1', source)
    comp = args.work / 'compilation'; comp.mkdir()
    commands = [{'directory': str(source), 'file': str(f), 'arguments': ['c++', '-std=c++17', '-I', str(source), '-c', str(f)]} for f in sorted(source.rglob('*.cpp'))]
    (comp / 'compile_commands.json').write_text(json.dumps(commands))
    database = args.work / 'real.sqlite3'
    command = [sys.executable, '-m', 'codeweave', 'index', '--project-root', str(source), '--compilation-database', str(comp),
               '--database', str(database), '--analyzer', str(args.analyzer), '--resource-dir', str(args.resource_dir)]
    process = subprocess.run(command, capture_output=True, text=True, timeout=60)
    output['real_index_command'] = {'argv': command, 'exit_code': process.returncode, 'stdout': process.stdout, 'stderr': process.stderr,
                                   'analyzer_sha256': sha(args.analyzer)}
    assert process.returncode == 0
    active = json.loads(process.stdout)['index_id']
    result, stats = measured(database, 'c:@F@left#', active, 12, args.samples)
    assert len(result['nodes']) == 4 and len(result['edges']) == 4
    output['cases'].append({'name': 'real_clang_multifile', 'origin': 'actual public CLI / new analyzer / Bubblewrap', **stats})
    (args.work / 'results.json').write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n')
    print('PASS', args.work / 'results.json')


if __name__ == '__main__':
    main()
