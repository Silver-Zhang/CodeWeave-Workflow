"""Optional real-HTTP Chromium race regression; no model calls or authority issued."""
import argparse
from http.server import ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from test_studio import task_fixture
from studio.graph import digest
from studio.server import App, handler


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--chromium', required=True)
    parser.add_argument('--node', default='node')
    parser.add_argument('--playwright-module', default='playwright')
    parser.add_argument('--artifacts', required=True, help='New directory outside the repository')
    args=parser.parse_args();out=Path(args.artifacts).resolve()
    root=Path(__file__).resolve().parents[1]
    if out.is_relative_to(root) or root.is_relative_to(out):parser.error('artifacts must be outside the repository')
    out.mkdir(mode=0o700);config=task_fixture();(out/'task.json').write_text(json.dumps(config))
    app=App(out/'drafts')
    # UI binding fixture only. Launcher.start still refuses because no actual task/auth is bound.
    app.launcher.status=lambda:dict(enabled=True,used=False,config_sha256=digest(config),controller_exit=None)
    server=ThreadingHTTPServer(('127.0.0.1',0),handler(app));thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    (out/'access.json').write_text(json.dumps(dict(url=f'http://127.0.0.1:{server.server_port}/',token=app.token)))
    try:
        result=subprocess.run([args.node,str(Path(__file__).with_suffix('.cjs')),str(out)],env=dict(os.environ,CHROMIUM=args.chromium,PLAYWRIGHT_MODULE=args.playwright_module),timeout=180)
        return result.returncode
    finally:server.shutdown();server.server_close();thread.join()


if __name__=='__main__':sys.exit(main())
