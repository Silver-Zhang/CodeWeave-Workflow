"""Issue 6 contracts on the real Runtime/Store/HTTP, never model acceptance."""
import copy
from http.server import ThreadingHTTPServer
import json
import os
import threading
import unittest
from urllib.request import Request, urlopen
from urllib.error import HTTPError

import test_usable
from orchestration.common import Blocked
from orchestration.contracts import config_check, schema, validate
from orchestration.gate import gate
from orchestration.store import Store, process_identity
from orchestration.verification import verify
from studio.usable_graph import template, node, compile_plan
from studio.usable_server import handler


def custom_document():
    doc = template('B')
    doc['name'] = '用户实际工作流'
    rename = {n['id']: 'custom-' + n['id'] for n in doc['nodes']}
    for n in doc['nodes']:
        n['id'] = rename[n['id']]
        n['label'] = '用户的 ' + n['type']
    for e in doc['edges']:
        e['source'], e['target'] = rename[e['source']], rename[e['target']]
    second = node('verifier', 'separate-check');second['label'] = '第二组验证'
    doc['nodes'].append(second)
    for e in doc['edges']:
        if e['source'] == 'custom-verifier' and e['on'] == 'next':
            e['target'] = second['id']
    doc['edges'].append(dict(source=second['id'], target='custom-reviewer', on='next'))
    doc['nodes'].reverse()  # Array order is not execution order.
    return doc


