"""Command surface. status/audit use read-only SQLite and never start agents."""
import argparse
import json
from pathlib import Path
import shutil
import sys
import subprocess
from .adapters import probe
from .common import Blocked
from .controller import deliver_run, resume, start
from .sandbox import abi
from .store import Store

COMMANDS = {'doctor', 'run', 'status', 'resume', 'cancel', 'audit', 'deliver'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('doctor')
    p = sub.add_parser('run')
    p.add_argument('--control', required=True)
    p.add_argument('--config', required=True)
    p.add_argument('--authorization', required=True)
    for name in ('status', 'resume', 'cancel', 'audit', 'deliver'):
        p = sub.add_parser(name)
        p.add_argument('--control', required=True)
        p.add_argument('--run', required=True)
        if name == 'audit':
            p.add_argument('--after', type=int, default=0)
            p.add_argument('--limit', type=int, default=50)
    args = parser.parse_args(argv)
    try:
        if args.command == 'doctor':
            value = {'python': sys.version.split()[0], 'landlock_abi': abi(), 'isolation': 'requires-per-run-probe',
                     'adapters': {kind: probe(shutil.which(kind) or kind, kind) for kind in ('codex', 'claude')}}
        elif args.command == 'run':
            value = start(args.control, args.config, args.authorization)
        else:
            store = Store(args.control, readonly=args.command in ('status', 'audit'))
            if args.command == 'status':
                value = store.get(args.run)
            elif args.command == 'audit':
                value = store.audit(args.run, args.after, args.limit)
            elif args.command == 'cancel':
                store.transition(args.run, None, cancel_requested=True)
                value = {'id': args.run, 'cancel_requested': True}
            elif args.command == 'resume':
                value = resume(store, args.run)
            else:
                value = deliver_run(store, args.run)
        if isinstance(value, dict) and 'data' in value:
            data = value['data']
            value = {k: value[k] for k in ('id', 'state')} | {k: data[k] for k in
                ('round', 'reason', 'receipts') if k in data} | {'candidate_sha256': data.get('candidate', {}).get('sha256')}
        print(json.dumps(value, ensure_ascii=False, indent=2))
        return 1 if isinstance(value, dict) and value.get('state') in ('BLOCKED', 'PARTIAL_DELIVERY') else 0
    except (Blocked, OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({'state': 'BLOCKED', 'reason': str(exc)}, ensure_ascii=False))
        return 1
