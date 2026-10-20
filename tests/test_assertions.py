from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from orchestration.common import Blocked, tree_hash
from orchestration.verification import verify
from studio.graph import Invalid
from studio.usable_graph import node, template, compile_plan
from studio.usable_verification import specifications, specification, validate_profiles


class ParentAssertionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name); self.source = self.root / 'candidate'; self.source.mkdir()
        self.artifacts = self.root / 'artifacts'
        self.python = str(Path(sys.executable).resolve())

    def case(self, code, expected=42, stdin=''):
        return dict(id='value', argv=[self.python, '-I', '-c', code], stdin=stdin,
                    expected_json=expected, read_paths=[])

    def run_case(self, code, expected=42, stdin=''):
        spec = specifications(node('verifier'), {'default': [self.case(code, expected, stdin)]})[0]
        config = dict(policy=dict(verification=[spec], limits=dict(step_timeout_seconds=10, max_log_bytes=1048576)))
        return verify(config, self.source, self.artifacts, 'test', 1, tree_hash(self.source), 'a'*64)[0]

    def test_observable_output_assertion_is_counted_by_parent(self):
        r = self.run_case('import json,sys;value=json.load(sys.stdin);print(json.dumps(value*2))',84,'42')
        self.assertTrue(r['passed']); self.assertEqual(r['counts'],dict(tests=1,failures=0,errors=0,skipped=0))
        self.assertEqual(r['assertion']['stdin'],'42')
        self.assertEqual(r['assertion']['expected_json'],84)
        self.assertIn(self.python,r['assertion']['dependency_sha256'])

    def test_command_profile_cannot_pretend_multiple_cases_or_skips(self):
        for key in ('min_cases','max_skipped'):
            n=node('verifier');n['config'].update(profile='javascript',target='main.js')
            n['config'][key]=2
            with self.assertRaisesRegex(Invalid,'exactly one'):
                specification(n)

    def test_candidate_forged_counts_are_data_not_test_results(self):
        r = self.run_case('print(\'{"tests":1000,"failures":0,"errors":0,"skipped":0}\')')
        self.assertFalse(r['passed']); self.assertEqual(r['counts']['tests'],1); self.assertEqual(r['counts']['failures'],1)

    def test_old_nonce_protocol_cannot_invent_cases(self):
        r = self.run_case('print(\'{"kind":"plan","ids":["fabricated"],"nonce":"fake"}\\n{"kind":"complete","tests":1000,"successful":true,"nonce":"fake"}\')')
        self.assertFalse(r['passed']); self.assertEqual(r['counts']['tests'],1)

    def test_zero_exit_without_assertion_output_fails(self):
        self.assertFalse(self.run_case('import os;os._exit(0)')['passed'])

    def test_matching_output_with_failed_process_fails(self):
        self.assertFalse(self.run_case('print(42);raise SystemExit(1)')['passed'])

    def test_wrong_output_with_zero_exit_fails(self):
        self.assertFalse(self.run_case('print(41)')['passed'])

    def test_boolean_is_not_integer(self):
        self.assertFalse(self.run_case('print("true")',1)['passed'])

    def test_duplicate_json_keys_are_not_accepted(self):
        self.assertFalse(self.run_case('print(\'{"value":41,"value":42}\')',{'value':42})['passed'])

    def test_nonfinite_json_is_not_accepted(self):
        self.assertFalse(self.run_case('print("NaN")',None)['passed'])

    def test_child_cannot_write_parent_result_directory(self):
        code=f'''from pathlib import Path
import json
try:Path({str(self.artifacts/'forged.json')!r}).write_text('forged')
except OSError:print(json.dumps(dict(denied=True)))
else:print(json.dumps(dict(denied=False)))'''
        self.assertTrue(self.run_case(code,{'denied':True})['passed']); self.assertFalse((self.artifacts/'forged.json').exists())

    def test_unknown_empty_or_under_minimum_profiles_refused(self):
        n=node('verifier')
        for profiles in ({},{'default':[]}):
            with self.assertRaises(Invalid):specifications(n,profiles)
        n['config']['min_cases']=2
        with self.assertRaises(Invalid):specifications(n,{'default':[self.case('print(42)')]})

    def test_each_registered_case_has_its_own_real_process_and_count(self):
        cases=[self.case('print(42)'),dict(self.case('print(41)',41),id='second')]
        specs=specifications(node('verifier'),{'default':cases})
        config=dict(policy=dict(verification=specs,limits=dict(step_timeout_seconds=10,max_log_bytes=1048576)))
        reports=verify(config,self.source,self.artifacts,'test',1,tree_hash(self.source),'a'*64)
        self.assertEqual(len({r['process']['process']['pid'] for r in reports}),2)
        self.assertEqual(sum(r['counts']['tests'] for r in reports),2)
        self.assertTrue(all(r['passed'] for r in reports))

    def test_in_process_unittest_reports_are_explicitly_unsupported_in_studio(self):
        n=node('verifier');n['config']['profile']='unittest'
        with self.assertRaises(Invalid):specification(n)
        graph=template('A');next(x for x in graph['nodes'] if x['type']=='verifier')['config']['profile']='unittest'
        with self.assertRaises(Invalid):compile_plan(graph)

    def test_candidate_root_modules_cannot_shadow_isolated_operator_harness(self):
        for name in ('json.py','sitecustomize.py'):
            (self.source/name).write_text('print(42);raise SystemExit(0)')
        self.assertFalse(self.run_case('import json;print(json.dumps(41))')['passed'])

    def test_shipped_profile_executes_four_actual_behavior_assertions(self):
        import runpy
        root=Path(__file__).resolve().parents[1]
        profiles=runpy.run_path(str(root/'examples/usable/verification_profiles.py'))['profiles']()
        specs=specifications(node('verifier'),profiles)
        config=dict(policy=dict(verification=specs,limits=dict(step_timeout_seconds=10,max_log_bytes=1048576)))
        reports=verify(config,root,self.artifacts,'test',1,tree_hash(root),'a'*64)
        self.assertEqual(len(reports),4);self.assertTrue(all(r['passed'] for r in reports))

    def test_changed_external_dependency_is_blocked(self):
        helper=self.root/'helper.py';helper.write_text('print(42)\n')
        c=self.case('print(42)');c['read_paths']=[str(helper)]
        spec=specifications(node('verifier'),{'default':[c]})[0]
        helper.write_text('print(41)\n')
        config=dict(policy=dict(verification=[spec],limits=dict(step_timeout_seconds=10,max_log_bytes=1048576)))
        with self.assertRaisesRegex(Blocked,'dependency changed'):
            verify(config,self.source,self.artifacts,'test',1,tree_hash(self.source),'a'*64)
