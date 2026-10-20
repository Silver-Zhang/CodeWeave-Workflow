"""Studio unit/HTTP/SQLite contracts. Fixtures are NOT real model execution."""
import copy
import hashlib
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from studio.graph import Invalid, compile_task, digest, from_task, template, validate
from studio.projection import Reader, Unavailable, project
from studio.server import App, Conflict, Drafts, Launcher, handler


def task_fixture():
    doc = template(); doc['goal'] = 'Implement the owned fixture; do not change tests.'
    return {'task_id': 'STUDIO_TEST_FIXTURE', 'project': 'owned-fixture', 'source': '/owned/source',
        'acceptance': '/owned/acceptance.txt', 'goal': doc['goal'], 'scope': ['value.py'], 'excludes': [],
        'policy': {'schema_version': 1, 'profile': 'dual-review', 'mode': 'B', 'authorization_required': True,
                   'agents': {role: {'adapter': 'codex-cli' if role == 'implementer' else 'claude-cli',
                                     'session_policy': 'new', 'model_policy': 'approved-local-binding'} for role in ('implementer', 'reviewer')},
                   'limits': doc['limits'], 'delivery': {k: False for k in ('commit','push','merge','force','tag','release')},
                   'required_contracts': ['unit','scope-inspection'], 'verification': [doc['nodes'][3]['config']]},
        'bindings': {role: {'project': 'owned-fixture', 'role': role, 'executable': '/usr/bin/fake-cli',
                           'home': f'/owned/{role}', 'read_paths': [], 'model': 'unknown', 'effort': 'unknown',
                           'session_id': None} for role in ('implementer','reviewer')}}


def database_fixture(control, state='REVIEWING'):
    control.mkdir(); db = sqlite3.connect(control / 'state.sqlite')
    db.execute('PRAGMA journal_mode=WAL')
    db.executescript('CREATE TABLE runs(id TEXT PRIMARY KEY,state TEXT,data TEXT);'
                    'CREATE TABLE events(seq INTEGER PRIMARY KEY,run TEXT,at REAL,kind TEXT,data TEXT);'
                    'CREATE TABLE operations(id TEXT PRIMARY KEY,run TEXT,kind TEXT,status TEXT,data TEXT);')
    run = 'a' * 32
    config = task_fixture()
    config['goal'] = 'SECRET_PROMPT_DO_NOT_EXPOSE'
    data = {'config': config, 'round': 2, 'authorization_path': '/secret/operator.json',
            'candidate': {'sha256': 'a' * 64}, 'verification': [{'id': 'unit', 'round': 2, 'passed': True,
            'counts': {'tests': 6, 'failures': 0, 'errors': 0, 'skipped': 0}}],
            'reviews': [{'round': 1, 'candidate_sha256': 'b'*64, 'verdict': 'NEEDS_CORRECTION',
                         'findings': [{'id': 'f1', 'status': 'OPEN'}]}], 'history': []}
    db.execute('INSERT INTO runs VALUES(?,?,?)', (run, state, json.dumps(data)))
    for kind in ('CREATED','IMPLEMENTING','VERIFYING','REVIEWING'):
        db.execute('INSERT INTO events(run,at,kind,data) VALUES(?,?,?,?)', (run, time.time(), kind, json.dumps({'round':2,'secret':'SECRET_EVENT'})))
    db.execute('INSERT INTO operations VALUES(?,?,?,?,?)', ('p1',run,'PROCESS','RUNNING',json.dumps({'argv':['SECRET_ARGV'], 'process':{'pid':99999999,'host':'foreign','boot_id':'foreign','start':'0'}})))
    db.commit()
    return db, run, data


