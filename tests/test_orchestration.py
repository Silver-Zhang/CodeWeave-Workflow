"""A01-A16 representative deterministic failures. Real models are separate evidence."""
from __future__ import annotations
import copy
import json
import os
from pathlib import Path
import signal
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from orchestration import adapters, controller, delivery, sandbox
from orchestration.common import Blocked, canonical, controller_hash, digest, git, load, manifest, save, snapshot, tree_hash, scope_check
from orchestration.contracts import authorized, config_check
from orchestration.gate import gate
from orchestration.process import execute, stop
from orchestration.store import Store, alive, lease, process_identity
from orchestration.verification import counts, verify
from orchestration.privacy import credentials, redact, check_tree


def repo(path, branch='flow/fixture'):
    path.mkdir()
    subprocess.run(['git', 'init', '-q', '-b', branch, str(path)], check=True)
    git(path, 'config', 'user.name', 'DevFlower Fixture')
    git(path, 'config', 'user.email', 'fixture@example.invalid')
    (path / 'value.py').write_text('VALUE = 0\n')
    git(path, 'add', 'value.py')
    git(path, 'commit', '-qm', 'fixture baseline')
    return path


FAKE = '''#!/usr/bin/python3
import hashlib,json,pathlib,re,sys,uuid
args=sys.argv; prompt=sys.stdin.read(); cwd=pathlib.Path.cwd()
session=args[args.index('--resume')+1] if '--resume' in args else args[args.index('--session-id')+1] if '--session-id' in args else args[args.index('resume')+1] if 'resume' in args else str(uuid.uuid4())
if 'exec' in args:
 (cwd/'value.py').write_text('VALUE = '+('42' if 'Prior review/verification feedback:\\n{}' not in prompt else '1')+'\\n')
 report={'status':'IMPLEMENTED','summary':'fixture change'}
 print(json.dumps({'type':'thread.started','thread_id':session}))
 print(json.dumps({'type':'item.completed','item':{'type':'agent_message','text':json.dumps(report)}}))
 print(json.dumps({'type':'turn.completed','usage':{}}))
else:
 passed='42' in (cwd/'value.py').read_text()
 report={'schema_version':1,'run_id':re.search(r'run_id=(\\w+)',prompt)[1],'round':int(re.search(r'round=(\\d+)',prompt)[1]),
 'candidate_sha256':re.search(r'candidate_sha256=(\\w+)',prompt)[1],'acceptance_sha256':re.search(r'acceptance_sha256=(\\w+)',prompt)[1],
 'verdict':'ACCEPT' if passed else 'NEEDS_CORRECTION','contracts':[{'id':'unit','status':'PASS' if passed else 'FAIL','evidence_refs':['unit']}],
 'findings':[{'id':'F1','severity':'P1','status':'CLOSED' if passed else 'OPEN','title':'wrong value','contract_ids':['unit'],'evidence_refs':['unit']}],'limitations':[]}
 print(json.dumps({'type':'result','subtype':'success','is_error':False,'session_id':session,'structured_output':report,'modelUsage':{},'usage':{}}))
'''


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='devflower-test-')
        self.base = Path(self.tmp.name)
        self.source = repo(self.base / 'source')
        self.control = self.base / 'control'
        self.acceptance = self.base / 'acceptance.txt'
        self.acceptance.write_text('VALUE must equal 42; no skipped tests.')
        self.bin = self.base / 'bin'
        self.bin.mkdir()
        self.fake = self.bin / 'fixture-cli'
        self.fake.write_text(FAKE)
        self.fake.chmod(0o755)
        policy = load(Path(__file__).resolve().parents[1] / 'docs/design/v0.2-a/examples/workflow-policy.example.json')
        policy['required_contracts'] = ['unit']
        for b in policy['agents'].values():
            b['session_policy'] = 'new'
        policy['limits'].update(step_timeout_seconds=30, max_log_bytes=65536)
        policy['verification'] = [{'id': 'unit', 'argv': [sys.executable, '-c',
            'import pathlib,json,sys; good="42" in pathlib.Path("value.py").read_text(); pathlib.Path(sys.argv[1]).write_text(json.dumps(dict(tests=1,failures=0 if good else 1,errors=0,skipped=0)))', '{result}'],
            'result_format': 'controller-json', 'min_cases': 1, 'max_skipped': 0}]
        self.config = {'task_id': 'fixture', 'project': 'fixture', 'source': str(self.source),
            'acceptance': str(self.acceptance), 'goal': 'Set VALUE to 42', 'scope': ['value.py'], 'excludes': [],
            'policy': policy, 'bindings': {role: {'project': 'fixture', 'role': role, 'executable': str(self.fake),
                'home': str(self.base / ('home-' + role)), 'read_paths': [str(self.bin)], 'model': 'unknown',
                'effort': 'unknown', 'session_id': None} for role in ('implementer', 'reviewer')}}
        self.config_path = self.base / 'config.json'
        self.auth_path = self.base / 'authorization.json'
        self.authorize()

    def tearDown(self):
        self.tmp.cleanup()

    def authorize(self):
        save(self.config_path, self.config)
        self.auth = {'config_sha256': digest(canonical(self.config)), 'controller_sha256': controller_hash(),
                     'acceptance_sha256': digest(self.acceptance.read_bytes()), 'source': str(self.source),
                     'head': git(self.source, 'rev-parse', 'HEAD'), 'branch': 'flow/fixture',
                     'approval_ref': 'test fixture only', 'external_source_approved': True, 'commit': False, 'push': False}
        save(self.auth_path, self.auth)


