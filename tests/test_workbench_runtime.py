"""Real filesystem/HTTP runtime boundaries; synthetic native data is not model acceptance."""
from pathlib import Path
from http.server import ThreadingHTTPServer
import copy,json,os,sys,threading,time,unittest
from unittest.mock import patch
from urllib.request import Request,urlopen
from urllib.error import HTTPError
sys.path[:0]=[str(Path(__file__).resolve().parents[1]/'tools'),str(Path(__file__).resolve().parent)]
from orchestration.common import Blocked,canonical,digest,save,tree_hash
from studio.graph import Invalid
from studio.server import Conflict
from studio.workbench_runtime import WorkbenchRuntime
from studio.workbench_server import create_server
from studio.workbench_sessions import WorkbenchSessions
from studio.workbench_examples import examples
from studio.workbench_scheduler import source_lease
from studio.workbench_external import validate_profile,validate_receipt
import test_agent_sessions


def fixture(owner):
    base=test_agent_sessions.CenterTests();base.setUp();owner.addCleanup(base.doCleanups)
    old=base.development_runtime();policy=base.root/'workbench-policy.json'
    save(policy,dict(version=1,models={},external_steps={}))
    rt=WorkbenchRuntime(old.operator_file,old.operator_sha256,tree_hash(Path(__file__).resolve().parents[1]),policy,digest(policy.read_bytes()))
    base.runtime=rt;base.project=rt.open_workspace(str(base.source))
    # Reuse the old filesystem-fixture builder without adding a production API.
    rt.sessions=rt.session_center.discover
    return base,rt


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.base,self.rt=fixture(self);self.w=self.base.project['id'];self.graph=examples(self.rt.operator['profiles'])[0]
    def request(self):return dict(workspace=self.w,graph=copy.deepcopy(self.graph),task='Synthetic transport boundary')
    def test_folder_is_browsable_but_outside_roots_and_links_are_refused(self):
        result=self.rt.folder(str(self.base.source));self.assertEqual(result['path'],str(self.base.source))
        with self.assertRaises(Blocked):self.rt.folder('/etc')
        link=self.base.source/'escape';link.symlink_to('/etc',target_is_directory=True)
        self.assertNotIn('escape',[x['name'] for x in self.rt.folder(str(self.base.source))['folders']])
    def test_ask_and_plan_cannot_select_write_permission(self):
        for mode in ('Ask','Plan'):
            n=copy.deepcopy(self.graph['nodes'][1]);n.update(mode=mode,permission='workspace-write')
            with self.assertRaises(Invalid):self.rt.node_binding(self.w,n)
    def test_drift_after_preview_refuses_launch(self):
        permit=self.rt.prepare_flow(self.request());(self.base.source/'late.txt').write_text('late')
        with patch.object(self.rt,'spawn') as spawn:
            with self.assertRaises(Conflict):self.rt.launch_flow(permit['id'],permit['sha256'],'approved test')
            spawn.assert_not_called()
    def test_duplicate_start_requires_same_authorization_and_never_spawns_twice(self):
        permit=self.rt.prepare_flow(self.request())
        with patch.object(self.rt,'spawn') as spawn:
            a=self.rt.launch_flow(permit['id'],permit['sha256'],'approved test');b=self.rt.launch_flow(permit['id'],permit['sha256'],'approved test')
            self.assertEqual(a['run']['id'],b['run']['id']);self.assertEqual(spawn.call_count,1)
            with self.assertRaises(Conflict):self.rt.launch_flow(permit['id'],'0'*64,'approved test')
    def test_dead_worker_is_unknown_never_running_and_missing_receipt_cannot_resume(self):
        p=self.rt.prepare_flow(self.request())
        with patch.object(self.rt,'spawn'):r=self.rt.launch_flow(p['id'],p['sha256'],'approved test')['run']['id']
        self.rt.flow.change('run',r,dict(state='RUNNING',created_at=time.time()-10))
        self.rt.flow.put('activation','lost',dict(id='lost',run=r,node='analyze',state='RUNNING'))
        self.assertEqual(self.rt.snapshot(r)['state'],'RECOVERY_REQUIRED')
        with self.assertRaises(Blocked):self.rt.control(r,'resume')
    def test_failed_first_session_name_never_null_or_protocol_scaffold(self):
        path,row=self.base.native_profile('codex',managed=True)
        # Native text scaffold is not an acceptable title; actual name remains separate.
        with path.open('a') as f:f.write(json.dumps(dict(type='response_item',payload=dict(type='message',role='user',content=[dict(type='input_text',text='## 本次运行初始化\nINIT\n\n## 每轮任务\nExplain the graph')])) )+'\n')
        rows=WorkbenchSessions(self.rt).listing(self.w)['sessions']
        self.assertTrue(all(isinstance(x['title'],str) and x['title'].strip() for x in rows))
    def test_two_native_uuids_in_one_managed_home_keep_exact_binding(self):
        path,row=self.base.native_profile('codex',managed=True)
        original=self.rt.db.get('chat-profile','test-profile');other=copy.deepcopy(original);other['binding']['session_id']='22222222-2222-4222-8222-222222222222'
        self.rt.db.put('chat-profile','second-profile',other)
        native=self.rt.db.get('session-handle',row['handle']);binding,reason=self.rt.session_center._binding(native,self.base.project)
        self.assertIsNotNone(binding,reason);self.assertEqual(binding['session_id'],row['session_id'])
    def test_native_flat_archive_history_and_metadata_restore_are_distinct(self):
        path,row=self.base.native_profile('codex',managed=True);manager=WorkbenchSessions(self.rt)
        home=Path(self.rt.db.get('chat-profile','test-profile')['binding']['home'])
        archived=home/'.codex/archived_sessions'/path.name;archived.parent.mkdir(parents=True)
        with patch.object(manager,'rpc',side_effect=lambda *args:path.rename(archived)):
            result=manager.change(self.w,row['handle'],'native_archive',answer='approved own synthetic session')
        self.assertTrue(result['native_modified'])
        history=manager.history(self.w,row['handle']);self.assertTrue(history['messages'])
        self.assertNotIn('HIDDEN_REASONING',json.dumps(history))
        with patch.object(manager,'rpc',side_effect=lambda *args:archived.rename(path)):
            self.assertTrue(manager.change(self.w,row['handle'],'restore')['native_modified'])
        manager.change(self.w,row['handle'],'trash',answer='approved own synthetic session')
        self.assertFalse(manager.change(self.w,row['handle'],'restore')['native_modified'])
    def test_attachments_cannot_grant_credential_or_outside_access(self):
        rows=self.rt.attachments(str(self.base.source),['/etc/passwd','../external','missing'])
        self.assertFalse(any(r['accessible'] for r in rows))
    def test_receiver_rechecks_attachment_hash_and_access(self):
        file=self.base.source/'artifact.txt';file.write_text('one')
        value=[{'content':{'artifacts':self.rt.attachments(str(self.base.source),['artifact.txt'])}}]
        self.assertTrue(self.rt.recipient_inputs(str(self.base.source),value)[0]['content']['artifacts'][0]['accessible'])
        file.write_text('two')
        self.assertFalse(self.rt.recipient_inputs(str(self.base.source),value)[0]['content']['artifacts'][0]['accessible'])
        self.assertFalse(self.rt.recipient_inputs(str(self.base.root),value)[0]['content']['artifacts'][0]['accessible'])
    def test_lost_native_mutation_receipt_prevents_blind_retry(self):
        _,row=self.base.native_profile('codex',managed=True);internal=self.rt.db.get('session-handle',row['handle'])
        binding,_=self.rt.session_center._binding(internal,self.base.project);manager=WorkbenchSessions(self.rt)
        with patch('studio.workbench_sessions.execute',return_value=({'exit':1,'timeout':True},b'',b'')) as execute:
            for _ in range(2):
                with self.assertRaises(Blocked):manager.rpc(binding,str(self.base.source),'thread/fork',{'threadId':row['session_id']})
            self.assertEqual(execute.call_count,1)
        self.assertEqual(self.rt.flow.list('native-mutation')[0]['state'],'RECOVERY_REQUIRED')
    def test_writer_lease_excludes_other_readers_but_two_readers_coexist(self):
        path=self.base.root/'scope.lock'
        with source_lease(path,False),source_lease(path,False):
            with self.assertRaises(Blocked):
                with source_lease(path,True):pass
        with source_lease(path,True):
            with self.assertRaises(Blocked):
                with source_lease(path,False):pass
    def test_delivery_profile_not_supplied_by_browser(self):
        g=self.request();g['graph']['nodes'][1].update(kind='delivery',profile='browser-command')
        with self.assertRaises(Invalid):self.rt.prepare_flow(g)
    def test_external_accept_with_failing_tests_or_wrong_identity_never_passes(self):
        executable=str(Path(sys.executable).resolve())
        sha=digest(Path(executable).read_bytes())
        self.rt.policy['external_steps']['fixed']=dict(kind='verify',argv=[executable],executable_sha256=sha,dependencies={executable:sha})
        self.rt.flow.put('run','r',dict(workspace=self.w,graph_sha256='g',authorization={},task='frozen task'))
        self.rt.flow.put('activation','a',dict(id='a',run='r'))
        base=dict(run='r',activation='a',candidate_sha256=tree_hash(self.base.source),graph_sha256='g',
                  authorization_sha256=digest(canonical({})),acceptance_sha256=digest(b'frozen task'),
                  tests=2,failures=1,errors=0,skipped=0,verdict='ACCEPT',verified=True)
        for changed in ({},{'failures':0,'candidate_sha256':'0'*64},{'failures':0,'tests':0},{'failures':0,'skipped':1}):
            receipt=dict(base,**changed)
            with patch('studio.workbench_runtime.execute',return_value=({'exit':0,'timeout':False,'cancelled':False,'overflow':False},canonical(receipt),b'')):
                with self.assertRaises(Blocked):self.rt.external_step('r','a',{'kind':'verify','profile':'fixed'},[])
        with patch('studio.workbench_runtime.execute',return_value=({'exit':0,'timeout':False,'cancelled':False,'overflow':False},canonical(dict(base,failures=0)),b'')):
            self.assertTrue(self.rt.external_step('r','a',{'kind':'verify','profile':'fixed'},[])['result']['verified'])
    def test_external_delivery_needs_remote_readback_even_with_accept(self):
        executable=str(Path(sys.executable).resolve())
        sha=digest(Path(executable).read_bytes())
        self.rt.policy['external_steps']['fixed']=dict(kind='delivery',argv=[executable],executable_sha256=sha,dependencies={executable:sha})
        self.rt.flow.put('run','r',dict(workspace=self.w,graph_sha256='g',authorization={},task='frozen task'))
        self.rt.flow.put('activation','a',dict(id='a',run='r'))
        receipt=dict(run='r',activation='a',candidate_sha256=tree_hash(self.base.source),graph_sha256='g',
                     authorization_sha256=digest(canonical({})),acceptance_sha256=digest(b'frozen task'),
                     verdict='ACCEPT',remote_verified=False,delivery_state='COMPLETED')
        with patch('studio.workbench_runtime.execute',return_value=({'exit':0,'timeout':False,'cancelled':False,'overflow':False},canonical(receipt),b'')):
            with self.assertRaises(Blocked):self.rt.external_step('r','a',{'kind':'delivery','profile':'fixed'},[])
    def test_external_interpreter_pin_does_not_cover_mutable_script(self):
        exe=str(Path(sys.executable).resolve());sha=digest(Path(exe).read_bytes());script=self.base.root/'bridge.py';script.write_text('print(1)')
        profile=dict(kind='verify',argv=[exe,'-I',str(script)],executable_sha256=sha,dependencies={exe:sha})
        with self.assertRaises(Blocked):validate_profile(profile)
        profile['dependencies'][str(script)]=digest(script.read_bytes());validate_profile(profile)
        script.write_text('print(2)')
        with self.assertRaises(Blocked):validate_profile(profile)
    def test_external_receipt_requires_contract_counters_and_real_remote_confirmation(self):
        p=dict(run='r',activation='a',candidate_sha256='c',graph_sha256='g',authorization_sha256='h',acceptance_sha256=digest(b'frozen task'))
        receipt=dict(p,tests=1,failures=0,errors=0,skipped=0,verified=True)
        validate_receipt(receipt,p,'verify')
        for change in ({'tests':True},{'tests':-1},{'skipped':1},{'graph_sha256':'stale'},{'authorization_sha256':'stale'},{'verified':False}):
            with self.assertRaises(Blocked):validate_receipt(dict(receipt,**change),p,'verify')
        delivery=dict(p,verdict='ACCEPT',remote_verified=True,delivery_state='COMPLETED');validate_receipt(delivery,p,'delivery')
        for change in ({'remote_verified':'true'},{'delivery_state':'PARTIAL_DELIVERY'},{'verdict':'ACCEPT_WITH_LIMITATIONS'}):
            with self.assertRaises(Blocked):validate_receipt(dict(delivery,**change),p,'delivery')

    def test_external_receipt_rejects_another_or_missing_task_contract(self):
        payload=dict(run='r',activation='a',candidate_sha256='c',graph_sha256='g',authorization_sha256='h',
                     acceptance_sha256=digest('冻结任务\r\n保留尾部空格  \n'.encode('utf-8')))
        for kind,extra in (('verify',dict(tests=1,failures=0,errors=0,skipped=0,verified=True)),
                           ('delivery',dict(verdict='ACCEPT',remote_verified=True,delivery_state='COMPLETED'))):
            receipt=dict(payload,**extra);validate_receipt(receipt,payload,kind)
            for changed in (digest(b'another task'),None):
                bad=dict(receipt,acceptance_sha256=changed)
                if changed is None:bad.pop('acceptance_sha256')
                with self.subTest(kind=kind,acceptance=changed):
                    with self.assertRaises(Blocked):validate_receipt(bad,payload,kind)

    def test_external_payload_hashes_frozen_task_utf8_bytes(self):
        executable=str(Path(sys.executable).resolve());sha=digest(Path(executable).read_bytes())
        self.rt.policy['external_steps']['fixed']=dict(kind='verify',argv=[executable],executable_sha256=sha,dependencies={executable:sha})
        request=self.request();request['task']='  冻结任务\r\n精确 UTF-8 字节  \n'
        permit=self.rt.prepare_flow(request)
        with patch.object(self.rt,'spawn'):
            run=self.rt.launch_flow(permit['id'],permit['sha256'],'approved test')['run']['id']
        self.rt.flow.put('activation','a',dict(id='a',run=run))
        request['task']='edited draft must not replace frozen task'
        expected=digest('  冻结任务\r\n精确 UTF-8 字节  \n'.encode('utf-8'))
        observed=[];receipt_acceptance=expected
        def execute(*args,**kwargs):
            payload=json.loads(kwargs['input_text']);observed.append(payload)
            receipt={k:payload[k] for k in ('run','activation','candidate_sha256','graph_sha256','authorization_sha256')}
            receipt.update(acceptance_sha256=receipt_acceptance,
                           tests=1,failures=0,errors=0,skipped=0,verified=True)
            if receipt_acceptance is None:receipt.pop('acceptance_sha256')
            return dict(exit=0,timeout=False,overflow=False,cancelled=False),canonical(receipt),b''
        with patch('studio.workbench_runtime.execute',side_effect=execute):
            result=self.rt.external_step(run,'a',{'kind':'verify','profile':'fixed'},[])
        self.assertEqual(observed[0].get('acceptance_sha256'),expected)
        self.assertEqual(result['result']['acceptance_sha256'],expected)
        for receipt_acceptance in (digest(b'another task'),None):
            with self.subTest(receipt_acceptance=receipt_acceptance):
                with patch('studio.workbench_runtime.execute',side_effect=execute):
                    with self.assertRaises(Blocked):self.rt.external_step(run,'a',{'kind':'verify','profile':'fixed'},[])