class GraphTests(unittest.TestCase):
    def setUp(self):
        self.graph = template(); self.task = task_fixture(); self.graph['goal'] = self.task['goal']

    def test_template_and_engine_roundtrip(self):
        validate(self.graph)
        self.assertEqual(compile_task(from_task(self.task), self.task), self.task)

    def test_export_changes_real_parameters_not_authority(self):
        self.graph['goal'] = 'New goal'; self.graph['nodes'][1]['config']['model'] = 'approved-model'
        self.graph['limits']['max_review_rounds'] = 3
        result = compile_task(self.graph, self.task)
        self.assertEqual(result['goal'], 'New goal'); self.assertEqual(result['bindings']['implementer']['model'], 'approved-model')
        for key in ('source', 'acceptance', 'scope', 'excludes'):
            self.assertEqual(result[key], self.task[key])
        self.assertEqual(result['policy']['delivery'], self.task['policy']['delivery'])
        self.assertIn('scope-inspection', result['policy']['required_contracts'])
        self.assertEqual(self.task['bindings']['implementer']['model'], 'unknown')

    def test_test_order_comes_from_edges(self):
        node = copy.deepcopy(self.graph['nodes'][3]); node.update(id='v2'); node['config']['id']='second'
        self.graph['nodes'].append(node)
        for edge in self.graph['edges']:
            if edge['source']=='freeze':edge['target']='v2'
        self.graph['edges'].append({'source':'v2','target':'verification','on':'next'})
        result=compile_task(self.graph,self.task)
        self.assertEqual([v['id'] for v in result['policy']['verification']],['second','unit'])
        self.assertIn('second',result['policy']['required_contracts'])

    def test_bypass_gate_rejected(self):
        self.graph['edges']=[e for e in self.graph['edges'] if e['source']!='reviewer']
        self.graph['edges'].append({'source':'reviewer','target':'delivery','on':'next'})
        with self.assertRaises(Invalid):validate(self.graph)

    def test_missing_repair_edge_rejected(self):
        self.graph['edges']=[e for e in self.graph['edges'] if e['on']!='repair']
        with self.assertRaises(Invalid):validate(self.graph)

    def test_cycle_parallel_dangling_rejected(self):
        for edge in [{'source':'delivery','target':'authorization','on':'next'}, {'source':'implementer','target':'reviewer','on':'next'}, {'source':'missing','target':'gate','on':'next'}]:
            g=copy.deepcopy(self.graph);g['edges'].append(edge)
            with self.subTest(edge=edge),self.assertRaises(Invalid):validate(g)

    def test_invalid_numeric_json_not_accepted(self):
        for value in (float('nan'),float('inf'),True,-1):
            g=copy.deepcopy(self.graph);g['nodes'][0]['x']=value
            with self.subTest(value=value),self.assertRaises(Invalid):validate(g)

    def test_no_silent_ac_conversion(self):
        for mode in ('A','C'):
            self.task['policy']['mode']=mode
            with self.assertRaises(Invalid):compile_task(self.graph,self.task)

    def test_shell_string_and_missing_result_rejected(self):
        for argv in ('echo pass',['echo','PASS']):
            self.graph['nodes'][3]['config']['argv']=argv
            with self.assertRaises(Invalid):validate(self.graph)

    def test_unbounded_limits_rejected(self):
        self.graph['limits']['max_review_rounds']=6
        with self.assertRaises(Invalid):validate(self.graph)


    def test_protected_ids_cannot_be_renamed(self):
        self.graph['nodes'][0]['id']='renamed'
        with self.assertRaises(Invalid):validate(self.graph)

    def test_old_mandatory_verifications_not_removed(self):
        self.graph['nodes'][3]['config']['id']='replacement'
        with self.assertRaises(Invalid):compile_task(self.graph,self.task)

    def test_coordinates_do_not_change_compiled_task(self):
        before=compile_task(self.graph,self.task)
        self.graph['nodes'][1]['x']+=100
        self.assertEqual(compile_task(self.graph,self.task),before)


