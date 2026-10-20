"""Optional real HTTP/Chromium identity-race tests; SQLite fixtures, no model calls."""
import argparse
from http.server import ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from test_studio import database_fixture, task_fixture
from studio.graph import from_task
from studio.server import App, handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--chromium', required=True)
    parser.add_argument('--node', default='node')
    parser.add_argument('--playwright-module', default='playwright')
    parser.add_argument('--artifacts', required=True)
    parser.add_argument('--baseline', action='store_true', help='Run the two primary reproductions only')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    out = Path(args.artifacts).resolve()
    if out.is_relative_to(root) or root.is_relative_to(out):
        parser.error('artifacts must be outside the repository')
    out.mkdir(mode=0o700)
    db, a, data = database_fixture(out / 'control', state='READY')
    data['config']['task_id'] = 'RUN_A'; data['round'] = data['candidate_round'] = 2
    data['review'] = {'report': {'round': 2, 'verdict': 'ACCEPT'}}
    data['reviews'] = [{'round': 2, 'candidate_sha256': 'a' * 64, 'verdict': 'ACCEPT'}]
    db.execute('UPDATE runs SET data=? WHERE id=?', (json.dumps(data), a))
    b = 'b' * 32
    other = json.loads(json.dumps(data)); other['config']['task_id'] = 'RUN_B'
    other['round'] = other['candidate_round'] = 3
    other['candidate']['sha256'] = 'b' * 64
    other['verification'] = [{'id': 'unit', 'round': 3, 'passed': False,
                              'counts': {'tests': 9, 'failures': 1, 'errors': 0, 'skipped': 0}}]
    other['review'] = {'report': {'round': 3, 'verdict': 'BLOCKED'}}
    other['reviews'] = [{'round': 3, 'candidate_sha256': 'b' * 64, 'verdict': 'BLOCKED'}]
    db.execute('INSERT INTO runs VALUES(?,?,?)', (b, 'BLOCKED', json.dumps(other)))
    db.execute('INSERT INTO events(run,at,kind,data) VALUES(?,?,?,?)',
               (b, time.time(), 'BLOCKED', json.dumps({'round': 3})))
    db.commit(); db.close()
    app = App(out / 'drafts', out / 'control')
    server = ThreadingHTTPServer(('127.0.0.1', 0), handler(app))
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    (out / 'access.json').write_text(json.dumps({'url': f'http://127.0.0.1:{server.server_port}/',
                                               'token': app.token, 'a': a, 'b': b}))
    (out / 'document.json').write_text(json.dumps(from_task(task_fixture())))
    try:
        result = subprocess.run([args.node, str(Path(__file__).with_suffix('.cjs')), str(out),
                                 *(['--baseline'] if args.baseline else [])],
                                env=dict(os.environ, CHROMIUM=args.chromium,
                                         PLAYWRIGHT_MODULE=args.playwright_module), timeout=240)
        return result.returncode
    finally:
        server.shutdown(); server.server_close(); thread.join()


if __name__ == '__main__':
    sys.exit(main())