class AuthorityTests(Fixture):
    def test_A01_missing_or_modified_authorization(self):
        with self.assertRaises(FileNotFoundError):
            authorized(self.config, self.base / 'absent')
        for field in ('config_sha256', 'controller_sha256', 'acceptance_sha256', 'head', 'branch', 'source'):
            changed = dict(self.auth, **{field: 'wrong'})
            save(self.auth_path, changed)
            with self.assertRaises(Blocked, msg=field):
                authorized(self.config, self.auth_path)

    def test_A01_scope_and_private_source(self):
        self.auth['external_source_approved'] = False
        save(self.auth_path, self.auth)
        with self.assertRaises(Blocked):
            authorized(self.config, self.auth_path)
        a = manifest(self.source)
        (self.source / 'outside').write_text('new')
        with self.assertRaises(Blocked):
            scope_check(a, manifest(self.source), ['value.py'])

    def test_A01_authority_source_overlap_rejected(self):
        with self.assertRaises(Blocked):
            controller.start(self.source / 'control', self.config_path, self.auth_path)
        self.assertFalse((self.source / 'control').exists())

    def test_A01_ignored_input_and_tracked_exclusion_rejected(self):
        self.config['excludes'] = ['value.py'];self.authorize()
        r = controller.start(self.control, self.config_path, self.auth_path)
        self.assertEqual(r['state'], 'BLOCKED');self.assertIn('committed baseline', r['data']['reason'])

    def test_A03_incomplete_initial_snapshot_preserved_and_resumed(self):
        original = controller.snapshot
        def interrupt(source, dest, *args, **kwargs):
            Path(dest).mkdir();(Path(dest) / 'partial').write_text('preserve me')
            raise OSError('injected snapshot interruption')
        controller.snapshot = interrupt
        try:r = controller.start(self.control, self.config_path, self.auth_path)
        finally:controller.snapshot = original
        self.assertEqual(r['state'], 'BLOCKED')
        result = controller.resume(Store(self.control), r['id'])
        self.assertEqual(result['state'], 'READY', result['data'].get('reason'))
        saved = list((self.control / r['id']).glob('interrupted-work-*/partial'))
        self.assertEqual(len(saved), 1);self.assertEqual(saved[0].read_text(), 'preserve me')

    def test_A05_home_inside_original_source_rejected(self):
        self.config['bindings']['implementer']['home'] = str(self.source / 'runtime')
        self.authorize()
        result = controller.start(self.control, self.config_path, self.auth_path)
        self.assertEqual(result['state'], 'BLOCKED')
        self.assertIn('runtime home overlaps', result['data']['reason'])
        self.assertFalse((self.source / 'runtime').exists())

    def test_A16_framework_source_not_gated_to_ready(self):
        p = self.source / 'tools/orchestration/controller.py';p.parent.mkdir(parents=True);p.write_text('# fixture framework marker')
        git(self.source, 'add', 'tools/orchestration/controller.py');git(self.source, 'commit', '-qm', 'framework fixture')
        self.authorize()
        with self.assertRaisesRegex(Blocked, 'external bootstrap'):
            controller.start(self.control, self.config_path, self.auth_path)

    def test_A10_new_policy_rejects_supplied_uuid(self):
        self.config['bindings']['reviewer']['session_id'] = str(uuid.uuid4())
        with self.assertRaisesRegex(Blocked, 'new-session'):
            config_check(self.config)

    def test_A05_external_mode_requires_bwrap(self):
        self.config['bindings']['implementer']['external_sandbox'] = True
        with self.assertRaises(Blocked):
            config_check(self.config)

    def test_A02_competing_live_lease_and_reused_pid(self):
        with lease(self.base / 'lock'):
            with self.assertRaises(Blocked):
                with lease(self.base / 'lock'):
                    pass
        me = process_identity(os.getpid())
        self.assertTrue(alive(me))
        self.assertFalse(alive(dict(me, start='wrong')))
        self.assertFalse(stop(dict(me, start='wrong')))

    def test_A02_second_controller_process_cannot_acquire_target(self):
        tool = Path(__file__).resolve().parents[1] / 'tools/devflower.py'
        with lease(self.source / '.git/devflower-writer.lock'):
            p = subprocess.run([sys.executable, str(tool), 'run', '--control', str(self.control),
                '--config', str(self.config_path), '--authorization', str(self.auth_path)], capture_output=True, text=True)
        self.assertEqual(p.returncode, 1)
        self.assertEqual(json.loads(p.stdout)['state'], 'BLOCKED')
        self.assertIn('live lease', json.loads(p.stdout)['reason'])

    def test_A03_transaction_rollback(self):
        s = Store(self.control)
        run = s.create({})
        before = len(s.audit(run))
        original = s._event
        def fail(*args):
            raise RuntimeError('injected before event commit')
        s._event = fail
        with self.assertRaises(RuntimeError):
            s.transition(run, 'READY')
        self.assertEqual(s.get(run)['state'], 'CREATED')
        self.assertEqual(len(s.audit(run)), before)
        s._event = original
        s.transition(run, 'VERIFYING')
        other = Store(self.control)
        self.assertEqual(other.get(run)['state'], 'VERIFYING')
        self.assertEqual(other.audit(run)[-1]['kind'], 'VERIFYING')

    def test_A03_process_death_before_and_after_transaction_commit(self):
        s = Store(self.control); run = s.create({})
        code = '''import sys,time
sys.path.insert(0,sys.argv[1]);from orchestration.store import Store
s=Store(sys.argv[2]);run=sys.argv[3]
if sys.argv[4]=='before':
 s.db.execute('BEGIN IMMEDIATE');s.db.execute('UPDATE runs SET state=? WHERE id=?',('COMPLETED',run));s._event(run,'COMPLETED',{})
else: s.transition(run,'VERIFYING')
print('ready',flush=True);time.sleep(30)
'''
        for stage in ('before', 'after'):
            p = subprocess.Popen([sys.executable, '-c', code, str(Path(__file__).resolve().parents[1] / 'tools'),
                                  str(self.control), run, stage], stdout=subprocess.PIPE, text=True)
            self.assertEqual(p.stdout.readline().strip(), 'ready')
            p.kill();p.wait();p.stdout.close()
            recovered = Store(self.control)
            self.assertEqual(recovered.get(run)['state'], 'CREATED' if stage == 'before' else 'VERIFYING')
            self.assertEqual(recovered.audit(run)[-1]['kind'], 'CREATED' if stage == 'before' else 'VERIFYING')

    def test_A04_complete_tree_modes_deleted_links(self):
        baseline = manifest(self.source)
        (self.source / 'value.py').write_text('staged\n')
        git(self.source, 'add', 'value.py')
        (self.source / 'value.py').write_text('unstaged\n')
        (self.source / 'new').write_bytes(b'\x00new\r\n')
        (self.source / 'new').chmod(0o755)
        (self.source / 'link').symlink_to('/etc/shadow')
        copied = snapshot(self.source, self.base / 'copy', baseline=baseline)
        self.assertEqual(copied['sha256'], tree_hash(self.source))
        by_path = {x['path']: x for x in copied['entries']}
        self.assertEqual(by_path['new']['mode'], '100755')
        self.assertEqual(by_path['link']['sha256'], digest(b'/etc/shadow'))
        (self.source / 'value.py').unlink()
        copied = snapshot(self.source, self.base / 'copy2', baseline=baseline)
        self.assertEqual(copied['deleted'], ['value.py'])

    def test_A04_reject_submodule_filters(self):
        for file, data in (('.gitmodules', ''), ('.gitattributes', '*.txt filter=lfs')):
            p = self.source / file
            p.write_text(data)
            with self.assertRaises(Blocked):
                manifest(self.source)
            p.unlink()

    def test_A05_actual_isolation_probes(self):
        self.control.mkdir()
        proof = controller.isolation_probe(self.control, self.source, self.base / 'probe-home')
        self.assertTrue(proof['read_and_write_denied'])
        secret = self.base / 'delivery-credential'
        secret.write_text('not-a-real-credential')
        argv = [sys.executable, '-c', 'import pathlib,sys; pathlib.Path(sys.argv[1]).read_text()', str(secret)]
        result, _, _ = execute(argv, self.source, self.base / 'home', read=[str(self.source)])
        self.assertNotEqual(result['exit'], 0)
        result, _, _ = execute([sys.executable, '-c', 'import os,sys; os.kill(int(sys.argv[1]),0)', str(os.getpid())],
                              self.source, self.base / 'home')
        self.assertNotEqual(result['exit'], 0)

    def test_A10_binding_wrong_project_role_uuid(self):
        for key, value in (('project', 'codeweave'), ('role', 'implementer'), ('session_id', '--last')):
            bad = copy.deepcopy(self.config)
            bad['bindings']['reviewer'][key] = value
            with self.assertRaises(Blocked):
                config_check(bad)

    def test_A01_C_requires_real_human_events(self):
        self.config['policy']['mode'] = 'C'
        self.authorize()
        with self.assertRaises(Blocked):
            authorized(self.config, self.auth_path)
        self.auth['human_events'] = [{'gate': g, 'actor': 'user', 'evidence_ref': 'test-only actual-event-ref'} for g in ('G1', 'G2', 'G3', 'G4')]
        save(self.auth_path, self.auth)
        authorized(self.config, self.auth_path)