class StorageTests(unittest.TestCase):
    def test_immutable_revisions_and_optimistic_conflict(self):
        with tempfile.TemporaryDirectory() as tmp:
            store=Drafts(tmp);g=template();a=store.save(g)
            g['name']='Version 2';b=store.save(g,a['id'],a['revision'])
            self.assertNotEqual(a['revision'],b['revision'])
            self.assertEqual(store.get(a['id'],a['revision'])['document']['name'],template()['name'])
            with self.assertRaises(Conflict):store.save(g,a['id'],a['revision'])

    def test_reject_workspace_inside_control_or_repository(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(Invalid):App(Path(tmp)/'control/drafts',Path(tmp)/'control')
            with self.assertRaises(Invalid):App(Path(__file__).resolve().parents[1]/'studio-drafts')

    def test_refuse_adoption_and_symlink_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(Invalid):App(tmp)
            p=Path(tmp)/'studio.sqlite';p.symlink_to('/does-not-exist')
            with self.assertRaises(Invalid):Drafts(tmp)

    def test_reader_does_not_create_missing_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'control'
            with self.assertRaises(Unavailable):Reader(p).list_runs()
            self.assertFalse(p.exists())

    def test_live_wal_and_database_readonly(self):
        with tempfile.TemporaryDirectory() as tmp:
            writer,run,data=database_fixture(Path(tmp)/'control')
            try:
                reader=Reader(Path(tmp)/'control')
                a=reader.snapshot(run);self.assertEqual(a['state'],'REVIEWING')
                writer.execute('UPDATE runs SET state=? WHERE id=?',('BLOCKED',run));writer.commit()
                self.assertEqual(reader.snapshot(run)['state'],'BLOCKED')
                ro=reader.connect()
                with self.assertRaises(sqlite3.OperationalError):ro.execute('DELETE FROM runs')
                ro.close()
                self.assertEqual(writer.execute('SELECT count(*) FROM runs').fetchone()[0],1)
            finally:writer.close()

    def test_monitor_filters_raw_secrets_and_stale_process(self):
        with tempfile.TemporaryDirectory() as tmp:
            writer,run,data=database_fixture(Path(tmp)/'control')
            try:
                result=Reader(Path(tmp)/'control').snapshot(run)
                raw=json.dumps(result)
                for secret in ('SECRET_PROMPT','SECRET_EVENT','SECRET_ARGV','/secret/operator'):
                    self.assertNotIn(secret,raw)
                reviewer=next(n for n in result['graph']['nodes'] if n['type']=='reviewer')
                self.assertEqual(reviewer['status'],'unconfirmed')
                self.assertEqual(result['rounds'][0]['verdict'],'NEEDS_CORRECTION')
            finally:writer.close()

    def test_old_round_evidence_never_current_pass(self):
        task=task_fixture();data={'config':task,'round':2,'verification':[{'id':'unit','round':1,'passed':True,'counts':dict(tests=6,failures=0,errors=0,skipped=0)}]}
        result=project('a'*32,'IMPLEMENTING',data,[],'unconfirmed')
        test=next(n for n in result['graph']['nodes'] if n['type']=='verification')
        self.assertIsNone(test['counts']);self.assertEqual(test['status'],'pending')

    def test_event_page_bounded(self):
        with tempfile.TemporaryDirectory() as tmp:
            writer,run,data=database_fixture(Path(tmp)/'control')
            try:
                writer.executemany('INSERT INTO events(run,at,kind,data) VALUES(?,?,?,?)',[(run,time.time(),'EXITED','{}')]*230);writer.commit()
                self.assertEqual(len(Reader(Path(tmp)/'control').snapshot(run)['events']),200)
            finally:writer.close()


    def test_only_the_matching_verifier_is_live(self):
        task=task_fixture();extra=copy.deepcopy(task['policy']['verification'][0]);extra['id']='other'
        task['policy']['verification'].append(extra)
        result=project('a'*32,'VERIFYING',{'config':task,'round':1},[],'alive','unit')
        tests=[n for n in result['graph']['nodes'] if n['type']=='verification']
        self.assertEqual([n['status'] for n in tests],['running','pending'])

    def test_hardlinked_draft_database_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'authority';source.write_text('do not touch')
            workspace=root/'workspace';workspace.mkdir();os.link(source,workspace/'studio.sqlite')
            with self.assertRaises(Invalid):Drafts(workspace)
            self.assertEqual(source.read_text(),'do not touch')


class HTTPTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.app=App(Path(self.tmp.name)/'studio')
        self.server=ThreadingHTTPServer(('127.0.0.1',0),handler(self.app))
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()

    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join();self.tmp.cleanup()

    def request(self,path,body=None,headers=None):
        connection=HTTPConnection('127.0.0.1',self.server.server_port,timeout=3)
        h={'Authorization':'Bearer '+self.app.token};h.update(headers or {})
        if body is not None:h['Content-Type']='application/json'
        connection.request('POST' if body is not None else 'GET',path,json.dumps(body) if body is not None else None,h)
        response=connection.getresponse();result=(response.status,response.read(),dict(response.getheaders()));connection.close();return result

    def test_static_security_headers(self):
        status,body,h=self.request('/')
        self.assertEqual(status,200);self.assertIn(b'DevFlower Studio',body)
        self.assertIn("frame-ancestors 'none'",h['Content-Security-Policy'])
        self.assertNotIn(self.app.token.encode(),body)

    def test_api_requires_bearer(self):
        self.assertEqual(self.request('/api/meta',headers={'Authorization':'wrong'})[0],401)

    def test_host_and_cross_origin_refused(self):
        for h in ({'Host':'evil.invalid'},{'Origin':'https://evil.invalid'},{'Sec-Fetch-Site':'cross-site'}):
            with self.subTest(headers=h):self.assertEqual(self.request('/api/meta',headers=h)[0],403)

    def test_workflow_roundtrip(self):
        status,body,_=self.request('/api/workflows',{'document':template()})
        self.assertEqual(status,200);saved=json.loads(body)
        self.assertEqual(self.request('/api/workflows/'+saved['id'])[0],200)
        self.assertEqual(self.request('/api/workflows',{'document':template(),'id':saved['id'],'expected':'stale'})[0],409)

    def test_compile_uses_actual_engine_contract(self):
        task=task_fixture()
        status,body,_=self.request('/api/compile',{'document':from_task(task),'task':task})
        self.assertEqual(status,200,body);result=json.loads(body)
        self.assertEqual(result['task'],task);self.assertFalse(result['authorization_generated'])

    def test_no_arbitrary_shell_or_delivery_routes(self):
        for path in ('/api/exec','/api/deliver','/api/authorize','/api/cancel','/api/resume'):
            self.assertEqual(self.request(path,{'argv':['echo','no']})[0],404)
        self.assertEqual(self.request('/api/start',{'config_sha256':'a'*64})[0],422)

    def test_path_traversal_and_body_budget(self):
        self.assertEqual(self.request('/../../etc/passwd')[0],404)
        self.assertEqual(self.request('/api/workflows',{'document':'x'*300000})[0],413)


    def test_null_origin_and_forged_authorization_document_rejected(self):
        self.assertEqual(self.request('/api/meta',headers={'Origin':'null'})[0],403)
        graph=template();graph['authorization']={'commit':True,'push':True}
        self.assertEqual(self.request('/api/workflows',{'document':graph})[0],422)

    def test_launch_status_when_database_does_not_exist(self):
        self.app.reader=Reader(Path(self.tmp.name)/'not-yet-created')
        code,body,_=self.request('/api/runs')
        self.assertEqual(code,200);self.assertFalse(json.loads(body)['available'])
        self.assertFalse((Path(self.tmp.name)/'not-yet-created').exists())


class LaunchTests(unittest.TestCase):
    def test_no_permit_no_process(self):
        with patch('studio.server.subprocess.Popen') as spawn:
            with self.assertRaises(Invalid):Launcher(None).start('x')
            spawn.assert_not_called()

    def test_bound_hash_and_single_use(self):
        with tempfile.TemporaryDirectory() as tmp:
            task=Path(tmp)/'task.json';auth=Path(tmp)/'operator.json'
            task.write_text(json.dumps(task_fixture()));auth.write_text('{}')
            launcher=Launcher(Path(tmp)/'control',task,auth)
            with patch('orchestration.contracts.authorized'),patch('studio.server.subprocess.Popen') as spawn:
                spawn.return_value=Mock(poll=Mock(return_value=None))
                with self.assertRaises(Conflict):launcher.start('wrong')
                spawn.assert_not_called()
                self.assertTrue(launcher.start(launcher.task_hash)['started'])
                argv=spawn.call_args.args[0]
                self.assertEqual(Path(argv[1]).name,'devflower.py');self.assertNotIn('shell',spawn.call_args.kwargs)
                with self.assertRaises(Conflict):launcher.start(launcher.task_hash)
                self.assertEqual(spawn.call_count,1)

    def test_authorization_changed_blocks_spawn(self):
        with tempfile.TemporaryDirectory() as tmp:
            task=Path(tmp)/'task.json';auth=Path(tmp)/'operator.json'
            task.write_text(json.dumps(task_fixture()));auth.write_text('{}')
            launcher=Launcher(Path(tmp)/'control',task,auth);auth.write_text('{"changed":true}')
            with patch('studio.server.subprocess.Popen') as spawn:
                with self.assertRaises(Conflict):launcher.start(launcher.task_hash)
                spawn.assert_not_called()


if __name__=='__main__':unittest.main()
