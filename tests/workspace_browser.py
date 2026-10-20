"""Optional ordinary Chromium + real HTTP regression; synthetic native files only."""
import argparse
from http.server import ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from studio.server import App, handler
from test_workspace_sessions import fixture, tree_hash


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--chromium',required=True);p.add_argument('--artifacts',required=True)
    p.add_argument('--node',default='node');p.add_argument('--playwright-module',default='playwright')
    args=p.parse_args();out=Path(args.artifacts).resolve();root=Path(__file__).resolve().parents[1]
    if out.is_relative_to(root) or root.is_relative_to(out):p.error('Artifacts must be outside checkout')
    out.mkdir(mode=0o700)
    f=fixture(out);before=[tree_hash(r) for r in f['roots']]
    app=App(out/'studio',project_roots=[f['a'],f['b']],session_profiles=f['cfg'])
    ids={x['path']:x['id'] for x in app.sessions.listing()['workspaces']}
    server=ThreadingHTTPServer(('127.0.0.1',0),handler(app))
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    (out/'access.json').write_text(json.dumps(dict(url=f'http://127.0.0.1:{server.server_port}',token=app.token,
        a=ids[str(f['a'])],b=ids[str(f['b'])],a_path=str(f['a']),b_path=str(f['b']))))
    try:
        result=subprocess.run([args.node,str(Path(__file__).with_suffix('.cjs')),str(out)],timeout=180,
            env=dict(os.environ,CHROMIUM=args.chromium,PLAYWRIGHT_MODULE=args.playwright_module))
        unchanged=before==[tree_hash(r) for r in f['roots']]
        (out/'native-unchanged.json').write_text(json.dumps(dict(unchanged=unchanged)))
        return result.returncode or int(not unchanged)
    finally:server.shutdown();server.server_close();thread.join()


if __name__=='__main__':sys.exit(main())
