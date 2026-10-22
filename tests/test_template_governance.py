"""Node-driven approvals, immutable legacy runs, and optional template provenance.

Native models are not used. Runtime fixtures mock release approval; the final
Controller test uses synthetic CLIs with real processes and deterministic gates.
"""
import copy
import json
from pathlib import Path
from http.server import ThreadingHTTPServer
import threading
import unittest
from unittest.mock import patch
from urllib.request import Request, urlopen
from urllib.error import HTTPError

import test_usable
import test_orchestration
from orchestration import controller
from orchestration.common import Blocked, canonical, controller_hash, digest, identity, save, tree_hash, manifest
from orchestration.contracts import config_check, authorized
from orchestration.store import Store
from orchestration.trust import TrustedRelease
from studio.graph import Invalid, digest as graph_digest
from studio.usable_graph import compile_plan, governance, node, template, upgrade_draft
from studio.usable_server import handler


def sequence(doc, ids):
    doc['edges'] = [dict(source=a, target=b, on='next') for a, b in zip(ids, ids[1:])]
    doc['edges'].append(dict(source='reviewer', target='developer', on='repair'))
    return doc


def custom_graph(origin='A'):
    doc = template('A'); doc['template'] = origin
    doc['nodes'] += [node('human_gate', key) for key in ('scope-confirm', 'result-one', 'result-two')]
    return sequence(doc, ['human-1', 'scope-confirm', 'developer', 'verifier', 'reviewer',
                          'result-one', 'result-two', 'delivery'])


class TemplateGraphTests(unittest.TestCase):
    def test_v2_template_label_never_changes_execution_or_approvals(self):
        first = None
        for origin in ('A', 'B', 'C', 'blank'):
            plan = compile_plan(custom_graph(origin))
            semantics = (plan['order'], plan['initial_gates'], plan['result_gates'], governance(plan))
            if first is None: first = semantics
            self.assertEqual(semantics, first)
            self.assertEqual(governance(plan)['mode'], 'B')  # legacy serialization, not a UI mode

    def test_C_is_editable_without_fixed_G1_G4_counts(self):
        doc = template('A'); doc['template'] = 'C'
        plan = compile_plan(doc)
        self.assertEqual(plan['initial_gates'], ['human-1'])
        self.assertEqual(plan['result_gates'], [])
        self.assertIsNone(governance(plan)['result_policy'])

    def test_blank_workflow_can_use_custom_result_nodes(self):
        doc = custom_graph('blank')
        plan = compile_plan(doc)
        self.assertEqual(plan['result_gates'], ['result-one', 'result-two'])
        self.assertEqual([g['id'] for g in governance(plan)['result_policy']['gates']], plan['result_gates'])

    def test_safety_nodes_remain_required_for_every_label(self):
        for label in ('A', 'B', 'C', 'blank'):
            for kind in ('human_gate', 'verifier', 'reviewer'):
                with self.subTest(label=label, kind=kind):
                    doc = template('A');doc['template'] = label
                    doc['nodes'] = [n for n in doc['nodes'] if n['type'] != kind]
                    ids = [n['id'] for n in doc['nodes']]
                    doc['edges'] = [dict(source=a, target=b, on='next') for a,b in zip(ids, ids[1:])]
                    if kind != 'reviewer': doc['edges'].append(dict(source='reviewer', target='developer', on='repair'))
                    with self.assertRaises(Invalid): compile_plan(doc)

    def test_questions_cannot_be_empty_in_executable_graph(self):
        for key in ('human-1', 'scope-confirm', 'result-one'):
            doc = custom_graph();next(n for n in doc['nodes'] if n['id'] == key)['config']['question'] = '  '
            with self.assertRaises(Invalid): compile_plan(doc)

    def test_gate_in_unsupported_phase_is_not_silently_hoisted(self):
        doc = custom_graph()
        sequence(doc, ['human-1', 'developer', 'scope-confirm', 'verifier', 'reviewer', 'result-one', 'result-two', 'delivery'])
        with self.assertRaises(Invalid): compile_plan(doc)

    def test_legacy_compile_preserves_contract_and_hash(self):
        for origin in ('A', 'B', 'C'):
            old = template(origin);old['version'] = 1
            before = copy.deepcopy(old);sha = graph_digest(old)
            plan = compile_plan(old)
            self.assertEqual(plan['sha256'], sha);self.assertEqual(old, before)
            self.assertEqual(governance(plan)['mode'], origin)
            if origin == 'C': self.assertEqual(governance(plan)['result_policy']['mode'], 'deferred-G4')
        invalid = template('A');invalid.update(version=1, template='C')
        with self.assertRaises(Invalid): compile_plan(invalid)

    def test_upgrade_is_copy_only_and_requires_new_hash(self):
        old = template('C');old['version'] = 1;before = copy.deepcopy(old)
        new = upgrade_draft(old)
        self.assertEqual(old, before);self.assertEqual(new['version'], 2)
        self.assertNotEqual(graph_digest(new), graph_digest(old))
        self.assertEqual(new['nodes'], old['nodes'])
        self.assertEqual(governance(compile_plan(new))['mode'], 'B')

    def test_partial_draft_and_strict_version(self):
        self.assertEqual(upgrade_draft(template('blank'))['nodes'], [])
        with self.assertRaises(Invalid): compile_plan(template('blank'))
        for value in (True, 1.0, 2.0, 3, None):
            doc = template('A');doc['version'] = value
            with self.assertRaises(Invalid): compile_plan(doc)


