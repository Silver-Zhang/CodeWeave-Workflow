#!/usr/bin/env python3
"""Run a pinned Development session center without Stable promotion or Controller execution."""
import argparse
from pathlib import Path
import sys

sys.dont_write_bytecode = True
from orchestration.common import Blocked
from orchestration.store import lease
from studio.session_runtime import SessionRuntime
from studio.usable_server import serve


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--operator', required=True)
    parser.add_argument('--operator-sha256', required=True)
    parser.add_argument('--candidate-sha256', required=True)
    parser.add_argument('--port', type=int, default=8766)
    args = parser.parse_args()
    try:
        runtime = SessionRuntime(args.operator, args.operator_sha256, args.candidate_sha256)
        with lease(runtime.storage / 'service.lock'):
            serve(runtime, args.port)
    except (Blocked, OSError, ValueError) as exc:
        print('BLOCKED: ' + str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':raise SystemExit(main())