class ProcessTests(Fixture):
    def test_A06_implementer_blocked_stops_before_reviewer(self):
        self.fake.write_text(FAKE.replace("'status':'IMPLEMENTED'", "'status':'BLOCKED'"))
        r = controller.start(self.control, self.config_path, self.auth_path)
        self.assertEqual(r['state'], 'BLOCKED')
        self.assertIn('implementer BLOCKED', r['data']['reason'])
        requests = [o for o in Store(self.control).operations(r['id']) if o['kind'] == 'AGENT_REQUEST']
        self.assertEqual(len(requests), 1)
    def test_A06_flood_timeout_and_real_exit(self):
        r, _, _ = execute([sys.executable, '-c', 'import sys; sys.stderr.write("x"*2000000)'], self.source,
                           self.base / 'home', cap=4096)
        self.assertTrue(r['overflow'])
        r, _, _ = execute([sys.executable, '-c', 'import time; time.sleep(10)'], self.source,
                           self.base / 'home', timeout=.2)
        self.assertTrue(r['timeout'])
        self.assertFalse(alive(r['process']))
        self.assertTrue(alive(process_identity(os.getpid())))

    def test_A06_bad_protocol_missing_terminal_and_auth_failure(self):
        adapter = adapters.CLI('codex', {}, {})
        good = {'exit': 0, 'timeout': False, 'overflow': False, 'cancelled': False}
        for raw in (b'invalid', b'', b'[]', b'123', b'{"type":"thread.started"}', b'{"type":"turn.failed"}'):
            with self.assertRaises(Blocked):
                adapter.collect(good, raw)
        with self.assertRaises(Blocked):
            adapter.collect(dict(good, exit=1), b'{}')

    def test_A06_detached_descendant_denied_and_background_stopped(self):
        r, _, _ = execute([sys.executable, '-c', 'import os; os.setsid()'], self.source, self.base / 'home')
        self.assertNotEqual(r['exit'], 0)
        script = 'import os,time; pid=os.fork(); os._exit(0) if pid else None; os.close(1);os.close(2);time.sleep(20)'
        r, _, _ = execute([sys.executable, '-c', script], self.source, self.base / 'home', timeout=2)
        self.assertTrue(r['timeout'])

    def test_A11_no_raw_tokens_or_reasoning_in_database(self):
        s = Store(self.control)
        run = s.create({})
        secret = 'TOKEN_FAKE_DO_NOT_PERSIST'
        execute([sys.executable, '-c', 'import sys;s=sys.stdin.read();sys.stderr.write(s);print(s)'],
                self.source, self.base / 'home', store=s, run=run,
                input_text=secret + ' hidden_reasoning_fixture')
        persisted = '\n'.join(s.db.iterdump())
        self.assertNotIn(secret, persisted)
        self.assertNotIn('hidden_reasoning_fixture', persisted)

    def test_A11_provider_token_echo_in_final_report_redacted(self):
        home = self.base / 'model-home';(home / '.claude').mkdir(parents=True)
        token = 'FIXTURE_AUTH_TOKEN_NO_REAL_SECRET'
        (home / '.claude/settings.json').write_text(json.dumps({'env': {'ANTHROPIC_AUTH_TOKEN': token}}))
        clean = redact({'verdict': 'NEEDS_CORRECTION', 'limitations': ['do not log ' + token]}, credentials(home))
        self.assertEqual(clean['verdict'], 'NEEDS_CORRECTION')
        self.assertNotIn(token, json.dumps(clean));self.assertIn('[REDACTED]', json.dumps(clean))
        (self.source / 'leaked').write_text(token)
        with self.assertRaisesRegex(Blocked, 'known provider credential'):
            check_tree(self.source, credentials(home))

    def test_A06_cancel_request_only_owned_group(self):
        s = Store(self.control)
        run = s.create({'cancel_requested': True})
        r, _, _ = execute([sys.executable, '-c', 'import time; time.sleep(10)'], self.source,
                           self.base / 'home', store=s, run=run)
        self.assertTrue(r['cancelled'])
        self.assertTrue(alive(process_identity(os.getpid())))

    def test_A07_zero_tests_skip_and_false_exit(self):
        for tests, failures, skipped in ((0, 0, 0), (1, 0, 1), (1, 1, 0)):
            self.config['policy']['verification'][0]['argv'] = [sys.executable, '-c',
                'import pathlib,sys; pathlib.Path(sys.argv[1]).write_text(sys.argv[2])', '{result}',
                json.dumps(dict(tests=tests, failures=failures, errors=0, skipped=skipped))]
            results = verify(self.config, self.source, self.base / f'v{tests}{failures}{skipped}', 'r', 1, tree_hash(self.source), 'a')
            self.assertFalse(results[0]['passed'])

    def test_A07_forged_result_symlink(self):
        old = self.base / 'old-result'
        old.write_text('{"tests":1,"failures":0,"errors":0,"skipped":0}')
        link = self.base / 'link'
        link.symlink_to(old)
        with self.assertRaises(Blocked):
            counts(link, 'controller-json')

    def test_A07_junit_actual_cases_and_contradictory_summary(self):
        path = self.base / 'junit.xml'
        path.write_text('<testsuite tests="1" failures="0" errors="0" skipped="0"><testcase name="ok"/></testsuite>')
        self.assertEqual(counts(path, 'junit'), dict(tests=1, failures=0, errors=0, skipped=0))
        path.write_text('<testsuite tests="1" failures="1"><testcase name="false-pass"/></testsuite>')
        with self.assertRaisesRegex(Blocked, 'contradicts'):
            counts(path, 'junit')
        path.write_text('<testsuite><testcase status="notrun" result="suppressed"/></testsuite>')
        self.assertEqual(counts(path, 'junit')['skipped'], 1)
        path.write_text('<bad')
        with self.assertRaisesRegex(Blocked, 'invalid JUnit'):
            counts(path, 'junit')

    def test_A09_simulated_reject_fix_review_bound_sessions(self):
        self.config['policy']['delivery']['commit'] = True
        self.authorize();self.auth['commit'] = True;save(self.auth_path, self.auth)
        before = tree_hash(self.source)
        result = controller.start(self.control, self.config_path, self.auth_path)
        self.assertEqual(result['state'], 'READY', result['data'].get('reason'))
        self.assertEqual(result['data']['round'], 2)
        self.assertEqual([r['verdict'] for r in result['data']['reviews']], ['NEEDS_CORRECTION', 'ACCEPT'])
        self.assertEqual(before, tree_hash(self.source))
        self.assertEqual(len(result['data']['sessions']), 2)
        self.assertFalse(any('reasoning' in str(e) for e in Store(self.control).audit(result['id'])))
        Path(result['data']['candidate_path'], 'value.py').write_text('changed after review')
        with self.assertRaisesRegex(Blocked, 'candidate changed'):
            controller.deliver_run(Store(self.control), result['id'])

    def test_A07_evidence_changed_after_ready(self):
        self.config['policy']['delivery']['commit'] = True
        self.authorize();self.auth['commit'] = True;save(self.auth_path, self.auth)
        result = controller.start(self.control, self.config_path, self.auth_path)
        self.assertEqual(result['state'], 'READY', result['data'].get('reason'))
        Path(result['data']['verification'][0]['result_path']).write_text('{}')
        with self.assertRaisesRegex(Blocked, 'verification evidence changed'):
            controller.deliver_run(Store(self.control), result['id'])

    def test_A10_model_effort_configuration_changed(self):
        home = Path(self.config['bindings']['implementer']['home'])
        (home / '.codex').mkdir(parents=True)
        p = home / '.codex/config.toml'
        p.write_text('model_reasoning_effort="high"')
        r = controller.start(self.control, self.config_path, self.auth_path)
        self.assertEqual(r['state'], 'READY', r['data'].get('reason'))
        p.write_text('model_reasoning_effort="low"')
        with self.assertRaises(Blocked):
            controller.binding_check(Store(self.control), r['data'])

    def test_A10_explicit_wrong_session_rejected(self):
        # Simulated CLI deliberately responds from another real process session.
        self.fake.write_text(FAKE.replace('session=args[', 'session=args[').replace("if 'exec' in args:", "session=str(uuid.uuid4())\nif 'exec' in args:"))
        binding = self.config['bindings']['implementer']
        adapter = adapters.CLI('codex', binding, self.config['policy']['limits'])
        with self.assertRaises(Blocked):
            adapter.start('probe', self.source, self.bin, session=str(uuid.uuid4()))

    def test_A09_budget_and_nonprogress(self):
        self.config['goal'] = 'do nothing'
        self.config['policy']['limits']['max_review_rounds'] = 1
        self.authorize()
        r = controller.start(self.control, self.config_path, self.auth_path)
        self.assertEqual(r['state'], 'BLOCKED')
        self.assertIn('budget', r['data']['reason'])

    def test_A09_two_pre_spawn_retries_then_blocked(self):
        s = Store(self.control); run = s.create({})
        binding = dict(self.config['bindings']['implementer'], executable=str(self.base / 'missing-cli'))
        with self.assertRaisesRegex(Blocked, 'before spawn'):
            controller.agent_step(s, run, 'codex', binding, self.config['policy']['limits'],
                                  'fixture', self.source, self.bin, None, None)
        ops = s.operations(run)
        self.assertEqual(len([o for o in ops if o['kind'] == 'INFRASTRUCTURE_RETRY']), 2)
        self.assertFalse(any(o['kind'] == 'PROCESS' for o in ops))

    def test_A09_identical_candidate_blockers_stop_two_rounds(self):
        self.fake.write_text(FAKE.replace("('42' if 'Prior review/verification feedback:\\n{}' not in prompt else '1')", "'1'"))
        r = controller.start(self.control, self.config_path, self.auth_path)
        self.assertEqual(r['state'], 'BLOCKED', r['data'].get('reason'))
        self.assertEqual(r['data']['round'], 2)

    def test_A11_status_read_only_bounded(self):
        s = Store(self.control)
        run = s.create({})
        for n in range(210):
            s.transition(run, 'VERIFYING', n=n)
        readonly = Store(self.control, readonly=True)
        self.assertEqual(len(readonly.audit(run, limit=1000)), 200)
        self.assertEqual(len(readonly.audit(run, after=200)), 11)
        with self.assertRaises(sqlite3.OperationalError):
            readonly.transition(run, 'READY')