class WorkflowTests(unittest.TestCase):
    setUp = test_usable.RuntimeTests.setUp
    request = test_usable.RuntimeTests.request

    def prepare(self):
        request = self.request();request['workflow'] = custom_document()
        return self.runtime.prepare(request)

    def record(self, state='VERIFYING', number=2):
        config = self.prepare()['data']['config']
        store = Store(self.runtime.control);self.addCleanup(store.db.close)
        data = dict(config=config, source={'root': str(self.source)}, round=number, sessions={},
                    candidate={'sha256': 'a' * 64}, candidate_round=number,
                    acceptance_sha256='b' * 64, authorization_sha256='c' * 64)
        run = store.create(data);store.transition(run, state, round=number)
        return store, run, data

    def reports(self, store, run, data, failed=False, number=None):
        number = data['round'] if number is None else number
        for i, identity in enumerate(['custom-verifier', 'separate-check']):
            op = store.intent(run, 'VERIFICATION', dict(run_id=run, round=number, verification_id=identity,
                candidate_sha256=data['candidate']['sha256'], acceptance_sha256=data['acceptance_sha256']))
            store.finish(op, 'VALIDATED', passed=not(failed and i == 1),
                counts=dict(tests=i + 1, failures=int(failed and i == 1), errors=0, skipped=0))

    def graph(self, run):
        return self.runtime.snapshot(run)['workflow_graph']

    def http_snapshot(self, run):
        if not hasattr(self, '_workflow_http'):
            capability = 'workflow-regression-only'
            server = ThreadingHTTPServer(('127.0.0.1', 0), handler(self.runtime, capability))
            thread = threading.Thread(target=server.serve_forever, daemon=True);thread.start()
            self.addCleanup(thread.join);self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
            self._workflow_http = ('http://127.0.0.1:' + str(server.server_port), capability)
        url, capability = self._workflow_http
        request = Request(url + '/api/run?id=' + run, headers={'Authorization': 'Bearer ' + capability})
        with urlopen(request) as response:
            return json.load(response)

    def final_report(self, run, data, **updates):
        report = dict(id='custom-verifier', run_id=run, round=data['round'],
                      candidate_sha256=data['candidate']['sha256'], acceptance_sha256=data['acceptance_sha256'],
                      passed=True, counts=dict(tests=1, failures=0, errors=0, skipped=0),
                      process=dict(exit=0, timeout=False, overflow=False, cancelled=False))
        return dict(report, **updates)

    def review_report(self, run, data, findings, verdict='ACCEPT'):
        return dict(schema_version=1, run_id=run, round=data['round'],
                    candidate_sha256=data['candidate']['sha256'], acceptance_sha256=data['acceptance_sha256'],
                    verdict=verdict, findings=findings, limitations=[],
                    contracts=[dict(id=identity, status='PASS', evidence_refs=['source-inspection'])
                               for identity in data['config']['policy']['required_contracts']])

    def assert_verifier_status(self, run, status):
        for snapshot in (self.runtime.snapshot(run), self.http_snapshot(run)):
            node = next(n for n in snapshot['workflow_graph']['nodes'] if n['id'] == 'custom-verifier')
            self.assertEqual(node['status'], status)
            self.assertEqual(node['results'][0]['status'], status)
            legacy = next(n for n in snapshot['graph']['nodes'] if n['id'] == 'verify-0')
            self.assertEqual(legacy['status'], status)

    def test_final_report_requires_successful_actual_process_receipt(self):
        store, run, data = self.record()
        good = self.final_report(run, data)
        store.transition(run, 'VERIFYING', verification=[good])
        self.assert_verifier_status(run, 'passed')
        bad_receipts = [None, {}, [], dict(good['process'], exit=1), dict(good['process'], exit=-15)]
        for field in ('exit', 'timeout', 'overflow', 'cancelled'):
            missing = dict(good['process']);del missing[field]
            bad_receipts.append(missing)
        for field in ('timeout', 'overflow', 'cancelled'):
            bad_receipts.append(dict(good['process'], **{field: True}))
        for receipt in bad_receipts:
            with self.subTest(process=receipt):
                store.transition(run, 'VERIFYING', verification=[dict(good, process=receipt)])
                self.assert_verifier_status(run, 'failed')
        missing = dict(good);del missing['process']
        store.transition(run, 'VERIFYING', verification=[missing])
        self.assert_verifier_status(run, 'failed')

    def test_actual_python_parent_reports_use_process_receipts_in_fallback(self):
        from orchestration.common import tree_hash
        store, run, data = self.record()
        for label, code, expected in (('success', 'VALUE = 42\n', 'passed'),
                                      ('failure', 'raise SystemExit(7)\n', 'failed')):
            (self.source / 'value.py').write_text(code)
            reports = verify(data['config'], self.source, self.root / ('actual-' + label),
                             run, data['round'], tree_hash(self.source), data['acceptance_sha256'])
            self.assertEqual([r['counts']['tests'] for r in reports], [1, 1])
            self.assertTrue(all(r['process']['process']['pid'] for r in reports))
            self.assertEqual(reports[0]['process']['exit'], 0 if label == 'success' else 7)
            data['candidate']['sha256'] = tree_hash(self.source)
            store.transition(run, 'VERIFYING', candidate=data['candidate'], verification=reports)
            self.assert_verifier_status(run, expected)
            if label == 'failure':
                # A contradictory PASS claim cannot override an observed Python exit.
                claimed = [dict(r, passed=True, counts=dict(tests=1, failures=0, errors=0, skipped=0)) for r in reports]
                store.transition(run, 'VERIFYING', verification=claimed)
                self.assert_verifier_status(run, 'failed')

    def test_invalid_counts_cannot_pass_validated_operation_or_final_report(self):
        store, run, data = self.record()
        good = self.final_report(run, data)
        c = good['counts']
        invalid = [None, {}, dict(c, tests=0), dict(c, tests=True), dict(c, tests=1.5),
                   dict(c, tests='1'), dict(c, failures=-1), dict(c, failures=1), dict(c, errors=1),
                   dict(c, skipped=1), dict(c, failures=1, errors=1), dict(c, fabricated=1)]
        for field in c:
            missing = dict(c);del missing[field]
            invalid.append(missing)
        for counters in invalid:
            with self.subTest(path='report', counts=counters):
                store.transition(run, 'VERIFYING', verification=[dict(good, counts=counters)])
                self.assert_verifier_status(run, 'failed')
        op = store.intent(run, 'VERIFICATION', dict(run_id=run, round=data['round'],
            verification_id=good['id'], candidate_sha256=good['candidate_sha256'], acceptance_sha256=good['acceptance_sha256']))
        for counters in invalid:
            with self.subTest(path='validated', counts=counters):
                store.finish(op, 'VALIDATED', passed=True, counts=counters)
                self.assert_verifier_status(run, 'failed')

    def test_validated_operation_does_not_require_a_fabricated_final_report(self):
        store, run, data = self.record()
        good = self.final_report(run, data)
        op = store.intent(run, 'VERIFICATION', dict(run_id=run, round=data['round'],
            verification_id=good['id'], candidate_sha256=good['candidate_sha256'], acceptance_sha256=good['acceptance_sha256']))
        store.finish(op, 'VALIDATED', passed=True, counts=good['counts'])
        self.assert_verifier_status(run, 'passed')
        self.assertNotIn('verification', store.get(run)['data'])
        store.finish(op, 'VERIFICATION_BLOCKED')
        store.transition(run, 'VERIFYING', verification=[good])
        self.assert_verifier_status(run, 'blocked')
        store.finish(op, 'VALIDATED', passed=False, counts=good['counts'])
        self.assert_verifier_status(run, 'failed')

    def test_review_optional_and_required_findings_follow_mechanical_gate(self):
        store, run, data = self.record(state='GATING')
        required = data['config']['policy']['required_contracts']
        process = dict(exit=0, timeout=False, overflow=False, cancelled=False)
        implementation = dict(report={'status': 'IMPLEMENTED'}, process=process, session_id='implementer-fixture')
        verification = [self.final_report(run, data, id=identity) for identity in
                        data['config']['studio_workflow']['verification_ids']]
        # Keep optional findings visible and count every non-CLOSED status.
        for severity, contracts, mandatory in (('P3', required, False), ('P2', ['optional'], False),
                                               ('P2', required[:1], True), ('P1', [], True), ('P0', [], True)):
            for status in ('OPEN', 'BLOCKED', 'NOT_REPRODUCED', 'CLOSED'):
                finding = dict(id='F-original', severity=severity, status=status, title='保留原始意见',
                               contract_ids=contracts, evidence_refs=['source-inspection'])
                report = self.review_report(run, data, [finding])
                review = dict(report=report, process=process, session_id='reviewer-fixture')
                blocked = mandatory and status != 'CLOSED'
                with self.subTest(severity=severity, contracts=contracts, status=status):
                    args = (run, data['round'], data['candidate']['sha256'], data['acceptance_sha256'],
                            required, verification, implementation, review)
                    if blocked:
                        with self.assertRaisesRegex(Blocked, 'open required finding'):
                            gate(*args, expected_verification=data['config']['policy']['verification'])
                    else:
                        self.assertTrue(gate(*args, expected_verification=data['config']['policy']['verification']))
                    store.transition(run, 'GATING', review=review)
                    for snapshot in (self.runtime.snapshot(run), self.http_snapshot(run)):
                        node = next(n for n in snapshot['workflow_graph']['nodes'] if n['type'] == 'reviewer')
                        self.assertEqual(node['status'], 'blocked' if blocked else 'passed')
                        self.assertEqual(node['open_findings'], int(status != 'CLOSED'))
                        self.assertEqual(node['findings'], [{k: finding[k] for k in ('id', 'status', 'severity', 'title')}])
                        self.assertEqual(snapshot['findings'], node['findings'])
        findings = [dict(id='suggestion', severity='P3', status='OPEN', title='可选建议', contract_ids=[], evidence_refs=[]),
                    dict(id='required', severity='P2', status='OPEN', title='必需修复', contract_ids=required[:1], evidence_refs=['source-inspection'])]
        store.transition(run, 'GATING', review={'report': self.review_report(run, data, findings)})
        node = next(n for n in self.http_snapshot(run)['workflow_graph']['nodes'] if n['type'] == 'reviewer')
        self.assertEqual(node['status'], 'blocked');self.assertEqual(node['open_findings'], 2)
        self.assertEqual([f['id'] for f in node['findings']], ['suggestion', 'required'])

    def test_review_verdict_and_four_bindings_remain_required(self):
        store, run, data = self.record(state='GATING')
        for verdict, status in (('ACCEPT', 'passed'), ('ACCEPT_WITH_LIMITATIONS', 'blocked'),
                                ('NEEDS_CORRECTION', 'failed'), ('BLOCKED', 'blocked')):
            report = self.review_report(run, data, [], verdict)
            store.transition(run, 'GATING', review={'report': report})
            node = next(n for n in self.http_snapshot(run)['workflow_graph']['nodes'] if n['type'] == 'reviewer')
            self.assertEqual(node['status'], status)
            self.assertEqual(node['verdict'], verdict)
        for field in ('run_id', 'round', 'candidate_sha256', 'acceptance_sha256'):
            report = self.review_report(run, data, [])
            report[field] = 1 if field == 'round' else 'wrong'
            store.transition(run, 'GATING', review={'report': report})
            node = next(n for n in self.http_snapshot(run)['workflow_graph']['nodes'] if n['type'] == 'reviewer')
            self.assertNotEqual(node['status'], 'passed');self.assertNotIn('verdict', node)

    def test_retained_evidence_requires_exact_present_round_on_all_paths(self):
        missing = object()
        for path in ('validated_operation', 'final_verification_report', 'review_report'):
            store, run, data = self.record(state='GATING')
            for label, number in (('old', 1), ('future', 3), ('missing', missing),
                                  ('null', None), ('wrong-type', '2'), ('current', 2)):
                report = (self.review_report(run, data, []) if path == 'review_report'
                          else self.final_report(run, data))
                if number is missing:
                    del report['round']
                else:
                    report['round'] = number
                if path == 'validated_operation':
                    info = {k: v for k, v in report.items() if k not in ('id', 'process')}
                    info['verification_id'] = report['id']
                    operation = store.intent(run, 'VERIFICATION', info)
                    store.finish(operation, 'VALIDATED')
                elif path == 'final_verification_report':
                    store.transition(run, 'GATING', verification=[report])
                else:
                    store.transition(run, 'GATING', review={'report': report})
                for read in (self.runtime.snapshot, self.http_snapshot):
                    with self.subTest(path=path, round=label, reader=read.__name__):
                        snapshot = read(run)
                        kind = 'reviewer' if path == 'review_report' else 'verifier'
                        node = next(n for n in snapshot['workflow_graph']['nodes'] if n['type'] == kind)
                        self.assertEqual(node['status'], 'passed' if label == 'current' else 'pending')
                        if label != 'current':
                            if kind == 'reviewer':
                                self.assertIsNone(snapshot['verdict']);self.assertNotIn('verdict', node)
                            else:
                                self.assertIsNone(node['counts'])

    def test_browser_canvas_fixtures_keep_complete_reports_and_negative_states(self):
        from usable_browser import canvas_runs
        runs = canvas_runs(self.runtime, self)
        store = Store(self.runtime.control, readonly=True);self.addCleanup(store.db.close)
        for case, run in runs.items():
            with self.subTest(case=case):
                data = store.get(run)['data']
                validate(data['review']['report'], schema('review-result'))
                snapshot = self.http_snapshot(run)
                nodes = {n['id']: n for n in snapshot['workflow_graph']['nodes']}
                self.assertEqual(nodes['separate-check']['status'],
                                 'failed' if case == 'failed' else 'pending' if case == 'stale' else 'passed')
                self.assertEqual(nodes['custom-reviewer']['status'],
                                 'failed' if case == 'failed' else 'pending' if case == 'stale' else 'passed')
                if case == 'failed':
                    self.assertEqual(nodes['custom-reviewer']['open_findings'], 1)
                    self.assertEqual(nodes['separate-check']['counts']['failures'], 1)
                if case == 'dead':
                    self.assertEqual(snapshot['state'], 'RECOVERY_REQUIRED')
                    self.assertFalse(any(n['status'] == 'running' for n in nodes.values()))
                if case == 'delivered':
                    self.assertEqual(nodes['custom-delivery']['delivery']['pr']['number'], 42)

    def test_capture_full_snapshot_compiled_identity_and_contract_ids(self):
        preview = self.prepare();config = preview['data']['config'];value = config['studio_workflow']
        self.assertEqual(value['document'], custom_document())
        self.assertEqual(value['sha256'], compile_plan(custom_document())['sha256'])
        self.assertEqual(value['verification_ids'], {'custom-verifier': ['custom-verifier'], 'separate-check': ['separate-check']})
        config_check(config)
        # The execution policy, rather than the display document, owns capabilities.
        self.assertFalse(config['policy']['delivery']['commit']);self.assertFalse(config['policy']['delivery']['merge'])
        self.assertFalse(self.runtime.control.exists())

    def test_tamper_hash_closed_fields_and_complete_graph(self):
        original = self.prepare()['data']['config']
        for change in ('hash', 'document', 'extra', 'graph'):
            config = copy.deepcopy(original);value = config['studio_workflow']
            if change == 'hash':value['sha256'] = '0' * 64
            elif change == 'document':value['document']['nodes'][0]['label'] = '篡改'
            elif change == 'extra':value['execute'] = True
            else:
                value['document']['edges'].pop()
                from studio.graph import digest
                value['sha256'] = digest(value['document'])
            with self.subTest(change=change), self.assertRaises(Blocked):config_check(config)

    def test_mapping_tamper_coverage_ownership_uniqueness_and_policy(self):
        original = self.prepare()['data']['config']
        for mapping in ({}, {'custom-verifier': ['separate-check'], 'separate-check': ['custom-verifier']},
                        {'custom-verifier': ['custom-verifier'], 'separate-check': ['custom-verifier']},
                        {'custom-verifier': [], 'separate-check': ['separate-check']},
                        {'custom-verifier': ['custom-verifier'], 'separate-check': ['missing']}):
            config = copy.deepcopy(original);config['studio_workflow']['verification_ids'] = mapping
            with self.subTest(mapping=mapping), self.assertRaises(Blocked):config_check(config)
        config = copy.deepcopy(original);config['policy']['verification'].reverse()
        with self.assertRaises(Blocked):config_check(config)

    def test_current_two_verifiers_aggregate_only_their_own_contracts(self):
        store, run, data = self.record();self.reports(store, run, data)
        graph = self.graph(run);nodes = {n['id']: n for n in graph['nodes']}
        self.assertEqual([n['id'] for n in graph['nodes']], compile_plan(custom_document())['order'])
        self.assertEqual(graph['edges'], custom_document()['edges'])
        self.assertEqual(nodes['custom-verifier']['counts']['tests'], 1)
        self.assertEqual(nodes['separate-check']['counts']['tests'], 2)
        self.assertEqual(nodes['separate-check']['status'], 'passed')
        self.assertEqual(graph['round'], 2)

    def test_failed_second_verifier_does_not_inherit_first_pass(self):
        store, run, data = self.record();self.reports(store, run, data, failed=True)
        nodes = {n['id']: n for n in self.graph(run)['nodes']}
        self.assertEqual(nodes['custom-verifier']['status'], 'passed')
        self.assertEqual(nodes['separate-check']['status'], 'failed')
        self.assertEqual(nodes['separate-check']['counts']['failures'], 1)

    def test_stale_round_run_candidate_and_contract_never_pass(self):
        store, run, data = self.record();self.reports(store, run, data, number=1)
        for alteration in ('round', 'run_id', 'candidate_sha256', 'acceptance_sha256'):
            report = self.final_report(run, data)
            report[alteration] = 1 if alteration == 'round' else 'wrong'
            store.transition(run, 'VERIFYING', verification=[report])
            for n in self.graph(run)['nodes']:
                if n['type'] == 'verifier':
                    self.assertEqual(n['status'], 'pending');self.assertIsNone(n['counts'])

    def test_redacted_projection_omits_task_context_credentials_and_config(self):
        store, run, data = self.record()
        config = data['config'];config['goal'] = 'SECRET task body'
        for n in config['studio_workflow']['document']['nodes']:
            if n['type'] in ('planner', 'developer', 'reviewer'):
                n['config']['background'] = 'SECRET background';n['config']['responsibility'] = 'SECRET responsibility'
        config['studio_workflow']['sha256'] = compile_plan(config['studio_workflow']['document'])['sha256']
        store.transition(run, 'VERIFYING', config=config)
        graph = self.graph(run);raw = json.dumps(graph)
        for forbidden in ('SECRET', 'background', 'responsibility', 'readonly_files', 'task body', 'config'):
            self.assertNotIn(forbidden, raw)
        self.assertEqual(graph['sha256'], config['studio_workflow']['sha256'])

    def test_legacy_record_keeps_original_graph_without_workflow_field(self):
        store, run, data = self.record();del data['config']['studio_workflow']
        config_check(data['config']);store.transition(run, 'VERIFYING', config=data['config'])
        snapshot = self.runtime.snapshot(run)
        self.assertNotIn('workflow_graph', snapshot);self.assertIn('graph', snapshot)

    def test_current_stage_liveness_native_session_and_prior_agent_isolation(self):
        store, run, data = self.record(state='IMPLEMENTING')
        proc = process_identity(os.getpid())
        worker = store.intent(run, 'WORKER', {});store.finish(worker, 'RUNNING', process=proc)
        request = store.intent(run, 'AGENT_REQUEST', dict(role='implementer', requested_session='11111111-1111-1111-1111-111111111111'))
        operation = store.intent(run, 'PROCESS', dict(context={'agent_role': 'implementer', 'provider': 'codex'}))
        store.finish(operation, 'RUNNING', process=proc)
        n = next(n for n in self.graph(run)['nodes'] if n['type'] == 'developer')
        self.assertEqual(n['status'], 'running');self.assertTrue(n['agent']['alive'])
        self.assertEqual(n['agent']['session_id'], '11111111-1111-1111-1111-111111111111')
        store.finish(operation, 'EXITED')
        self.assertEqual(next(n for n in self.graph(run)['nodes'] if n['type'] == 'developer')['status'], 'blocked')
        store.transition(run, 'IMPLEMENTING', round=3)
        n = next(n for n in self.graph(run)['nodes'] if n['type'] == 'developer')
        self.assertEqual(n['status'], 'blocked');self.assertFalse(n['agent']['alive'])
        store.finish(worker, 'EXITED', process=None)
        snapshot = self.runtime.snapshot(run)
        self.assertEqual(snapshot['state'], 'RECOVERY_REQUIRED')
        self.assertFalse(any(n['status'] == 'running' for n in snapshot['workflow_graph']['nodes']))

    def test_http_workflow_identity_and_empty_answer_server_gate(self):
        store, run, data = self.record();self.reports(store, run, data, failed=True)
        capability = 'only-for-test'
        server = ThreadingHTTPServer(('127.0.0.1', 0), handler(self.runtime, capability))
        thread = threading.Thread(target=server.serve_forever, daemon=True);thread.start()
        self.addCleanup(thread.join);self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
        url = 'http://127.0.0.1:' + str(server.server_port)
        request = Request(url + '/api/run?id=' + run, headers={'Authorization': 'Bearer ' + capability})
        with urlopen(request) as response:value = json.load(response)
        self.assertEqual(value['workflow_graph']['nodes'][0]['id'], 'custom-human-1')
        permit = self.prepare()
        request = Request(url + '/api/authorize-run', data=json.dumps(dict(permit=permit['id'], sha256=permit['sha256'], answers=[''])).encode(),
                          headers={'Authorization': 'Bearer ' + capability, 'Content-Type': 'application/json'})
        with self.assertRaises(HTTPError) as caught:urlopen(request)
        self.assertEqual(caught.exception.code, 400)
        with self.runtime.db.db() as db:self.assertEqual(db.execute('SELECT used FROM permits WHERE id=?', (permit['id'],)).fetchone()[0], 0)

    def test_multiple_contracts_per_verifier_keep_exact_profile_mapping(self):
        from orchestration.common import save, digest
        operator = copy.deepcopy(self.runtime.operator)
        second = copy.deepcopy(operator['verification_profiles']['default'][0]);second['id'] = 'second'
        operator['verification_profiles']['default'].append(second)
        save(self.operator_file, operator)
        self.runtime = self.runtime.__class__(self.operator_file, digest(self.operator_file.read_bytes()))
        store, run, data = self.record()
        mapping = data['config']['studio_workflow']['verification_ids']
        self.assertEqual(mapping['custom-verifier'], ['custom-verifier-value', 'custom-verifier-second'])
        for identity in mapping['custom-verifier']:
            op = store.intent(run, 'VERIFICATION', dict(run_id=run, round=2, verification_id=identity,
                candidate_sha256='a' * 64, acceptance_sha256='b' * 64))
            store.finish(op, 'VALIDATED', passed=True, counts=dict(tests=1, failures=0, errors=0, skipped=0))
        nodes = {n['id']: n for n in self.graph(run)['nodes']}
        self.assertEqual(nodes['custom-verifier']['counts']['tests'], 2)
        self.assertEqual(nodes['custom-verifier']['status'], 'passed')
        self.assertIsNone(nodes['separate-check']['counts']);self.assertEqual(nodes['separate-check']['status'], 'pending')

    def test_planner_reviewer_require_own_phase_process_and_current_candidate(self):
        for role, kind, stage, number in (('planner', 'planner', 'PLANNING', 0), ('reviewer', 'reviewer', 'REVIEWING', 2)):
            store, run, data = self.record(state=stage, number=number)
            worker = store.intent(run, 'WORKER', {});store.finish(worker, 'RUNNING', process=process_identity(os.getpid()))
            store.intent(run, 'AGENT_REQUEST', dict(role=role, requested_session='11111111-1111-1111-1111-111111111111'))
            process = store.intent(run, 'PROCESS', dict(context=dict(agent_role=role, provider='claude' if role == 'reviewer' else 'codex')))
            store.finish(process, 'RUNNING', process=process_identity(os.getpid()))
            n = next(n for n in self.graph(run)['nodes'] if n['type'] == kind)
            self.assertEqual(n['status'], 'running')
            store.finish(process, 'EXITED');self.assertEqual(next(n for n in self.graph(run)['nodes'] if n['type'] == kind)['status'], 'blocked')
            if role == 'reviewer':
                report = dict(run_id=run, round=number, candidate_sha256='wrong', acceptance_sha256='b' * 64, verdict='ACCEPT', findings=[])
                store.transition(run, 'GATING', review={'report': report})
                snapshot = self.runtime.snapshot(run)
                self.assertIsNone(snapshot['verdict'])
                self.assertNotEqual(next(n for n in snapshot['workflow_graph']['nodes'] if n['type'] == 'reviewer')['status'], 'passed')
                self.assertNotEqual(next(n for n in snapshot['graph']['nodes'] if n['type'] == 'reviewer')['status'], 'passed')
                report['candidate_sha256'] = 'a' * 64
                store.transition(run, 'GATING', review={'report': report})
                self.assertEqual(next(n for n in self.graph(run)['nodes'] if n['type'] == 'reviewer')['status'], 'passed')

    def test_human_result_gate_is_bound_to_exact_candidate_and_round(self):
        request = self.request();request['workflow'] = template('C')
        config = self.runtime.prepare(request)['data']['config']
        store = Store(self.runtime.control);self.addCleanup(store.db.close)
        data = dict(config=config, source={'root': str(self.source)}, round=2, sessions={},
                    candidate={'sha256': 'a' * 64}, candidate_round=2, acceptance_sha256='b' * 64)
        run = store.create(data);store.transition(run, 'AWAITING_HUMAN')
        final = lambda: next(n for n in self.graph(run)['nodes'] if n['id'] == 'human-4')
        self.assertEqual(final()['status'], 'blocked')
        receipt = dict(actor='user', gate='G4', round=1, candidate_sha256='a' * 64, acceptance_sha256='b' * 64, answer='实际结果解释', approval_ref='studio-g4:test-fixture')
        store.transition(run, 'AWAITING_HUMAN', human_result=receipt)
        self.assertEqual(final()['status'], 'blocked')
        receipt['round'] = 2;store.transition(run, 'READY', human_result=receipt)
        self.assertEqual(final()['status'], 'passed')
