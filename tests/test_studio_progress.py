"""Regression evidence for explicit verifier identity, validation, WAL and candidate rounds."""
import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from test_studio import task_fixture
from orchestration.common import tree_hash
from orchestration.store import Store
from orchestration import verification
from studio.graph import from_task, validate, Invalid
from studio.projection import Reader, project


def nodes(snapshot):
    return [n for n in snapshot['graph']['nodes'] if n['type'] == 'verification']


class ProgressTests(unittest.TestCase):
    def test_equal_commands_progress_before_whole_list_finishes_and_no_exit_zero_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp); source = base/'source'; source.mkdir(); (source/'fixed').write_text('fixed')
            control = base/'control'; config = task_fixture()
            argv = [sys.executable, '-c', 'import sys,time,pathlib;time.sleep(.2);pathlib.Path(sys.argv[1]).write_text(sys.argv[2])', '{result}', json.dumps(dict(tests=1,failures=0,errors=0,skipped=0))]
            config['policy']['verification'] = [dict(config['policy']['verification'][0], id=name, argv=argv, result_format='controller-json') for name in ('unit test', 'other test')]
            store = Store(control); candidate = tree_hash(source)
            run = store.create(dict(config=config, round=1, candidate={'sha256':candidate}, candidate_round=1, acceptance_sha256='b'*64))
            store.transition(run, 'VERIFYING'); entered = threading.Event(); release = threading.Event(); errors=[]
            original = verification.counts
            def slow_validation(*args):
                if not entered.is_set():
                    entered.set()
                    if not release.wait(5): raise RuntimeError('test validation barrier timeout')
                return original(*args)
            def worker():
                writer=Store(control)
                try:
                    result=verification.verify(config,source,base/'artifacts',run,1,candidate,'b'*64,writer)
                    writer.transition(run,'REVIEWING',verification=result)
                except Exception as e:errors.append(e)
                finally:writer.db.close()
            with patch.object(verification,'counts',slow_validation):
                thread=threading.Thread(target=worker);thread.start()
                try:
                    self.assertTrue(entered.wait(5))
                    reader=Reader(control);current=nodes(reader.snapshot(run))
                    self.assertEqual([n['status'] for n in current],['executed','pending'])
                    self.assertIsNone(current[0]['counts'])  # exit=0 is not validated PASS
                    release.set();seen=False;reads=0;end=time.monotonic()+5
                    while thread.is_alive() and time.monotonic()<end:
                        snapshot=reader.snapshot(run);current=nodes(snapshot);reads+=1
                        if [n['status'] for n in current]==['passed','running']:
                            seen=True
                            self.assertEqual(current[0]['counts']['tests'],1)
                            self.assertNotEqual(current[0]['operation_id'],current[1]['operation_id'])
                            self.assertEqual(current[1]['verification_round'],1)
                        time.sleep(.002)
                    self.assertTrue(seen,f'first validated result must appear while identical second command runs; errors={errors}; final={current}')
                    self.assertGreater(reads,1)
                finally:release.set();thread.join(6)
            self.assertFalse(thread.is_alive());self.assertFalse(errors,errors)
            self.assertEqual([n['status'] for n in nodes(Reader(control).snapshot(run))],['passed','passed'])
            ops=store.operations(run);v=[o for o in ops if o['kind']=='VERIFICATION'];p=[o for o in ops if o['kind']=='PROCESS']
            self.assertEqual(len(v),2);self.assertEqual(len(p),2)
            for op,proc in zip(v,p):
                self.assertEqual(proc['data']['context']['verification_operation_id'],op['id'])
                self.assertEqual(op['data']['process_operation_id'],proc['id'])
                self.assertNotIn('argv',op['data'])
            store.db.close()

    def test_invalid_result_exit_zero_is_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);source=base/'source';source.mkdir();config=task_fixture()
            config['policy']['verification'][0]['argv']=[sys.executable,'-c','import pathlib,sys;pathlib.Path(sys.argv[1]).write_text("{}")','{result}']
            s=Store(base/'control');h=tree_hash(source);run=s.create(dict(config=config,round=1,candidate={'sha256':h},candidate_round=1,acceptance_sha256='b'*64));s.transition(run,'VERIFYING')
            with self.assertRaises(Exception):verification.verify(config,source,base/'artifacts',run,1,h,'b'*64,s)
            s.transition(run,'BLOCKED');node=nodes(Reader(base/'control').snapshot(run))[0]
            self.assertEqual(node['status'],'blocked');self.assertIsNone(node['counts']);s.db.close()

    def test_original_id_preserves_failed_and_passed_results(self):
        config=task_fixture();spec=config['policy']['verification'][0]
        config['policy']['verification']=[dict(spec,id=i) for i in ('unit test','other test')]
        data={'config':config,'round':1,'verification':[dict(id=i,round=1,passed=j==1,counts=dict(tests=j+1,failures=1-j,errors=0,skipped=0)) for j,i in enumerate(('unit test','other test'))]}
        actual=nodes(project('a'*32,'BLOCKED',data,[],'unconfirmed'))
        self.assertEqual([n['status'] for n in actual],['failed','passed'])
        self.assertEqual([n['counts']['tests'] for n in actual],[1,2]);self.assertNotEqual(actual[0]['config']['id'],actual[1]['config']['id'])

    def test_new_round_has_no_old_candidate_counts_or_accept(self):
        data={'config':task_fixture(),'round':2,'candidate':{'sha256':'a'*64},'candidate_round':1,
              'verification':[dict(id='unit',round=1,passed=True,counts=dict(tests=1,failures=0,errors=0,skipped=0))],
              'review':{'report':dict(round=1,candidate_sha256='a'*64,verdict='ACCEPT')}}
        result=project('b'*32,'IMPLEMENTING',data,[],'alive')
        self.assertIsNone(result['candidate']);self.assertFalse(result['candidate_frozen']);self.assertIsNone(result['candidate_round'])
        self.assertEqual(result['previous_candidate'],dict(sha256='a'*64,round=1));self.assertIsNone(result['verdict']);self.assertIsNone(nodes(result)[0]['counts'])
        self.assertEqual(data['review']['report']['verdict'],'ACCEPT')  # never rewrite historical evidence
        data.update(candidate={'sha256':'c'*64},candidate_round=2)
        result=project('b'*32,'VERIFYING',data,[],'unconfirmed');self.assertEqual(result['candidate'],'c'*64);self.assertTrue(result['candidate_frozen'])

    def test_legacy_candidate_without_provenance_is_unassigned(self):
        result=project('b'*32,'IMPLEMENTING',{'config':task_fixture(),'round':2,'candidate':{'sha256':'a'*64}},[],'alive')
        self.assertIsNone(result['candidate']);self.assertEqual(result['previous_candidate']['round'],None)

    def test_mismatched_operation_candidate_and_round_never_project_pass(self):
        data=dict(config=task_fixture(),round=2,candidate={'sha256':'a'*64},candidate_round=2,acceptance_sha256='b'*64)
        for field,value in [('run_id','d'*32),('round',1),('candidate_sha256','c'*64),('acceptance_sha256','c'*64)]:
            info=dict(run_id='a'*32,round=2,candidate_sha256='a'*64,acceptance_sha256='b'*64,verification_id='unit',passed=True,counts=dict(tests=1,failures=0,errors=0,skipped=0));info[field]=value
            result=project('a'*32,'VERIFYING',data,[],'alive',operations=[dict(id='op',kind='VERIFICATION',status='VALIDATED',data=info)])
            self.assertEqual(nodes(result)[0]['status'],'pending')

    def test_editor_subset_never_silently_truncates_monitor(self):
        task=task_fixture();spec=task['policy']['verification'][0];task['policy']['verification']=[dict(spec,id=f'test-{i}') for i in range(21)]
        graph=from_task(task);self.assertEqual(len([n for n in graph['nodes'] if n['type']=='verification']),21)
        with self.assertRaises(Invalid):validate(graph)
        self.assertEqual(len(nodes(project('a'*32,'VERIFYING',{'config':task,'round':1},[],'unconfirmed'))),21)

    def test_crafted_display_label_collision_is_distinct(self):
        config=task_fixture();spec=config['policy']['verification'][0]
        ids=['unit test','verification-8b7927fe4531db10','unknown','1. unknown']
        config['policy']['verification']=[dict(spec,id=i) for i in ids]
        actual=nodes(project('a'*32,'VERIFYING',{'config':config,'round':1},[],'unconfirmed'))
        self.assertEqual(len({n['label'] for n in actual}),len(ids))
        self.assertEqual(len({n['config']['id'] for n in actual}),len(ids))
