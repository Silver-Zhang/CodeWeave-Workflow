"""Actual Landlock regressions for descriptor-based workspace/history access.

No ancestor allowlist grants, pre-opened data descriptors, namespace fallback or
mock isolation: each case execs a fresh process through the product backend.
Native records and HTTP transports here are fixtures, not model acceptance.
"""
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'tests')]
from orchestration.common import manifest
from orchestration.process import _execute
from orchestration.sandbox import abi
from test_agent_sessions import append_messages
from test_workspace_sessions import native


class SessionLandlockTests(unittest.TestCase):
    def setUp(self):
        self.assertGreaterEqual(abi(), 6, 'Real Landlock ABI >= 6 required; no unconfined fallback')
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        # Data and runner HOME/TMPDIR are siblings. Granting either invocation
        # directory cannot accidentally authorize the data's ancestors/siblings.
        self.workspace = self.base / 'projects' / 'allowed'
        self.workspace.mkdir(parents=True)
        self.paths = {}
        for provider in ('codex', 'claude'):
            path = native(self.workspace / ('.' + provider), provider, self.workspace)
            append_messages(path, provider)
            self.paths[provider] = str(path)
        self.denied = self.base / 'projects' / 'denied'
        self.denied.mkdir()
        self.secret = native(self.denied / '.claude', 'claude', self.denied)
        append_messages(self.secret, 'claude')
        (self.workspace / 'file-link').symlink_to(self.paths['claude'])
        (self.workspace / 'directory-link').symlink_to(self.workspace / '.claude', target_is_directory=True)
        (self.workspace / 'escape').symlink_to(self.secret)
        self.before = manifest(self.base / 'projects')

    def run_child(self, code, read=None, on_stdout=None):
        run = self.base / 'runner';run.mkdir()
        scratch = run / 'tmp';scratch.mkdir()
        preamble = '''import json,os,sys
from pathlib import Path
sys.path[:0]=[str(Path.cwd()/'tools'),str(Path.cwd()/'tests')]
from studio.session_sources import opened,scan,Refused
from studio.agent_sessions import conversation
from studio.graph import Invalid
p=json.loads(sys.argv[1]);workspace=Path(p['workspace']);paths=p['paths']
def denied(operation):
 try:operation()
 except (OSError,Invalid,Refused):pass
 else:raise AssertionError('Unauthorized access succeeded')
def listing(path):
 with opened(path,directory=True) as fd:return os.listdir(fd)
'''
        args = dict(workspace=str(self.workspace), paths=self.paths, secret=str(self.secret), denied=str(self.denied))
        result, stdout, stderr = _execute(
            [sys.executable, '-B', '-I', '-c', preamble + code, json.dumps(args)],
            ROOT, run / 'home', [str(ROOT), *(read if read is not None else [str(self.workspace)])],
            [], 30, 1048576, None, None, '', None, True, 'landlock', None, (), str(scratch), on_stdout)
        self.assertEqual(result['exit'], 0, stderr.decode('utf-8', 'replace'))
        self.assertFalse(any(result[k] for k in ('timeout', 'overflow', 'cancelled')), result)
        self.assertEqual(manifest(self.base / 'projects'), self.before, 'Readonly native/source data changed')
        return stdout

    def test_workspace_discovery_and_visible_history_without_ancestor_read_access(self):
        self.run_child('''
assert '.claude' in listing(workspace)
for provider,path in paths.items():
 rows,coverage=scan(workspace/('.'+provider)/('sessions' if provider=='codex' else 'projects'),provider)
 assert coverage['status']=='complete' and len(rows)==1,(rows,coverage)
 assert conversation(provider,path,query='HeLLo')==[dict(role='user',text='VISIBLE hello')]
 text=json.dumps(conversation(provider,path))
 assert 'VISIBLE answer' in text
 assert not any(secret in text for secret in ('HIDDEN_REASONING','PRIVATE_COMMAND','PRIVATE_TOOL_RESULT','sk-fixture-'))
 with opened(path) as fd:assert os.read(fd,1)
denied(lambda:os.open(workspace/'file-link',os.O_WRONLY))
''')

    def test_single_file_grant_does_not_require_reading_any_parent(self):
        self.run_child('''
path=paths['claude']
assert conversation('claude',path,query='hello')==[dict(role='user',text='VISIBLE hello')]
denied(lambda:listing(Path(path).parent))
denied(lambda:listing(workspace))
denied(lambda:conversation('codex',paths['codex']))
''', read=[self.paths['claude']])

    def test_root_parents_siblings_and_native_writes_remain_denied(self):
        self.run_child('''
for path in ('/',workspace.parent,workspace.parent.parent,p['denied']):
 denied(lambda:os.open(path,os.O_RDONLY|os.O_DIRECTORY))
 denied(lambda:listing(path))
denied(lambda:Path(p['secret']).read_bytes())
denied(lambda:conversation('claude',p['secret']))
denied(lambda:Path(paths['claude']).write_text('unauthorized native overwrite'))
denied(lambda:os.open(workspace/'new-source',os.O_WRONLY|os.O_CREAT,0o600))
''')

    def test_symlink_files_and_ancestors_stay_refused_even_when_target_is_allowed(self):
        self.run_child('''
for path in (workspace/'file-link',workspace/'escape',
 workspace/'directory-link'/Path(paths['claude']).relative_to(workspace/'.claude')):
 denied(lambda:conversation('claude',path))
denied(lambda:listing(workspace/'directory-link'))
''')

    def test_directory_replacement_cannot_redirect_pinned_lookup(self):
        # The concurrent owner swaps an approved directory after its metadata
        # descriptor is acquired. Traversal must keep that original descriptor.
        # Only the concurrent parent mutates this disposable fixture; the
        # restricted child receives no write grant for either directory.
        parent = self.workspace / 'pinned';parent.mkdir()
        (parent / 'original').write_text('original')
        self.before = manifest(self.base / 'projects')
        output = bytearray();swaps = []
        def replace(chunk):
            output.extend(chunk)
            if b'PINNED\n' in output and not swaps:
                parent.rename(self.workspace / 'pinned-original')
                parent.symlink_to(self.denied, target_is_directory=True)
                self.before = manifest(self.base / 'projects')
                swaps.append(True)
                (self.base / 'runner/tmp/swapped').touch()
        self.run_child('''
from unittest.mock import patch
import time
real_open=os.open
def replace_after_pin(name,flags,*args,**kwargs):
 fd=real_open(name,flags,*args,**kwargs)
 if name=='pinned' and flags & os.O_PATH:
  # The parent replaces the pathname with an unauthorized sibling symlink.
  # Keep this real descriptor and wait until the replacement is complete.
  print('PINNED',flush=True)
  deadline=time.monotonic()+5
  while not (Path(os.environ['TMPDIR'])/'swapped').exists():
   assert time.monotonic()<deadline,'Parent replacement did not finish'
   time.sleep(.01)
 return fd
with patch('studio.session_sources.os.open',side_effect=replace_after_pin):
 assert listing(workspace/'pinned')==['original']
denied(lambda:listing(workspace/'pinned'))
''', on_stdout=replace)
        self.assertEqual(swaps, [True])

    def test_http_profile_history_visibility_and_canvas_boundaries_under_landlock(self):
        self.run_child('''
import unittest
names=[
 'test_agent_sessions.CenterTests.test_http_registered_roots_keep_same_uuid_histories_and_visibility_independent',
 'test_agent_sessions.CenterTests.test_http_native_delete_archive_and_arbitrary_argv_are_denied',
 'test_agent_sessions.CenterTests.test_transcript_cannot_disclose_messages_from_a_different_workspace_cwd',
 'test_agent_sessions.VisibleHistoryTests.test_all_identity_components_participate',
 'test_agent_sessions.CenterTests.test_v2_provider_swaps_bind_actual_adapter_and_keep_mandatory_gates',
 'test_studio_workflow.WorkflowTests.test_http_workflow_identity_and_empty_answer_server_gate',
 'test_agent_sessions.CenterTests.test_resume_preview_preserves_exact_profile_cwd_uuid_and_tools']
result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromNames(names))
assert result.wasSuccessful()
''')


if __name__ == '__main__':
    unittest.main(verbosity=2)
