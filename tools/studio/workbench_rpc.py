"""Bounded native Codex metadata client; executes inside the existing bwrap supervisor."""
import json
import selectors
import subprocess
import sys
import time

METHODS = {'model/list', 'thread/read', 'thread/archive', 'thread/unarchive', 'thread/name/set', 'thread/fork'}


def request(executable, method, params):
    if method not in METHODS: raise ValueError('Unsupported native metadata request')
    p = subprocess.Popen([executable, 'app-server'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    selector = selectors.DefaultSelector();selector.register(p.stdout, selectors.EVENT_READ)
    pending = bytearray();start = time.monotonic()
    def send(value): p.stdin.write(json.dumps(value).encode() + b'\n');p.stdin.flush()
    try:
        send({'id': 1, 'method': 'initialize', 'params': {'clientInfo': {'name': 'devflower_workbench', 'version': '0.1'}}})
        while time.monotonic() - start < 20:
            if not selector.select(.2): continue
            block = p.stdout.read1(65536)
            if not block: break
            pending.extend(block)
            if len(pending) > 2_000_000: raise ValueError('Native metadata budget exceeded')
            while b'\n' in pending:
                line, _, rest = pending.partition(b'\n');pending[:] = rest
                x = json.loads(line)
                if x.get('id') == 1:
                    if 'error' in x: return x
                    send({'method': 'initialized'});send({'id': 2, 'method': method, 'params': params})
                elif x.get('id') == 2: return x
        raise ValueError('Native metadata request timed out')
    finally:
        selector.close();p.terminate()
        try: p.wait(timeout=2)
        except subprocess.TimeoutExpired: p.kill();p.wait(timeout=2)


if __name__ == '__main__':
    try:
        value = json.loads(sys.stdin.buffer.read(100000))
        print(json.dumps(request(value['executable'], value['method'], value.get('params', {}))))
    except (OSError, ValueError, KeyError) as exc:
        print(json.dumps({'error': {'message': str(exc)}}));sys.exit(1)
