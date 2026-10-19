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
        r, _, _ = execute([sys.executable, '-c', 'import pathlib;pathlib.Path("file").write_text("changed")'],
                          self.work, self.home, read=[str(self.work)], backend='bwrap')
        self.assertNotEqual(r['exit'], 0);self.assertEqual(p.read_text(), 'fixed')

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


if __name__ == '__main__':
    unittest.main(verbosity=2)
