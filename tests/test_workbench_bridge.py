"""Real frozen verification / local-bare transport; synthetic model verdicts only.

The test-only approval and fake native CLI never leave TemporaryDirectory and
cannot authorize production publication. Full native acceptance is separate.
"""
import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys
from unittest.mock import patch

sys.path[:0]=[str(Path(__file__).resolve().parents[1]/'tools'),str(Path(__file__).parent)]
from devflower_stable_bridge import Bridge
from test_orchestration import Fixture,repo
from orchestration import controller,delivery
from orchestration.common import Blocked,canonical,digest,git,manifest,save,tree_hash
from orchestration.store import Store
from orchestration.trust import TrustedRelease


class BridgeTests(Fixture):
    def setUp(self):
        super().setUp()
        self.remote=self.base/'source.git'
        subprocess.run(['git','clone','-q','--bare',str(self.source),str(self.remote)],check=True)
        git(self.source,'remote','add','origin',str(self.remote))
        target=dict(kind='source',root=str(self.source),remote=str(self.remote),branch='flow/fixture',expected_tip=git(self.source,'rev-parse','HEAD'))
        self.config['delivery_targets']=[target]
        self.config['policy']['delivery'].update(commit=True,push=True)
        self.authorize();self.auth.update(commit=True,push=True);save(self.auth_path,self.auth)
        root=Path(controller.__file__).resolve().parents[2];entries=manifest(root);record=self.base/'test-approval.json'
        save(record,dict(version=1,root=str(root),git_commit='a'*40,git_tree='b'*40,candidate_sha256=digest(canonical(entries)),files=entries,review_verdict='ACCEPT',review_receipt_sha256='c'*64,approval_ref='SYNTHETIC TEST ONLY; NEVER PRODUCTION'))
        trust=TrustedRelease(record,digest(record.read_bytes()))
        result=controller.start(self.control,self.config_path,self.auth_path,trust=trust)
        self.assertEqual(result['state'],'READY',result['data'].get('reason'));self.run=result['id']
        self.workspace=self.base/'flow-workspace';shutil.copytree(result['data']['candidate_path'],self.workspace)
        self.payload=dict(run='1'*32,activation='verify-1',source=str(self.workspace),candidate_sha256=tree_hash(self.workspace),graph_sha256='g'*64,authorization_sha256='h'*64,
                          acceptance_sha256=digest(self.acceptance.read_bytes()))
        grants=self.base/'grants';grants.mkdir();save(grants/(self.payload['run']+'.json'),dict(control=str(self.control),stable_run=self.run,binding={k:v for k,v in self.payload.items() if k!='activation'},github=None))
        cfg=dict(version=1,stable=trust.binding(),grants=str(grants))
        self.bridge=Bridge(cfg);self.bridge.bind(self.payload);self.addCleanup(lambda:self.bridge.store.db.close())

    def test_fixed_stable_verification_and_two_idempotent_delivery_readbacks(self):
        verify=self.bridge.execute('verify',self.payload)
        self.assertGreater(verify['tests'],0);self.assertTrue(verify['verified'])
        self.assertEqual(verify['acceptance_sha256'],self.payload['acceptance_sha256'])
        result=self.bridge.execute('delivery',dict(self.payload,activation='delivery-1'))
        self.assertTrue(result['remote_verified']);self.assertEqual(result['delivery_state'],'COMPLETED')
        self.assertEqual(result['acceptance_sha256'],self.payload['acceptance_sha256'])
        head=delivery.remote_tip(str(self.remote),'flow/fixture')
        again=self.bridge.execute('delivery',dict(self.payload,activation='delivery-1'))
        self.assertEqual(again['receipts'],result['receipts']);self.assertEqual(delivery.remote_tip(str(self.remote),'flow/fixture'),head)
        self.assertEqual(git(self.source,'status','--porcelain=v1'),'')

    def test_isolated_cli_reads_real_stable_results_without_target_imports(self):
        config=self.base/'bridge-config.json';save(config,self.bridge.config)
        program=Path(__file__).resolve().parents[1]/'tools/devflower_stable_bridge.py'
        # Candidate-controlled names must not shadow the trusted Python modules.
        hostile=self.base/'hostile-cwd';hostile.mkdir();(hostile/'orchestration.py').write_text('raise RuntimeError("untrusted import")')
        p=subprocess.run([sys.executable,'-I','-B',str(program),'--config',str(config),'--config-sha256',digest(config.read_bytes()),'--kind','verify'],input=canonical(self.payload),capture_output=True,cwd=hostile,timeout=30)
        self.assertEqual(p.returncode,0,p.stderr.decode());receipt=json.loads(p.stdout)
        self.assertTrue(receipt['verified']);self.assertGreater(receipt['tests'],0)
        self.assertEqual(receipt['acceptance_sha256'],self.payload['acceptance_sha256'])

    def test_lost_push_receipt_is_resolved_by_readback_without_second_push(self):
        real=delivery.push
        calls=[]
        def lost(store,run,target,sha):
            def push(argv):
                calls.append(argv);subprocess.run(argv,capture_output=True,check=True)
                raise subprocess.TimeoutExpired(argv,1)
            return real(store,run,target,sha,push_runner=push)
        with patch('orchestration.delivery.push',side_effect=lost):
            result=self.bridge.execute('delivery',self.payload)
        self.assertTrue(result['remote_verified']);self.assertEqual(len(calls),1)

    def test_accept_cannot_override_failed_tests_or_changed_source_or_contract(self):
        original=copy.deepcopy(self.bridge.store.get(self.run)['data']['verification'])
        bad=copy.deepcopy(original);bad[0]['counts']['failures']=1
        self.bridge.store.transition(self.run,'READY',verification=bad)
        with self.assertRaises(Blocked):self.bridge.execute('delivery',self.payload)
        self.bridge.store.transition(self.run,'READY',verification=original)
        with self.assertRaises(Blocked):self.bridge.execute('verify',dict(self.payload,graph_sha256='0'*64))
        (self.workspace/'value.py').write_text('VALUE = 43\n')
        with self.assertRaises(Blocked):self.bridge.execute('delivery',self.payload)
        self.assertEqual(delivery.remote_tip(str(self.remote),'flow/fixture'),git(self.source,'rev-parse','HEAD'))

    def test_remote_race_and_two_repository_partial_delivery_are_truthful(self):
        records=repo(self.base/'records','project/fixture');remote=self.base/'records.git'
        subprocess.run(['git','clone','-q','--bare',str(records),str(remote)],check=True)
        git(records,'remote','add','origin',str(remote))
        second=dict(kind='records',root=str(records),remote=str(remote),branch='project/fixture',expected_tip='0'*40,receipt_path='project/receipt.json')
        data=self.bridge.store.get(self.run)['data'];cfg=copy.deepcopy(data['config']);cfg['delivery_targets'].append(second)
        save(self.config_path,cfg);self.auth['config_sha256']=digest(canonical(cfg));save(self.auth_path,self.auth)
        self.bridge.store.transition(self.run,'READY',config=cfg,authorization_sha256=digest(self.auth_path.read_bytes()))
        result=self.bridge.execute('delivery',self.payload)
        self.assertFalse(result['remote_verified']);self.assertTrue(result['partial']);self.assertEqual(result['delivery_state'],'PARTIAL_DELIVERY')
        self.assertEqual(len(result['receipts']),1);sha=result['receipts'][0]['commit']
        self.assertEqual(delivery.remote_tip(str(self.remote),'flow/fixture'),sha)
        self.assertEqual(delivery.remote_tip(str(remote),'project/fixture'),git(records,'rev-parse','HEAD'))

    def test_changed_machine_result_cannot_publish(self):
        data=self.bridge.store.get(self.run)['data'];file=Path(data['verification'][0]['result_path']);file.write_text('{}')
        with self.assertRaises(Blocked):self.bridge.execute('verify',self.payload)
        self.assertEqual(delivery.remote_tip(str(self.remote),'flow/fixture'),git(self.source,'rev-parse','HEAD'))

    def test_task_card_acceptance_mismatch_cannot_verify_or_deliver(self):
        mismatch=dict(self.payload,acceptance_sha256=digest(self.acceptance.read_bytes()+b' changed task card'))
        for kind in ('verify','delivery'):
            with self.subTest(kind=kind):
                with self.assertRaises(Blocked):self.bridge.execute(kind,mismatch)
        self.assertEqual(delivery.remote_tip(str(self.remote),'flow/fixture'),git(self.source,'rev-parse','HEAD'))

    def test_missing_task_contract_cannot_reuse_an_old_grant(self):
        payload={k:v for k,v in self.payload.items() if k!='acceptance_sha256'}
        grant=copy.deepcopy(self.bridge.grant);grant['binding'].pop('acceptance_sha256',None)
        save(self.bridge.grant_path,grant)
        with self.assertRaises(Blocked):self.bridge.execute('verify',payload)

    def test_matching_grant_and_payload_cannot_substitute_another_stable_acceptance(self):
        # The unmodified candidate, graph, authorization and verification receipts
        # are valid. Agreement between the two new hashes alone is insufficient.
        verified=self.bridge.execute('verify',self.payload)
        original=self.bridge.store.get(self.run)['data']['acceptance_sha256']
        self.assertEqual(verified['acceptance_sha256'],original)
        other=digest(self.acceptance.read_bytes()+b'\nDifferent task-card acceptance.')
        self.assertNotEqual(other,original)
        payload=dict(self.payload,acceptance_sha256=other)
        grant=copy.deepcopy(self.bridge.grant);grant['binding']['acceptance_sha256']=other
        save(self.bridge.grant_path,grant)
        for kind in ('verify','delivery'):
            with self.subTest(kind=kind):
                with patch('orchestration.controller.deliver_run') as deliver:
                    with self.assertRaisesRegex(Blocked,'acceptance differs from the original Stable run'):
                        self.bridge.execute(kind,payload)
                    deliver.assert_not_called()
        self.assertEqual(self.bridge.store.get(self.run)['state'],'READY')
        self.assertEqual(delivery.remote_tip(str(self.remote),'flow/fixture'),git(self.source,'rev-parse','HEAD'))

    def test_no_external_run_grant_or_open_required_finding_never_publishes(self):
        with self.assertRaises(FileNotFoundError):self.bridge.execute('delivery',dict(self.payload,run='2'*32))
        self.bridge.bind(self.payload);data=self.bridge.store.get(self.run)['data'];review=copy.deepcopy(data['review']);review['report']['findings'][0]['status']='OPEN'
        self.bridge.store.transition(self.run,'READY',review=review)
        with self.assertRaises(Blocked):self.bridge.execute('delivery',self.payload)
        self.assertEqual(delivery.remote_tip(str(self.remote),'flow/fixture'),git(self.source,'rev-parse','HEAD'))
