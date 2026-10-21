"""Ordinary Chromium + real HTTP session UI regression; synthetic history only."""
import argparse
from http.server import ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import sys
import threading

sys.dont_write_bytecode = True
sys.path[:0] = [str(Path(__file__).resolve().parents[1] / 'tools'), str(Path(__file__).resolve().parent)]
from test_agent_sessions import CenterTests
from test_workspace_sessions import native, tree_hash
from test_agent_sessions import append_messages
from studio.usable_server import handler
from orchestration import sandbox


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--chromium', required=True)
    parser.add_argument('--node', default='node')
    parser.add_argument('--playwright-module', default='playwright')
    parser.add_argument('--artifacts', required=True)
    parser.add_argument('--server-landlock', action='store_true',
        help='Confine the HTTP service thread and all request threads; browser remains ordinary Chromium')
    args = parser.parse_args();output = Path(args.artifacts).resolve();root = Path(__file__).resolve().parents[1]
    if output.is_relative_to(root) or root.is_relative_to(output):parser.error('Artifacts must be outside source')
    output.mkdir(mode=0o700)
    fixture = CenterTests();fixture.setUp()
    registered = fixture.root / 'registered-profile-stores'
    registered_roots, registered_markers = [], []
    for name in ('alpha','beta'):
        config = registered / name / '.claude'
        path = native(config,'claude',fixture.source)
        marker = 'REGISTERED_'+name+'_VISIBLE'
        with path.open('a') as f:
            f.write(json.dumps(dict(type='user',sessionId=path.stem,
                message=dict(role='user',content=marker)))+'\n')
        registered_roots.append(str(config));registered_markers.append(marker)
    runtime = fixture.development_runtime(session_read_roots=[str(registered)])
    for provider in ('codex', 'claude'):
        path = native(fixture.source / ('profiles/' + provider + '/.' + provider), provider, fixture.source)
        append_messages(path, provider)
    other = fixture.root / 'readonly-notes';other.mkdir()
    before = (tree_hash(fixture.source),tree_hash(registered))
    server = ThreadingHTTPServer(('127.0.0.1', 0), handler(runtime, 'browser-fixture-only-token'))
    ready = threading.Event();startup = []
    def serve():
        try:
            if args.server_landlock:
                reads = sandbox.runtime_paths() + [str(root), str(fixture.source), str(registered),
                    str(other), str(runtime.operator_file), *runtime.operator['dependencies']]
                writes = [str(runtime.storage), str(runtime.native)]
                sandbox.enforce(reads, writes)
                # Never permit parent listings just to make the UI test pass.
                for denied in ('/', str(fixture.root)):
                    try:
                        fd = os.open(denied, os.O_RDONLY | os.O_DIRECTORY)
                    except PermissionError:
                        pass
                    else:
                        os.close(fd)
                        raise AssertionError('Ancestor READ_DIR unexpectedly allowed')
                startup.append(dict(backend='landlock', abi=sandbox.abi(), read=reads, write=writes,
                    ancestors_read_denied=True, scope='service thread and inherited request threads'))
            else:
                startup.append(dict(backend='unconfined'))
        except BaseException as error:
            startup.append(dict(error=repr(error)))
            ready.set();return
        ready.set()
        server.serve_forever()
    thread = threading.Thread(target=serve, daemon=True);thread.start()
    if not ready.wait(10) or not startup or 'error' in startup[0]:
        server.server_close();fixture.doCleanups()
        raise RuntimeError('HTTP isolation startup failed: '+repr(startup))
    (output / 'server-isolation.json').write_text(json.dumps(startup[0],indent=2))
    (output / 'access.json').write_text(json.dumps(dict(url='http://127.0.0.1:' + str(server.server_port),
        token='browser-fixture-only-token', source=str(fixture.source), other=str(other),
        registered_roots=registered_roots,registered_markers=registered_markers,
        evidence_type='synthetic history UI regression; not native or final acceptance')))
    try:
        result = subprocess.run([args.node, str(Path(__file__).with_suffix('.cjs')), str(output)], timeout=180,
            env=dict(os.environ, CHROMIUM=args.chromium, PLAYWRIGHT_MODULE=args.playwright_module,
                     TMPDIR=os.environ.get('BROWSER_TMPDIR', os.environ.get('TMPDIR', '/tmp'))))
        unchanged = before == (tree_hash(fixture.source),tree_hash(registered))
        (output / 'native-unchanged.json').write_text(json.dumps(dict(unchanged=unchanged)))
        return result.returncode or int(not unchanged)
    finally:
        server.shutdown();server.server_close();thread.join();fixture.doCleanups()


if __name__ == '__main__':raise SystemExit(main())