class GateTests(unittest.TestCase):
    def setUp(self):
        self.process = {'exit': 0, 'timeout': False, 'overflow': False, 'cancelled': False}
        self.impl = {'session_id': str(uuid.uuid4()), 'process': self.process, 'report': {'status': 'IMPLEMENTED'}}
        self.review = {'session_id': str(uuid.uuid4()), 'process': self.process, 'report': {
            'schema_version': 1, 'run_id': 'r', 'round': 1, 'candidate_sha256': 'a'*64, 'acceptance_sha256': 'b'*64,
            'verdict': 'ACCEPT', 'contracts': [{'id': 'unit', 'status': 'PASS', 'evidence_refs': ['unit']}], 'findings': [], 'limitations': []}}
        self.verification = [{'id': 'unit', 'run_id': 'r', 'round': 1, 'candidate_sha256': 'a'*64, 'acceptance_sha256': 'b'*64,
                              'passed': True, 'process': self.process, 'counts': dict(tests=1, failures=0, errors=0, skipped=0)}]

    def check(self):
        return gate('r', 1, 'a'*64, 'b'*64, ['unit'], self.verification, self.impl, self.review)

    def test_A08_accept_not_sufficient(self):
        self.assertTrue(self.check())
        for key, value in (('run_id', 'other'), ('round', 2), ('candidate_sha256', 'c'*64), ('acceptance_sha256', 'd'*64), ('verdict', 'ACCEPT_WITH_LIMITATIONS')):
            old = self.review['report'][key]
            self.review['report'][key] = value
            with self.assertRaises(Blocked, msg=key):
                self.check()
            self.review['report'][key] = old
        for status in ('FAIL', 'BLOCKED', 'NOT_APPLICABLE'):
            self.review['report']['contracts'][0]['status'] = status
            with self.assertRaises(Blocked):
                self.check()

    def test_A08_accept_with_failed_test_open_finding_missing_evidence(self):
        self.verification[0]['passed'] = False
        with self.assertRaisesRegex(Blocked, 'verification failed'):
            self.check()
        self.verification[0]['passed'] = True
        self.review['report']['findings'] = [{'id': 'F1', 'severity': 'P1', 'status': 'OPEN', 'title': 'block', 'contract_ids': ['unit'], 'evidence_refs': ['unit']}]
        with self.assertRaisesRegex(Blocked, 'open required finding'):
            self.check()
        self.review['report']['findings'] = []
        self.review['report']['contracts'][0]['evidence_refs'] = ['/etc/passwd']
        with self.assertRaisesRegex(Blocked, 'unknown review evidence'):
            self.check()
        self.review['report']['contracts'][0]['evidence_refs'] = ['unit']
        self.verification = []
        with self.assertRaisesRegex(Blocked, 'missing or duplicate verification'):
            self.check()

    def test_A07_true_pass_flag_with_failed_counters_or_process(self):
        self.verification[0]['counts']['failures'] = 1
        with self.assertRaisesRegex(Blocked, 'contradicts PASS'):
            self.check()
        self.verification[0]['counts']['failures'] = 0
        self.verification[0]['process'] = dict(self.process, exit=1)
        with self.assertRaisesRegex(Blocked, 'verifier process'):
            self.check()