class NodePolicyTests(unittest.TestCase):
    setUp = test_usable.RuntimeTests.setUp
    request = test_usable.RuntimeTests.request

    def preview(self, origin='A'):
        request = self.request();request['workflow'] = custom_graph(origin)
        return self.runtime.prepare(request)

    def test_prepare_uses_nodes_not_template_for_all_labels(self):
        for origin in ('A', 'B', 'C', 'blank'):
            value = self.preview(origin)['data']
            self.assertEqual(len(value['human_questions']), 2)
            config = value['config'];self.assertEqual(config['policy']['mode'], 'B')
            self.assertEqual([g['id'] for g in config['human_gate_policy']['gates']], ['result-one','result-two'])
            config_check(config)

    def test_result_contract_cannot_be_removed_reordered_or_reworded(self):
        config = self.preview()['data']['config']
        for mutate in (lambda c: c.pop('human_gate_policy'),
                       lambda c: c['human_gate_policy']['gates'].reverse(),
                       lambda c: c['human_gate_policy']['gates'][0].update(question='different question'),
                       lambda c: c['human_gate_policy']['gates'].pop()):
            c = copy.deepcopy(config);mutate(c)
            with self.assertRaises(Blocked): config_check(c)

    def test_template_metadata_does_not_create_new_engine_mode(self):
        config = self.preview()['data']['config']
        for mode in ('A', 'C'):
            c = copy.deepcopy(config);c['policy']['mode'] = mode
            with self.assertRaises(Blocked): config_check(c)

    def test_result_gates_cannot_be_added_outside_graph(self):
        config = self.runtime.prepare(self.request())['data']['config']
        config['human_gate_policy'] = {'mode':'node-results','gates':[{'id':'hidden', 'question':'hidden'}]}
        with self.assertRaises(Blocked): config_check(config)

    def test_legacy_new_launch_requires_explicit_edit_migration(self):
        request = self.request();request['workflow']['version'] = 1
        with self.assertRaisesRegex(Invalid, 'Reload'): self.runtime.prepare(request)
        request['workflow'] = upgrade_draft(request['workflow'])
        self.assertTrue(self.runtime.prepare(request)['id'])

    def test_legacy_runtime_validation_still_works(self):
        request = self.request();request['workflow'] = template('C')
        config = self.runtime.prepare(request)['data']['config']
        doc = config['studio_workflow']['document'];doc['version'] = 1
        config['studio_workflow']['sha256'] = graph_digest(doc)
        config['policy']['mode'] = 'C'
        config['human_gate_policy'] = governance(compile_plan(doc))['result_policy']
        config_check(config)

    def authorization(self, config):
        acceptance=self.root/'node-acceptance.md';acceptance.write_text('fixture-only')
        config['acceptance']=str(acceptance);source=identity(self.source)
        return dict(config_sha256=digest(canonical(config)),controller_sha256=controller_hash(),
                    acceptance_sha256=digest(acceptance.read_bytes()), source=source['root'],head=source['head'],
                    branch=source['branch'], approval_ref='UNIT TEST ONLY',external_source_approved=True,
                    commit=False,push=False,human_events=[dict(gate='node:'+key, actor='user',evidence_ref='unit:'+key)
                        for key in ('human-1','scope-confirm')])

    def test_every_initial_node_must_have_matching_user_evidence(self):
        config=self.preview()['data']['config'];auth=self.authorization(config)
        path=self.root/'node-authorization.json';save(path,auth)
        self.assertEqual(authorized(config,path)[1]['root'],str(self.source))
        cases=[[],auth['human_events'][:1],list(reversed(auth['human_events'])),
               [dict(gate='G1',actor='user',evidence_ref='old-mode'),dict(gate='G2',actor='user',evidence_ref='old-mode')],
               [dict(e,actor='agent') for e in auth['human_events']]]
        for events in cases:
            save(path,dict(auth,human_events=events))
            with self.assertRaises(Blocked): authorized(config,path)

    def test_template_relabel_still_invalidates_old_authorization_hash(self):
        config=self.preview()['data']['config'];auth=self.authorization(config)
        path=self.root/'node-authorization.json';save(path,auth)
        doc=config['studio_workflow']['document'];doc['template']='blank'
        config['studio_workflow']['sha256']=graph_digest(doc)
        config_check(config)  # same permissions, but a different immutable snapshot
        with self.assertRaisesRegex(Blocked,'authorization binding'): authorized(config,path)

    def test_http_default_blank_and_explicit_migration(self):
        old=template('C');old['version']=1
        saved=self.runtime.db.save_draft(old)
        server=ThreadingHTTPServer(('127.0.0.1',0),handler(self.runtime,'fixture-token'))
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        base=f'http://127.0.0.1:{server.server_port}'
        try:
            def request(path,data=None,token=True):
                headers={'Authorization':'Bearer fixture-token'} if token else {}
                if data is not None:headers['Content-Type']='application/json'
                with urlopen(Request(base+path,None if data is None else json.dumps(data).encode(),headers)) as r:return json.load(r)
            self.assertEqual(request('/api/template')['nodes'],[])
            new=request('/api/migrate-workflow',{'document':old})
            self.assertEqual(new['version'],2)
            self.assertEqual(self.runtime.db.get('draft',saved['id'])['document'],old)
            with self.assertRaises(HTTPError) as denied:request('/api/migrate-workflow',{'document':old},False)
            self.assertEqual(denied.exception.code,403)
        finally:server.shutdown();server.server_close();thread.join()

    def awaiting(self):
        config=self.preview()['data']['config']
        candidate=self.root/'candidate';candidate.mkdir(exist_ok=True);(candidate/'value').write_text('fixed')
        store=Store(self.runtime.control);self.addCleanup(store.db.close)
        data=dict(config=config,source=identity(self.source),stable={'fixture':True},round=1,
                  candidate={'sha256':tree_hash(candidate)},candidate_path=str(candidate),verification=[],
                  implementation={},review={},history=[],acceptance_sha256='b'*64)
        run=store.create(data);store.transition(run,'AWAITING_HUMAN')
        answers=[dict(id=key,answer='Actual unit fixture response') for key in ('result-one','result-two')]
        expected=dict(candidate_sha256=data['candidate']['sha256'],acceptance_sha256='b'*64,round=1)
        return store,run,data,answers,expected

    def test_result_nodes_require_each_answer_and_exact_visible_snapshot(self):
        store,run,data,answers,expected=self.awaiting()
        invalid=[(answers[:1],expected),(list(reversed(answers)),expected),
                 ([dict(answers[0],answer=''),answers[1]],expected),
                 (answers,dict(expected,round=True)),(answers,dict(expected,round=2)),
                 (answers,dict(expected,candidate_sha256='c'*64)),(answers,None)]
        with patch.object(controller,'binding_check',return_value=data['config']),patch.object(controller,'gate') as gate:
            for response,binding in invalid:
                with self.assertRaises(Blocked):controller.approve_human_gate(store,run,response,'studio-result:fixture',expected=binding)
                self.assertEqual(store.get(run)['state'],'AWAITING_HUMAN')
            self.assertEqual(gate.call_count,0)
            result=controller.approve_human_gate(store,run,answers,'studio-result:fixture',expected=expected)
            self.assertEqual(result['state'],'READY');self.assertTrue(controller.human_result_bound(result['data']))
            self.assertEqual(result['data']['human_result']['answers'],answers)

    def test_result_receipt_is_not_reusable_for_another_graph_round_or_gate(self):
        store,run,data,answers,expected=self.awaiting()
        with patch.object(controller,'binding_check',return_value=data['config']),patch.object(controller,'gate'):
            data=controller.approve_human_gate(store,run,answers,'studio-result:fixture',expected=expected)['data']
        for field,value in [('round',True),('round',1.0),('round',2),('candidate_sha256','c'*64),('workflow_sha256','d'*64)]:
            changed=copy.deepcopy(data);changed['human_result'][field]=value
            self.assertFalse(controller.human_result_bound(changed),field)
        changed=copy.deepcopy(data);changed['human_result']['answers'][0]['id']='another-node'
        self.assertFalse(controller.human_result_bound(changed))


