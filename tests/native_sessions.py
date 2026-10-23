"""Operator-run real native HTTP create/resume proof, without Stable promotion.

Requires a pinned Development session operator and working native bwrap/CLI/auth.
No fixture envelopes, global authentication changes, Git delivery or approvals.
"""
import argparse
from http.server import ThreadingHTTPServer
import json
import os
from pathlib import Path
import secrets
import sys
import threading
import time
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from orchestration.common import canonical, digest, tree_hash
from studio.session_runtime import SessionRuntime
from studio.usable_server import handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('operator', 'operator-sha256', 'candidate-sha256', 'workspace', 'artifacts'):
        parser.add_argument('--' + key, required=True)
    parser.add_argument('--profiles', nargs='+', required=True)
    parser.add_argument('--allow-native-turns', action='store_true', required=True)
    args = parser.parse_args()
    runtime = SessionRuntime(args.operator, args.operator_sha256, args.candidate_sha256)
    output, workspace = Path(args.artifacts).resolve(), Path(args.workspace).resolve()
    root = Path(__file__).resolve().parents[1]
    protected = [root, workspace, runtime.storage, runtime.native, runtime.operator_file]
    if any(output.is_relative_to(p) or p.is_relative_to(output) for p in protected):
        parser.error('Evidence directory must be new and disjoint from source/operator/runtime data')
    output.mkdir(mode=0o700)
    token = secrets.token_urlsafe(32)
    server = ThreadingHTTPServer(('127.0.0.1', 0), handler(runtime, token))
    thread = threading.Thread(target=server.serve_forever, daemon=True);thread.start()
    base = 'http://127.0.0.1:' + str(server.server_port)
    summary = dict(actor='external operator running native_sessions.py; no Controller approval',
                   candidate_sha256=args.candidate_sha256, operator_sha256=args.operator_sha256,
                   source_before=tree_hash(workspace), profiles=[], status='BLOCKED')

    def api(route, data=None, capability=token):
        request = Request(base + route, data=canonical(data) if data is not None else None,
                          headers={'Authorization': 'Bearer ' + capability, 'Content-Type': 'application/json'})
        with urlopen(request, timeout=60) as response:return json.load(response)

    def wait_operation(key, project, budget):
        end = time.monotonic() + budget + 30
        while time.monotonic() < end:
            row = api('/api/session/operation?' + urlencode(dict(workspace=project, id=key)))
            if row['state'] in ('FAILED', 'CANCELLED', 'RECOVERY_REQUIRED'):
                raise RuntimeError('Native operation did not complete: ' + json.dumps(row))
            if row['state'] == 'COMPLETED' and not row['worker_alive']:
                return row
            time.sleep(.25)
        raise RuntimeError('Native operation exceeded its operator budget')

    try:
        project = api('/api/workspace', dict(path=str(workspace)))
        if not project['execution_allowed']:
            raise RuntimeError('Workspace is not an operator-approved executable repository')
        for profile_id in args.profiles:
            p = runtime.operator['profiles'][profile_id]
            marker = 'native-memory-' + secrets.token_hex(12)
            common = dict(workspace=project['id'], profile=profile_id, permission='read')
            preview = api('/api/session/prepare', dict(common, handle='new', prompt='Remember this exact marker for the next turn: ' + marker + '. Reply with the marker.'))
            launched = api('/api/session/authorize', dict(permit=preview['id'], sha256=preview['sha256'],
                answer='Operator command explicitly authorizes this isolated native read-only test turn.'))
            first = wait_operation(launched['id'], project['id'], p.get('timeout_seconds', 1800))
            if marker not in first['reply']:
                raise RuntimeError('First native answer did not acknowledge the test marker')
            listing = api('/api/sessions?workspace=' + project['id'])
            home = first['receipt']['home']
            rows = [r for r in listing['discovery']['sessions'] if r['session_id'] == first['session_id'] and
                    r['provider'] == p['provider'] and r['cwd'] == str(workspace) and r['storage_root'] == str(Path(home) / ('.' + p['provider']))]
            if len(rows) != 1 or not rows[0]['resume']:
                raise RuntimeError('Exact new native UUID/profile/cwd was not discoverable and resumable')
            handle = rows[0]['handle']
            next_turn = dict(common, handle=handle, prompt='What exact marker did I ask you to remember in the previous turn? Reply with only that marker.')
            stale = api('/api/session/prepare', next_turn)
            second_preview = api('/api/session/prepare', next_turn)
            second_launch = api('/api/session/authorize', dict(permit=second_preview['id'], sha256=second_preview['sha256'],
                answer='Operator authorizes exact UUID/profile/cwd continuation with unchanged read-only permissions.'))
            second = wait_operation(second_launch['id'], project['id'], p.get('timeout_seconds', 1800))
            if marker not in second['reply'] or second['session_id'] != first['session_id'] or second['receipt']['home'] != home:
                raise RuntimeError('Native continuation failed exact identity or prior-turn recall')
            denied = {}
            for label, route, payload, capability in [
                ('stale-preview', '/api/session/authorize', dict(permit=stale['id'], sha256=stale['sha256'], answer='stale test'), token),
                ('native-delete', '/api/session/delete', dict(workspace=project['id'], handle=handle, confirmed=True), token),
                ('unauthorized', '/api/session/visibility', dict(workspace=project['id'], handle=handle, hidden=True), 'invalid')]:
                try:api(route, payload, capability)
                except HTTPError as exc:denied[label] = exc.code
                else:raise RuntimeError('Negative native API case unexpectedly succeeded: ' + label)
            summary['profiles'].append(dict(profile=profile_id, provider=p['provider'], create=first,
                resume=second, exact_uuid=first['session_id'], negative_http=denied))
            print(p['provider'] + ': actual HTTP create/resume and prior-turn recall passed', flush=True)
        summary['source_after'] = tree_hash(workspace)
        if summary['source_after'] != summary['source_before']:
            raise RuntimeError('Read-only native test changed original source bytes')
        summary['status'] = 'NATIVE_SESSION_CHECKS_PASSED'
        return 0
    except Exception as exc:
        summary['reason'] = str(exc)
        return 1
    finally:
        (output / 'native-session-results.json').write_bytes(canonical(summary))
        (output / 'native-session-results.json').chmod(0o600)
        server.shutdown();server.server_close();thread.join()


if __name__ == '__main__':raise SystemExit(main())
