"""Final-integration regressions for DF-R01/R02/R03, using owned fixtures only."""
import copy
import contextlib
import io
import json
import subprocess
import sys
from pathlib import Path

from test_orchestration import Fixture
from orchestration import controller, delivery, cli
from orchestration.common import Blocked, git, load, save, snapshot, tree_hash
from orchestration.store import Store
from orchestration.verification import verify


class IntegrationRegressions(Fixture):
    def target(self):
        remote = self.base / 'remote.git'
        subprocess.run(['git', 'clone', '-q', '--bare', str(self.source), str(remote)], check=True)
        git(self.source, 'remote', 'add', 'origin', str(remote))
        return dict(kind='source', root=str(self.source), remote=str(remote),
                    branch='flow/fixture', expected_tip=git(self.source, 'rev-parse', 'HEAD'))

    def test_DF_R01_descendants_and_physical_aliases_rejected(self):
        other_home = Path(self.config['bindings']['reviewer']['home'])
        (other_home / 'private').mkdir(parents=True)
        secret = other_home / 'private/token';secret.write_text('fixture only')
        alias = self.base / 'alias';alias.symlink_to(other_home, target_is_directory=True)
        protected = [self.source / 'value.py', self.source / '.git/objects',
                     self.control / 'nested/file', secret, alias / 'private/token',
                     Path(controller.__file__).resolve()]
        for index, path in enumerate(protected):
            with self.subTest(path=path):
                self.config['bindings']['implementer']['read_paths'] = [str(self.bin), str(path)]
                self.authorize()
                result = controller.start(self.control, self.config_path, self.auth_path)
                self.assertEqual(result['state'], 'BLOCKED')
                self.assertIn('read allowlist', result['data']['reason'])
                self.assertFalse(any(o['kind'] == 'AGENT_REQUEST' for o in Store(self.control).operations(result['id'])))

    def test_DF_R01_legitimate_runtime_dependency_still_runs(self):
        result = controller.start(self.control, self.config_path, self.auth_path)
        self.assertEqual(result['state'], 'READY', result['data'].get('reason'))

    def test_A03_interrupted_review_baseline_preserved_and_rebuilt(self):
        original = controller.snapshot
        def interrupted(source, dest, *args, **kwargs):
            if Path(dest).name == 'baseline':
                Path(dest).mkdir();(Path(dest) / 'partial').write_text('retain this interrupted copy')
                raise OSError('injected baseline copy interruption')
            return original(source, dest, *args, **kwargs)
        controller.snapshot = interrupted
        try:result = controller.start(self.control, self.config_path, self.auth_path)
        finally:controller.snapshot = original
        self.assertEqual(result['state'], 'BLOCKED')
        result = controller.resume(Store(self.control), result['id'])
        self.assertEqual(result['state'], 'READY', result['data'].get('reason'))
        saved = list((self.control / result['id']).glob('interrupted-baseline-*/partial'))
        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0].read_text(), 'retain this interrupted copy')

    def test_A04_reviewer_can_read_fixed_baseline_but_cannot_write_it(self):
        text = self.fake.read_text()
        marker = " passed='42' in (cwd/'value.py').read_text()"
        probe = """ baseline=pathlib.Path(re.search(r'baseline_path=(\\S+)',prompt)[1])
 assert (baseline/'value.py').read_text()=='VALUE = 0\\n'
 try: (baseline/'value.py').write_text('forged baseline')
 except OSError: pass
 else: raise RuntimeError('reviewer could write baseline')
"""
        self.assertIn(marker, text)
        self.fake.write_text(text.replace(marker, probe + marker))
        result = controller.start(self.control, self.config_path, self.auth_path)
        self.assertEqual(result['state'], 'READY', result['data'].get('reason'))
        for rd in (self.control / result['id']).glob('round-*'):
            self.assertEqual((rd / 'baseline/value.py').read_text(), 'VALUE = 0\n')
            self.assertIn(str(rd / 'baseline'), (rd / 'changes.diff').read_text())

    def test_DF_R02_commit_only_is_pinned_and_survives_prune(self):
        target = self.target();candidate = self.base / 'candidate';snapshot(self.source, candidate)
        (candidate / 'value.py').write_text('VALUE = 42\n')
        index = (self.source / '.git/index').read_bytes();head = git(self.source, 'rev-parse', 'HEAD')
        store = Store(self.control);run = store.create({})
        receipts = delivery.deliver(store, run, candidate, [target], False, tree_hash(candidate))
        self.assertEqual(store.get(run)['state'], 'LOCAL_COMMITTED')
        ref = receipts[0]['local_ref'];sha = receipts[0]['commit']
        self.assertEqual(git(self.source, 'rev-parse', ref), sha)
        git(self.source, 'reflog', 'expire', '--expire=now', '--all')
        git(self.source, 'gc', '--prune=now')
        self.assertEqual(git(self.source, 'rev-parse', ref + '^{commit}'), sha)
        self.assertEqual(delivery.deliver(store, run, candidate, [target], False), receipts)
        self.assertEqual(head, git(self.source, 'rev-parse', 'HEAD'))
        self.assertEqual(index, (self.source / '.git/index').read_bytes())
        self.assertFalse(git(self.source, 'status', '--porcelain'))
        self.assertEqual(delivery.remote_tip(target['remote'], target['branch']), head)

    def test_DF_R02_lost_receipt_after_pin_recovers_same_commit(self):
        target = self.target();store = Store(self.control);run = store.create({})
        tree = delivery.make_tree(self.source, self.source);finish = store.finish
        def lost(op, status, **updates):
            if status == 'COMMITTED':
                raise RuntimeError('injected receipt loss after durable ref')
            return finish(op, status, **updates)
        store.finish = lost
        with self.assertRaises(RuntimeError):
            delivery.commit(store, run, target, tree)
        store.finish = finish
        op = store.operations(run)[0]
        pinned = git(self.source, 'rev-parse', op['data']['local_ref'])
        self.assertEqual(delivery.commit(store, run, target, tree), pinned)
        self.assertEqual(delivery.commit(store, run, target, tree), pinned)
        self.assertEqual(len([o for o in store.operations(run) if o['kind'] == 'COMMIT']), 1)

    def test_DF_R02_changed_pin_is_never_overwritten(self):
        target = self.target();store = Store(self.control);run = store.create({})
        tree = delivery.make_tree(self.source, self.source)
        delivery.commit(store, run, target, tree)
        ref = store.operations(run)[0]['data']['local_ref'];base = target['expected_tip']
        git(self.source, 'update-ref', ref, base)
        with self.assertRaisesRegex(Blocked, 'reference'):
            delivery.commit(store, run, target, tree)
        self.assertEqual(git(self.source, 'rev-parse', ref), base)

    def test_DF_R02_commit_only_controller_resume_and_repeat_deliver(self):
        target = self.target();self.config['delivery_targets'] = [target]
        self.config['policy']['delivery']['commit'] = True;self.authorize()
        self.auth['commit'] = True;save(self.auth_path, self.auth)
        result = controller.start(self.control, self.config_path, self.auth_path)
        self.assertEqual(result['state'], 'READY', result['data'].get('reason'))
        store = Store(self.control);run = result['id']
        receipts = controller.deliver_run(store, run)
        self.assertEqual(store.get(run)['state'], 'LOCAL_COMMITTED')
        before = len(store.operations(run))
        self.assertEqual(controller.resume(store, run)['state'], 'LOCAL_COMMITTED')
        self.assertEqual(len(store.operations(run)), before)
        self.assertEqual(controller.deliver_run(store, run), receipts)
        self.assertFalse(any(o['kind'] == 'PUSH' for o in store.operations(run)))
        self.assertEqual(delivery.remote_tip(target['remote'], target['branch']), target['expected_tip'])

    def test_A06_cancel_ready_stops_delivery_and_resume(self):
        target = self.target();self.config['delivery_targets'] = [target]
        self.config['policy']['delivery']['commit'] = True;self.authorize()
        self.auth['commit'] = True;save(self.auth_path, self.auth)
        result = controller.start(self.control, self.config_path, self.auth_path)
        self.assertEqual(result['state'], 'READY')
        store = Store(self.control);run = result['id']
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(cli.main(['cancel', '--control', str(self.control), '--run', run]), 0)
        self.assertEqual(json.loads(output.getvalue())['state'], 'CANCELLED')
        self.assertEqual(store.get(run)['state'], 'CANCELLED')
        with self.assertRaisesRegex(Blocked, 'cancel'):
            controller.deliver_run(store, run)
        self.assertEqual(controller.resume(store, run)['state'], 'CANCELLED')
        self.assertFalse(any(o['kind'] in ('COMMIT', 'PUSH') for o in store.operations(run)))
        self.assertEqual(delivery.remote_tip(target['remote'], target['branch']), target['expected_tip'])

    def test_A06_pending_cancel_blocks_ready_resume_without_agent(self):
        result = controller.start(self.control, self.config_path, self.auth_path)
        store = Store(self.control);run = result['id'];before = len(store.operations(run))
        store.transition(run, None, cancel_requested=True)
        self.assertEqual(controller.resume(store, run)['state'], 'CANCELLED')
        self.assertEqual(len(store.operations(run)), before)

    def test_A06_cancel_preserves_committed_receipt_and_stops_later_delivery(self):
        target = self.target();self.config['delivery_targets'] = [target]
        self.config['policy']['delivery']['commit'] = True;self.authorize()
        self.auth['commit'] = True;save(self.auth_path, self.auth)
        result = controller.start(self.control, self.config_path, self.auth_path)
        store = Store(self.control);run = result['id'];receipts = controller.deliver_run(store, run)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(cli.main(['cancel', '--control', str(self.control), '--run', run]), 0)
        self.assertEqual(json.loads(output.getvalue())['state'], 'CANCELLED')
        self.assertEqual(store.get(run)['state'], 'CANCELLED')
        self.assertEqual(store.get(run)['data']['receipts'], receipts)
        self.assertEqual(git(self.source, 'rev-parse', receipts[0]['local_ref']), receipts[0]['commit'])
        with self.assertRaisesRegex(Blocked, 'cancel'):
            controller.deliver_run(store, run)
        self.assertEqual(delivery.remote_tip(target['remote'], target['branch']), target['expected_tip'])

    def test_A06_cancel_during_tree_build_creates_no_commit(self):
        target = self.target();candidate = self.base / 'candidate';snapshot(self.source, candidate)
        store = Store(self.control);run = store.create({});original = delivery.make_tree
        def cancelled(root, source):
            tree = original(root, source)
            store.transition(run, None, cancel_requested=True)
            return tree
        delivery.make_tree = cancelled
        try:
            with self.assertRaisesRegex(Blocked, 'cancel'):
                delivery.deliver(store, run, candidate, [target], True)
        finally:delivery.make_tree = original
        self.assertEqual(store.get(run)['state'], 'CANCELLED')
        self.assertFalse(any(o['kind'] in ('COMMIT', 'PUSH') for o in store.operations(run)))
        self.assertEqual(delivery.remote_tip(target['remote'], target['branch']), target['expected_tip'])

    def test_A06_cancel_after_pin_keeps_receipt_without_push(self):
        target = self.target();candidate = self.base / 'candidate';snapshot(self.source, candidate)
        (candidate / 'value.py').write_text('VALUE = 7\n')
        store = Store(self.control);run = store.create({});original = delivery.commit
        def cancelled(*args, **kwargs):
            sha = original(*args, **kwargs)
            store.transition(run, None, cancel_requested=True)
            return sha
        delivery.commit = cancelled
        try:
            with self.assertRaisesRegex(Blocked, 'cancel'):
                delivery.deliver(store, run, candidate, [target], True)
        finally:delivery.commit = original
        self.assertEqual(store.get(run)['state'], 'CANCELLED')
        receipts = store.get(run)['data']['receipts'];self.assertEqual(len(receipts), 1)
        self.assertFalse(receipts[0]['pushed'])
        self.assertEqual(git(self.source, 'rev-parse', receipts[0]['local_ref']), receipts[0]['commit'])
        self.assertFalse(any(o['kind'] == 'PUSH' for o in store.operations(run)))
        self.assertEqual(delivery.remote_tip(target['remote'], target['branch']), target['expected_tip'])

    def test_DF_R02_push_requires_independent_authorization(self):
        target = self.target();self.config['delivery_targets'] = [target]
        self.config['policy']['delivery'].update(commit=True, push=True);self.authorize()
        with self.assertRaisesRegex(Blocked, 'not authorized'):
            controller.start(self.control, self.config_path, self.auth_path)
        self.assertFalse(self.control.exists())
        self.assertEqual(delivery.remote_tip(target['remote'], target['branch']), target['expected_tip'])

    def test_DF_R02_symbolic_pin_cannot_create_or_move_user_branch(self):
        target = self.target();store = Store(self.control);run = store.create({})
        tree = delivery.make_tree(self.source, self.source);delivery.commit(store, run, target, tree)
        ref = store.operations(run)[0]['data']['local_ref']
        git(self.source, 'symbolic-ref', ref, 'refs/heads/unborn-user-branch')
        with self.assertRaisesRegex(Blocked, 'reference'):
            delivery.commit(store, run, target, tree)
        p = subprocess.run(['git', '-C', str(self.source), 'rev-parse', '--verify', '--quiet', 'refs/heads/unborn-user-branch'])
        self.assertNotEqual(p.returncode, 0)

    def test_DF_R03_shipped_policy_uses_actual_result_binding(self):
        policy = load(Path(__file__).resolve().parents[1] / 'docs/design/v0.2-a/examples/workflow-policy.example.json')
        spec = policy['verification'][0]
        self.assertTrue(any('{result}' in value for value in spec['argv']))
        # Exercise the actual verifier with the shipped arguments and a tiny
        # fixture pytest stand-in, without requiring a downloaded dependency.
        candidate = self.base / 'candidate';candidate.mkdir()
        (candidate / 'pytest.py').write_text('import pathlib,sys; pathlib.Path(sys.argv[sys.argv.index("--junitxml")+1]).write_text(\'<testsuite tests="1"><testcase name="fixture"/></testsuite>\')\n')
        config = copy.deepcopy(self.config);config['policy'] = policy
        spec['argv'][0] = sys.executable
        results = verify(config, candidate, self.base / 'verification', 'fixture', 1, tree_hash(candidate), 'a'*64)
        self.assertTrue(results[0]['passed'])
        self.assertEqual(results[0]['counts']['tests'], 1)

    def test_DF_R03_demo_preparation_produces_real_valid_config(self):
        tool = Path(__file__).resolve().parents[1] / 'examples/orchestrator/prepare.py'
        bindings = self.base / 'bindings.json';save(bindings, self.config['bindings'])
        directory = self.base / 'demo'
        argv = [sys.executable, str(tool), '--directory', str(directory), '--bindings', str(bindings),
                '--project', 'fixture', '--approval-ref', 'owned regression only', '--approve-fixture-external']
        p = subprocess.run(argv, capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        result = json.loads(p.stdout);self.assertEqual(result['agent_processes_started'], 0)
        from orchestration.contracts import authorized
        config = load(directory / 'task.json');auth, actual = authorized(config, directory / 'operator.json')
        self.assertEqual(actual['branch'], 'flow/clamp-demo');self.assertFalse(auth['push'])
        p = subprocess.run(argv, capture_output=True, text=True)
        self.assertNotEqual(p.returncode, 0)
