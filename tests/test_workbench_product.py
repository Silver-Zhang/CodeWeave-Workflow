"""Product projections: exact identity and only explicitly public provider summaries."""
import copy
import json
import tempfile
import time
import sys
import unittest
from unittest.mock import patch
from pathlib import Path

sys.path[:0] = [str(Path(__file__).parent), str(Path(__file__).resolve().parents[1] / 'tools')]
from test_workbench_runtime import fixture, structured_session
from studio.workbench_sessions import WorkbenchSessions
from orchestration.common import Blocked, digest
from studio.graph import Invalid
from studio.workbench_examples import examples
from studio.workbench_graph import validate_graph
from studio.workbench_external import validate_profile
from studio.workbench_store import WorkbenchStore
from studio.workbench_scheduler import Scheduler
from studio.workbench_scheduler import source_lease
from orchestration.store import lease
from studio.server import Conflict


class ProductProjectionTests(unittest.TestCase):
    def test_node_link_does_not_select_another_homes_identical_uuid(self):
        base, rt = fixture(self)
        _, first = structured_session(base, rt, 'same-uuid-first', 'codex')
        _, second = structured_session(base, rt, 'same-uuid-second', 'codex')
        self.assertEqual(first['session_id'], second['session_id'])
        manager = WorkbenchSessions(rt)
        result = manager.activation_session(base.project['id'], 'same-uuid-first-run', 'same-uuid-first-turn-1')
        self.assertEqual(result['handle'], first['handle'])
        with self.assertRaises(Blocked):
            manager.activation_session(base.project['id'], 'same-uuid-second-run', 'same-uuid-first-turn-1')

    def test_existing_session_reports_its_bound_profile_not_the_default_other_provider(self):
        base, rt = fixture(self)
        _, session = structured_session(base, rt, 'actual-codex-config', 'codex')
        row = next(r for r in WorkbenchSessions(rt).listing(base.project['id'])['sessions']
                   if r['handle'] == session['handle'])
        profile = rt.operator['profiles']['default-codex']
        self.assertEqual(row['execution'], dict(profile='default-codex', provider='codex',
                                               model=profile['model'], effort=profile['effort']))

    def test_sidebar_exposes_bound_workflow_and_human_node_name(self):
        base, rt = fixture(self)
        _, session = structured_session(base, rt, 'named-workflow')
        row = next(r for r in WorkbenchSessions(rt).listing(base.project['id'])['sessions']
                   if r['handle'] == session['handle'])
        self.assertEqual(row['workflow_id'], 'named-workflow-run')
        self.assertEqual(row['workflow'], rt.flow.get('run', row['workflow_id'])['graph']['name'])
        self.assertEqual(row['node_name'], 'Synthetic named-workflow')

    def test_explicit_public_summary_is_separate_from_hidden_reasoning(self):
        base, rt = fixture(self)
        path, _ = structured_session(base, rt, 'public-summary', 'codex')
        with path.open('a') as stream:
            stream.write(json.dumps({'type': 'response_item', 'payload': {'type': 'reasoning',
                'summary': [{'type': 'summary_text', 'text': 'PUBLIC-SUMMARY'}],
                'content': [{'type': 'reasoning_text', 'text': 'HIDDEN-CONTENT'}],
                'encrypted_content': 'HIDDEN-ENCRYPTED'}}) + '\n')
        rows = rt.session_center.discover(base.project['id'], True)['discovery']['sessions']
        row = next(r for r in rows if rt.db.get('session-handle', r['handle'])['native']['path'] == str(path))
        history = WorkbenchSessions(rt).history(base.project['id'], row['handle'])
        self.assertEqual(history['summaries'], [{'source': 'provider-public-summary', 'text': 'PUBLIC-SUMMARY'}])
        self.assertNotIn('HIDDEN-', json.dumps(history))


