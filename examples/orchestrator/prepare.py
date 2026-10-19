"""Operator-only, owned demo preparation. No agents, network or Git delivery.

Creates a new six-case clamp fixture, full task configuration and one explicit
operator authorization. Never overwrites an existing directory or CLI home.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
from orchestration.common import canonical, controller_hash, digest, git, identity, load, save
from orchestration.contracts import config_check


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', required=True)
    parser.add_argument('--bindings', required=True, help='Approved dedicated CLI homes/model/role bindings JSON')
    parser.add_argument('--project', default='devflower-demo')
    parser.add_argument('--approval-ref', required=True, help='Reference to the actual human task authorization')
    parser.add_argument('--approve-fixture-external', required=True, action='store_true')
    args = parser.parse_args()
    base = Path(args.directory).resolve()
    if base.exists() or not args.approval_ref.strip():
        parser.error('a new directory and nonempty human approval reference are required')
    bindings = load(args.bindings)
    policy = load(Path(__file__).resolve().parents[2] / 'docs/design/v0.2-a/examples/workflow-policy.example.json')
    for role in policy['agents']:
        policy['agents'][role]['session_policy'] = 'new'
    policy['required_contracts'] = ['clamp']
    policy['verification'] = [{'id': 'clamp', 'argv': [sys.executable, 'verify_fixture.py', '{result}'],
                               'result_format': 'controller-json', 'min_cases': 6, 'max_skipped': 0}]
    source = base / 'source'
    config = {'task_id': 'clamp-demo', 'project': args.project, 'source': str(source),
              'acceptance': str(base / 'acceptance.txt'),
              'goal': 'Read acceptance.txt, implement clamp.py, run verify_fixture.py, and correct all review feedback. Do not edit verification or use Git delivery.',
              'scope': ['clamp.py'], 'excludes': [], 'policy': policy, 'bindings': bindings}
    # Inputs are validated before any files are written. New policy never resumes
    # a supplied UUID; subsequent rounds restore the exact captured role session.
    config_check(config)
    for b in bindings.values():
        home = Path(b['home']).resolve()
        if home == base or base.is_relative_to(home):
            parser.error('runtime homes must not contain the whole task directory')
    source.mkdir(parents=True)
    (source / 'clamp.py').write_text('def clamp(value):\n    raise NotImplementedError\n')
    (source / 'acceptance.txt').write_text('clamp(value) returns max(0, min(10, value)) for integers; six required cases, zero skips. Only clamp.py may change.\n')
    (source / 'verify_fixture.py').write_text('''import json,sys
from pathlib import Path
from clamp import clamp
cases=[(-5,0),(0,0),(1,1),(9,9),(10,10),(17,10)]
failed=0
for value,expected in cases:
 try: failed += clamp(value) != expected
 except Exception: failed += 1
Path(sys.argv[1]).write_text(json.dumps(dict(tests=len(cases),failures=failed,errors=0,skipped=0)))
sys.exit(1 if failed else 0)
''')
    (base / 'acceptance.txt').write_bytes((source / 'acceptance.txt').read_bytes())
    subprocess.run(['git', 'init', '-q', '-b', 'flow/clamp-demo', str(source)], check=True)
    git(source, 'config', 'user.name', 'DevFlower owned demo')
    git(source, 'config', 'user.email', 'demo@example.invalid')
    git(source, 'add', '--', 'clamp.py', 'acceptance.txt', 'verify_fixture.py')
    git(source, 'commit', '-qm', 'fixture: signed-off clamp demo baseline')
    save(base / 'task.json', config)
    actual = identity(source)
    auth = {'config_sha256': digest(canonical(config)), 'acceptance_sha256': digest((base / 'acceptance.txt').read_bytes()),
            'controller_sha256': controller_hash(), 'source': actual['root'], 'head': actual['head'],
            'branch': actual['branch'], 'approval_ref': args.approval_ref,
            'external_source_approved': True, 'commit': False, 'push': False}
    save(base / 'operator.json', auth)
    (base / 'operator.json').chmod(0o600)
    print(json.dumps({'task': str(base / 'task.json'), 'authorization': str(base / 'operator.json'),
                      'control': str(base / 'control'), 'delivery': 'disabled', 'agent_processes_started': 0}))


if __name__ == '__main__':
    main()