class ControllerNodeGateTests(test_orchestration.Fixture):
    def test_real_controller_synthetic_agents_stop_and_confirm_node_results(self):
        doc=template('A');doc['template']='blank';doc['max_rounds']=self.config['policy']['limits']['max_review_rounds']
        next(n for n in doc['nodes'] if n['type']=='verifier')['id']='unit'
        for e in doc['edges']:
            for k in ('source','target'):
                if e[k]=='verifier':e[k]='unit'
        doc['nodes'] += [node('human_gate','final-one'),node('human_gate','final-two')]
        sequence(doc,['human-1','developer','unit','reviewer','final-one','final-two','delivery'])
        self.config['studio_workflow']=dict(document=doc,sha256=graph_digest(doc),verification_ids={'unit':['unit']})
        self.config['human_gate_policy']=governance(compile_plan(doc))['result_policy']
        self.authorize();self.auth['human_events']=[dict(gate='node:human-1',actor='user',evidence_ref='UNIT FIXTURE')];save(self.auth_path,self.auth)
        root=Path(controller.__file__).resolve().parents[2];entries=manifest(root);record=self.base/'fixture-approval.json'
        save(record,dict(version=1,root=str(root),git_commit='a'*40,git_tree='b'*40,candidate_sha256=digest(canonical(entries)),
                         files=entries,review_verdict='ACCEPT',review_receipt_sha256='c'*64,approval_ref='UNIT FIXTURE ONLY; not a release'))
        trust=TrustedRelease(record,digest(record.read_bytes()))
        result=controller.start(self.control,self.config_path,self.auth_path,trust=trust)
        self.assertEqual(result['state'],'AWAITING_HUMAN',result['data'].get('reason'))
        store=Store(self.control);self.addCleanup(store.db.close);run=result['id'];data=result['data']
        self.assertEqual(controller.resume(store,run)['state'],'AWAITING_HUMAN')
        with self.assertRaises(Blocked):controller.deliver_run(store,run)
        answers=[dict(id=k,answer='Fixture confirms this actual reviewed candidate') for k in ('final-one','final-two')]
        expected=dict(candidate_sha256=data['candidate']['sha256'],acceptance_sha256=data['acceptance_sha256'],round=data['round'])
        approved=controller.approve_human_gate(store,run,answers,'studio-result:fixture',expected=expected)
        self.assertEqual(approved['state'],'READY');self.assertTrue(controller.human_result_bound(approved['data']))
        self.assertEqual((self.source/'value.py').read_text(),'VALUE = 0\n')