class IndependentCounterexampleTests(unittest.TestCase):
    # Derived from the actual Claude source-r1 scripts; host-executed originals
    # and unchanged negative outputs are retained outside the source repository.
    def test_relative_interpreter_script_cannot_run_as_a_pinned_external_executor(self):
        exe=str(Path(sys.executable).resolve());sha=digest(Path(exe).read_bytes())
        for argv in ([exe,'-I','script.py'],[exe,'-m','untrusted_module'],[exe,'-c','print(1)'],[exe,'relative_without_suffix']):
            with self.subTest(argv=argv):
                with self.assertRaises(Blocked):validate_profile(dict(kind='verify',argv=argv,executable_sha256=sha,dependencies={exe:sha}))

    def test_duplicate_source_target_edges_do_not_duplicate_merge_inputs(self):
        base,rt=fixture(self);g=examples(rt.operator['profiles'])[1]
        g['edges'].append(dict(id='duplicate',source='branchA',target='merge'))
        with self.assertRaises(Invalid):validate_graph(g)

    def test_external_directory_arguments_also_require_tree_pins(self):
        from orchestration.common import tree_hash
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);script=root/'adapter.py';script.write_text('print(1)')
            exe=str(Path(sys.executable).resolve());sha=digest(Path(exe).read_bytes())
            profile=dict(kind='verify',argv=[exe,'-I',str(script),'--data',str(root)],executable_sha256=sha,
                         dependencies={exe:sha,str(script):digest(script.read_bytes())})
            with self.assertRaises(Blocked):validate_profile(profile)
            profile['dependency_trees']={str(root):tree_hash(root)}
            validate_profile(profile)

    def test_actual_sidebar_execute_entry_shares_only_readonly_source_leases(self):
        base,rt=fixture(self);center=rt.session_center
        for permission in ('read','workspace-write'):
            with self.subTest(permission=permission):
                value=center.prepare(dict(workspace=base.project['id'],handle='new',profile='default-codex',
                                          prompt='Synthetic lease probe; provider is not invoked',permission=permission))['data']
                key='shared-'+permission;rt.db.put('session-operation',key,dict(value,id=key,state='QUEUED',cancel_requested=False,created_at=time.time()))
                observed=[]
                def probe(*args,**kwargs):
                    try:
                        with source_lease(Path(value['source']['common_dir'])/'devflower-writer.lock',False):observed.append(True)
                    except Blocked:observed.append(False)
                    raise Blocked('Synthetic probe ends before calling any provider')
                with patch('studio.session_center.CLI.start',side_effect=probe):center.execute(key)
                self.assertEqual(observed,[permission=='read'])

    def test_finished_run_controls_do_not_rewrite_historical_state(self):
        base,rt=fixture(self);rt.flow.put('run','closed',dict(id='closed',state='COMPLETED'))
        before=rt.flow.get('run','closed')
        for action in ('pause','stop','resume'):
            with self.assertRaises(Conflict):rt.control('closed',action)
        self.assertEqual(rt.flow.get('run','closed'),before)

    def test_discovered_but_unapproved_model_is_not_an_executable_choice(self):
        base,rt=fixture(self)
        rt.flow.put('model-catalog','codex',{'id':'codex','models':[dict(id='unapproved-native-model',efforts=['high'])]})
        cap=next(c for c in WorkbenchSessions(rt).capabilities() if c['provider']=='codex')
        model=next(m for m in cap['models'] if m['id']=='unapproved-native-model')
        self.assertFalse(model.get('execution_allowed',True))

    def test_selected_branch_merge_waits_for_all_terminal_states_and_runs_downstream_once(self):
        base,rt=fixture(self)
        for selected in (True,False):
            with self.subTest(selected=selected),tempfile.TemporaryDirectory() as folder:
                graph=examples(rt.operator['profiles'])[1]
                graph['nodes'].insert(1,dict(id='choose',kind='condition',name='选择',test=dict(field='result.task',op='equals',value='typed conditional merge' if selected else 'other')))
                next(n for n in graph['nodes'] if n['id']=='merge')['strategy']='selected'
                for e in graph['edges']:
                    if e['source']=='start':e.update(source='choose',when='true' if e['target']=='branchA' else 'false')
                graph['edges'].insert(0,dict(id='choose-input',source='start',target='choose'))
                db=WorkbenchStore(Path(folder)/'flow.sqlite')
                class Runtime:
                    flow=db
                    def check_operator(self):pass
                db.put('run','r',dict(id='r',graph=validate_graph(graph),state='QUEUED',task='typed conditional merge',created_at=time.time(),paused=False,cancel_requested=False))
                calls=[]
                def execute(n,*args):calls.append(n['id']);return dict(answer=n['id'],result={'accepted':selected})
                # Both typed condition outcomes must converge exactly once.
                Scheduler(Runtime(),'r',execute).run_graph()
                self.assertEqual(db.get('run','r')['state'],'COMPLETED')
                self.assertEqual(calls,['branchA' if selected else 'branchB','summary'])
                merge=next(a for a in db.list('activation') if a['node']=='merge')
                self.assertEqual([v['source'] for v in merge['output']['sources']],['branchA' if selected else 'branchB'])


if __name__ == '__main__':
    unittest.main()