class GitTests(Fixture):
    def test_A12_mutation_during_git_tree_rejected(self):
        target = self.target(); candidate = self.base / 'candidate';snapshot(self.source, candidate)
        expected = tree_hash(candidate); original = delivery.make_tree
        def mutate(root, tree):
            (Path(tree) / 'value.py').write_text('UNREVIEWED')
            return original(root, tree)
        delivery.make_tree = mutate
        try:
            s = Store(self.control); run = s.create({})
            with self.assertRaisesRegex(Blocked, 'prospective commit'):
                delivery.deliver(s, run, candidate, [target], False, expected)
            self.assertFalse(any(o['kind'] == 'COMMIT' for o in s.operations(run)))
        finally:
            delivery.make_tree = original
    def target(self, root=None, kind='source'):
        root = root or self.source
        remote = self.base / ('remote-' + kind + '.git')
        subprocess.run(['git', 'clone', '-q', '--bare', str(root), str(remote)], check=True)
        git(root, 'remote', 'add', 'origin', str(remote))
        return {'kind': kind, 'root': str(root), 'remote': str(remote), 'branch': git(root, 'branch', '--show-current'),
                'expected_tip': git(root, 'rev-parse', 'HEAD')}

    def test_A12_exact_tree_index_preserved_and_commit_recovery(self):
        target = self.target()
        candidate = self.base / 'candidate'
        snapshot(self.source, candidate)
        (candidate / 'value.py').unlink()
        (candidate / 'exec').write_text('new\r\n')
        (candidate / 'exec').chmod(0o755)
        (candidate / 'link').symlink_to('/outside')
        before = (self.source / '.git/index').read_bytes()
        s = Store(self.control)
        run = s.create({})
        tree = delivery.make_tree(self.source, candidate)
        one = delivery.commit(s, run, target, tree)
        two = delivery.commit(s, run, target, tree)
        self.assertEqual(one, two)
        self.assertEqual(before, (self.source / '.git/index').read_bytes())
        self.assertEqual(git(self.source, 'rev-parse', one + '^{tree}'), tree)
        self.assertIn('120000', git(self.source, 'ls-tree', tree))

    def test_A12_hooks_filters_dirty_and_wrong_remote(self):
        target = self.target()
        hook = self.source / '.git/hooks/pre-commit'
        hook.write_text('#!/bin/sh\nexit 0\n')
        hook.chmod(0o755)
        with self.assertRaises(Blocked):
            delivery.checks(target)
        hook.unlink()
        git(self.source, 'config', 'core.hooksPath', '/external-hooks')
        with self.assertRaises(Blocked):
            delivery.checks(target)
        git(self.source, 'config', '--unset', 'core.hooksPath')
        (self.source / 'untracked').write_text('existing work')
        with self.assertRaises(Blocked):
            delivery.checks(target)
        (self.source / 'untracked').unlink()
        with self.assertRaises(Blocked):
            delivery.checks(dict(target, remote='/wrong'))

    def test_A12_commit_interrupt_before_receipt_reuses_same_sha(self):
        target = self.target()
        s = Store(self.control)
        run = s.create({})
        tree = delivery.make_tree(self.source, self.source)
        original = s.finish
        def crash(*args, **kwargs):
            raise RuntimeError('injected after commit object before receipt')
        s.finish = crash
        with self.assertRaises(RuntimeError):
            delivery.commit(s, run, target, tree)
        s.finish = original
        sha = delivery.commit(s, run, target, tree)
        self.assertEqual(sha, delivery.commit(s, run, target, tree))
        self.assertEqual(len([o for o in s.operations(run) if o['kind'] == 'COMMIT']), 1)

    def test_A13_lost_receipt_remote_readback_and_race(self):
        target = self.target()
        candidate = self.base / 'candidate'
        snapshot(self.source, candidate)
        (candidate / 'value.py').write_text('VALUE=42\n')
        s = Store(self.control)
        run = s.create({})
        sha = delivery.commit(s, run, target, delivery.make_tree(self.source, candidate))
        calls = []
        def lost(argv):
            calls.append(argv)
            subprocess.run(argv, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            raise subprocess.TimeoutExpired(argv, 30)
        self.assertEqual(delivery.push(s, run, target, sha, lost), sha)
        self.assertEqual(delivery.push(s, run, target, sha, lost), sha)
        self.assertEqual(len(calls), 1)
        git(target['remote'], 'update-ref', 'refs/heads/' + target['branch'], target['expected_tip'])
        with self.assertRaises(Blocked):
            delivery.push(s, run, dict(target, expected_tip='0'*40), sha)

    def test_A13_two_repos_partial_delivery(self):
        target = self.target()
        records = repo(self.base / 'records', 'project/fixture')
        second = self.target(records, 'records')
        second['receipt_path'] = 'project/receipt.json'
        # Divergent expected tip must fail after the first successful push.
        second['expected_tip'] = '0'*40
        candidate = self.base / 'candidate'
        snapshot(self.source, candidate)
        (candidate / 'value.py').write_text('VALUE=42\n')
        s = Store(self.control)
        run = s.create({})
        with self.assertRaises(Blocked):
            delivery.deliver(s, run, candidate, [target, second], True)
        self.assertEqual(s.get(run)['state'], 'PARTIAL_DELIVERY')
        receipt = s.get(run)['data']['receipts'][0]
        self.assertEqual(delivery.remote_tip(target['remote'], target['branch']), receipt['commit'])
        self.assertEqual(delivery.remote_tip(second['remote'], second['branch']), git(records, 'rev-parse', 'HEAD'))

    def test_A13_partial_retry_does_not_repeat_source_push(self):
        target = self.target()
        records = repo(self.base / 'records', 'project/fixture')
        second = self.target(records, 'records')
        second['receipt_path'] = 'project/receipt.json'
        hook = Path(second['remote']) / 'hooks/pre-receive'
        hook.write_text('#!/bin/sh\nexit 1\n')
        hook.chmod(0o755)
        candidate = self.base / 'candidate'
        snapshot(self.source, candidate)
        (candidate / 'value.py').write_text('VALUE=42\n')
        s = Store(self.control)
        run = s.create({})
        with self.assertRaises(Blocked):
            delivery.deliver(s, run, candidate, [target, second], True)
        self.assertEqual(s.get(run)['state'], 'PARTIAL_DELIVERY')
        source_sha = s.get(run)['data']['receipts'][0]['commit']
        hook.unlink()
        receipts = delivery.deliver(s, run, candidate, [target, second], True)
        self.assertEqual(receipts[0]['commit'], source_sha)
        self.assertEqual(s.get(run)['state'], 'COMPLETED')

    def test_A13_generated_receipt_symlink_cannot_escape(self):
        target = self.target()
        records = repo(self.base / 'records', 'project/fixture')
        outside = self.base / 'outside'
        outside.mkdir()
        (records / 'project').symlink_to(outside)
        git(records, 'add', 'project'); git(records, 'commit', '-qm', 'malicious link fixture')
        second = self.target(records, 'records')
        second['receipt_path'] = 'project/receipt.json'
        s = Store(self.control); run = s.create({})
        with self.assertRaises(Blocked):
            delivery.deliver(s, run, self.source, [target, second], False)
        self.assertFalse((outside / 'receipt.json').exists())

    def test_A13_records_tree_does_not_import_ignored_credentials(self):
        records = repo(self.base / 'records', 'project/fixture')
        (records / '.gitignore').write_text('.env\n')
        git(records, 'add', '.gitignore');git(records, 'commit', '-qm', 'ignore local credentials')
        (records / '.env').write_text('PRIVATE_FIXTURE_CREDENTIAL')
        index = (records / '.git/index').read_bytes()
        tree = delivery.records_tree(records, 'project/receipt.json', {'run_id': 'test', 'source': {'commit': 'a'*40}})
        self.assertNotIn('.env', git(records, 'ls-tree', '-r', '--name-only', tree).splitlines())
        self.assertEqual(index, (records / '.git/index').read_bytes())


if __name__ == '__main__':
    unittest.main()