class HttpTests(unittest.TestCase):
    def setUp(self):
        self.base,self.rt=fixture(self);self.server,self.token=create_server(self.rt);t=threading.Thread(target=self.server.serve_forever,daemon=True);t.start()
        self.addCleanup(t.join);self.addCleanup(self.server.server_close);self.addCleanup(self.server.shutdown)
        self.url='http://127.0.0.1:'+str(self.server.server_port)
    def get(self,path,auth=True,extra=None):
        headers={'Authorization':'Bearer '+self.token} if auth else {};headers.update(extra or {})
        return urlopen(Request(self.url+path,headers=headers))
    def test_auth_origin_cookie_and_static_boundary(self):
        with self.assertRaises(HTTPError) as e:self.get('/api/status',False)
        self.assertEqual(e.exception.code,403)
        with self.assertRaises(HTTPError):self.get('/api/status',extra={'Origin':'http://127.0.0.1:1'})
        with self.assertRaises(HTTPError):self.get('/api/status',False,{'Cookie':'devflower_workbench='+self.token})
        with self.get('/') as r:self.assertIn('Max-Age=0',r.headers['Set-Cookie'])
        with self.get('/api/status') as r:self.assertFalse(json.load(r)['stable_approved'])
    def test_no_shell_or_stable_approval_endpoints(self):
        for path in ('/api/shell','/api/approve-stable','/api/authorize-run'):
            with self.assertRaises(HTTPError) as e:self.get(path)
            self.assertEqual(e.exception.code,400)

if __name__=='__main__':unittest.main()
