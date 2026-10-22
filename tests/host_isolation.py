"""Required host-only probes. Explicit command; missing bwrap is failure, never Skip."""
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from orchestration.controller import isolation_probe
from orchestration.process import execute


class HostIsolation(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='devflower-host-')
        self.base = Path(self.tmp.name);self.control = self.base / 'control';self.control.mkdir()
        self.work = self.base / 'work';self.work.mkdir();self.home = self.base / 'home'

    def tearDown(self):
        self.tmp.cleanup()

    def test_A05_control_credentials_and_original_git_not_mounted(self):
        paths = []
        for name in ('authorization', 'git-config', 'delivery-credential'):
            p = self.control / name;p.write_text('host-only-fixture');paths.append(p)
        proof = isolation_probe(self.control, self.work, self.home, 'bwrap', paths)
        self.assertTrue(proof['read_and_write_denied'])

    def test_A05_source_is_readonly_for_reviewer(self):
        p = self.work / 'file';p.write_text('fixed')
        control, stdout, _ = execute([sys.executable, '-c', 'import pathlib;assert pathlib.Path("file").read_text()=="fixed";print("started")'],
                                    self.work, self.home, read=[str(self.work)], backend='bwrap')
        self.assertEqual(control['exit'], 0);self.assertEqual(stdout.strip(), b'started')
        r, _, _ = execute([sys.executable, '-c', 'import pathlib;pathlib.Path("file").write_text("changed")'],
                          self.work, self.home, read=[str(self.work)], backend='bwrap')
        self.assertNotEqual(r['exit'], 0);self.assertEqual(p.read_text(), 'fixed')

    def test_DF_R01_protected_descendants_and_symlinks_unreadable(self):
        paths = [Path(__file__).resolve().parents[1] / 'tools/orchestration/controller.py']
        for name in ('authority/config.json', 'original/source.py', 'original/.git/config', 'other-home/private/token'):
            p = self.base / name;p.parent.mkdir(parents=True, exist_ok=True);p.write_text('private fixture')
            paths.append(p)
        for index, path in enumerate(list(paths)):
            alias = self.work / ('alias-' + str(index));alias.symlink_to(path);paths.append(alias)
        for backend in ('landlock', 'bwrap'):
            with self.subTest(backend=backend):
                proof = isolation_probe(self.control, self.work, self.base / ('probe-' + backend), backend, paths)
                self.assertTrue(proof['read_and_write_denied'])

    def test_A06_pid_namespace_cancellation_kills_detached_children(self):
        script = '''import os,time,pathlib
if os.fork()==0:
 os.setsid()
 while True:
  with pathlib.Path('marker').open('a') as f:f.write('x')
  time.sleep(.02)
time.sleep(20)
'''
        r, _, _ = execute([sys.executable, '-c', script], self.work, self.home,
                           write=[str(self.work)], timeout=.3, backend='bwrap')
        self.assertTrue(r['timeout'])
        p = self.work / 'marker'; before = p.read_bytes();time.sleep(.1);self.assertEqual(before, p.read_bytes())

    def test_short_scratch_does_not_erase_persistent_home(self):
        import json
        home = self.base / ('long-' + 'x' * 110) / 'native-home'
        home.mkdir(parents=True);(home / 'session').write_text('persistent')
        code = "import os,socket,json;from pathlib import Path;p=Path(os.environ['TMPDIR']);s=socket.socket(socket.AF_UNIX);s.bind(str(p/'socket'));s.close();print(json.dumps(dict(tmp=str(p),home=os.environ['HOME'])))"
        for backend in ('landlock', 'bwrap'):
            with self.subTest(backend=backend):
                r, out, err = execute([sys.executable, '-c', code], self.work, home,
                                       read=[str(self.work)], backend=backend)
                self.assertEqual(r['exit'], 0, err)
                value = json.loads(out)
                self.assertFalse(Path(value['tmp']).exists())
                self.assertEqual(value['home'], str(home))
                self.assertEqual((home / 'session').read_text(), 'persistent')

    def test_operator_bound_verification_supports_nested_session(self):
        from orchestration.common import tree_hash
        from orchestration.verification import verify
        from studio.usable_verification import specifications
        from studio.usable_graph import node
        python = str(Path(sys.executable).resolve())
        cases = {"default": [dict(id="session", argv=[python, "-I", "-c",
            "import subprocess,json;subprocess.run(['python3','-c','assert 6*7==42'],start_new_session=True,check=True);print(json.dumps(42))"],
            stdin="", expected_json=42, read_paths=[])]}
        config = dict(verification_isolation='bwrap', policy=dict(
            verification=specifications(node('verifier'), cases),
            limits=dict(step_timeout_seconds=10, max_log_bytes=1048576)))
        reports = verify(config, self.work, self.base / 'reports', 'host-fixture', 1,
                         tree_hash(self.work), 'a' * 64)
        self.assertTrue(reports[0]['passed'])
        self.assertEqual(reports[0]['counts'], dict(tests=1, failures=0, errors=0, skipped=0))


if __name__ == '__main__':
    unittest.main(verbosity=2)
