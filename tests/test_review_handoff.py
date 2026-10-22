"""Offline source-review transport tests; never call models or accept a release."""
from contextlib import redirect_stderr, redirect_stdout
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import review_handoff as h


class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.source = self.base / 'candidate'
        self.source.mkdir()
        (self.source / 'app.py').write_text('print("fixture")\n')
        (self.source / 'docs').mkdir()
        (self.source / 'docs' / '使用.md').write_text('审查用，不是批准。\n')
        self.output = self.base / 'review.zip'

    def pins(self):
        files = h.collect(self.source)
        return h.sha256(h.canonical(h.manifest(files))), h.git_tree(files), len(files)

    def export(self):
        pins = self.pins()
        info = h.export(self.source, self.output, *pins)
        return info, pins

    def rewrite(self, mutate):
        with zipfile.ZipFile(self.output) as z:
            values = [(i, z.read(i)) for i in z.infolist()]
        with zipfile.ZipFile(self.output, 'w') as z:
            for item, data in values:
                for new_item, new_data in mutate(item, data):
                    z.writestr(new_item, new_data)

    def test_roundtrip_is_integrity_not_acceptance(self):
        before = h.collect(self.source)
        info, pins = self.export()
        self.assertEqual(h.verify(self.output, *pins), info)
        self.assertEqual(info['integrity'], 'VERIFIED')
        self.assertEqual(info['review'], 'NOT_PERFORMED')
        self.assertFalse(any(info['authority'].values()))
        self.assertEqual(h.collect(self.source), before)
        self.assertEqual(stat.S_IMODE(self.output.stat().st_mode), 0o600)

    def test_expected_manifest_matches_existing_common_module(self):
        try:
            from orchestration.common import manifest, tree_hash
        except ModuleNotFoundError:
            # Standalone download test still exercises the documented canonical format.
            entries = [{'path': p, 'mode': m, 'size': len(d), 'sha256': h.sha256(d)}
                       for p, (m, d) in sorted(h.collect(self.source).items())]
            self.assertEqual(h.sha256(h.canonical(entries)), self.pins()[0])
        else:
            self.assertEqual(h.manifest(h.collect(self.source)), manifest(self.source))
            self.assertEqual(self.pins()[0], tree_hash(self.source))

    def test_git_tree_matches_git_plumbing_including_directory_sort(self):
        # '.' sorts before the implicit slash of a tree; UTF-8 and executable mode matter.
        (self.source / 'docs.txt').write_bytes(b'not a directory\r\n')
        (self.source / 'executable').write_bytes(b'#!/bin/sh\nexit 0\n')
        (self.source / 'executable').chmod(0o755)
        actual = self.pins()[1]
        env = {'PATH': os.environ['PATH'], 'HOME': str(self.base), 'LANG': 'C.UTF-8',
               'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': '/dev/null'}
        def git(*args):
            return subprocess.run(['git', '-C', str(self.source), *args], env=env,
                capture_output=True, check=True, timeout=10).stdout.decode().strip()
        git('init', '-q')
        git('-c', 'core.autocrlf=false', '-c', 'core.filemode=true', 'add', '--all')
        self.assertEqual(actual, git('write-tree'))
        self.assertEqual(self.pins()[1], actual)

    def test_git_metadata_is_never_read_or_exported(self):
        expected = self.pins()
        (self.source / '.git').symlink_to(self.base / 'missing-auth')
        self.assertEqual(self.pins(), expected)
        self.export()
        with zipfile.ZipFile(self.output) as z:
            self.assertFalse(any('.git' in Path(n).parts for n in z.namelist()))

    def test_ignored_and_untracked_files_are_not_silently_excluded(self):
        (self.source / '.gitignore').write_text('untracked.txt\n')
        (self.source / 'untracked.txt').write_text('must be present')
        _, pins = self.export()
        self.assertEqual(pins[2], 4)
        with zipfile.ZipFile(self.output) as z:
            self.assertEqual(z.read('source/untracked.txt'), b'must be present')

    def test_wrong_candidate_tree_and_count_fail_before_output(self):
        pins = self.pins()
        for index, replacement in ((0, '0'*64), (1, '0'*40), (2, pins[2] + 1)):
            wrong = list(pins); wrong[index] = replacement
            with self.subTest(index=index), self.assertRaises(h.Refused):
                h.export(self.source, self.output, *wrong)
            self.assertFalse(self.output.exists())

    def test_boolean_or_missing_independent_pins_are_refused(self):
        files = h.collect(self.source)
        for values in (('', 'a'*40, 2), ('a'*64, '', 2), ('a'*64, 'b'*40, True)):
            with self.assertRaises(h.Refused):
                h.receipt(files, *values)

    def test_symlink_source_and_ancestors_are_refused(self):
        alias = self.base / 'alias'; alias.symlink_to(self.source, target_is_directory=True)
        for root in (alias, alias / 'docs'):
            with self.assertRaises((h.Refused, OSError)):
                h.collect(root)

    def test_link_and_special_source_files_are_refused_without_opening(self):
        path = self.source / 'unsafe'
        for kind in ('symlink', 'hardlink', 'fifo'):
            if kind == 'symlink': path.symlink_to(self.source / 'app.py')
            elif kind == 'hardlink': os.link(self.source / 'app.py', path)
            else: os.mkfifo(path)
            with self.subTest(kind=kind), self.assertRaises(h.Refused):
                h.collect(self.source)
            path.unlink()

    def test_private_paths_refused_not_silently_removed(self):
        for name in ('auth.json', 'operator.json', '.env.local', 'history.jsonl', 'private.key'):
            p = self.source / name; p.write_text('private fixture')
            with self.subTest(name=name), self.assertRaises(h.Refused):
                h.collect(self.source)
            p.unlink()
        p = self.source / '.claude'; p.mkdir()
        with self.assertRaises(h.Refused): h.collect(self.source)

    def test_secret_error_never_echoes_secret(self):
        secret = 'ghp_' + 'Q9' * 20
        (self.source / 'leak.py').write_text('key = ' + repr(secret))
        with self.assertRaises(h.Refused) as error:
            h.collect(self.source)
        self.assertNotIn(secret, str(error.exception))

    def test_submodule_and_filter_semantics_refused(self):
        for name, content in (('.gitmodules', 'submodule'), ('.gitattributes', '*.x filter=lfs')):
            p = self.source / name; p.write_text(content)
            with self.assertRaises(h.Refused): h.collect(self.source)
            p.unlink()

    def test_size_entry_and_depth_budgets(self):
        for key, limit in (('MAX_FILE', 2), ('MAX_TOTAL', 2), ('MAX_FILES', 1), ('MAX_NODES', 1), ('MAX_DEPTH', 0)):
            with self.subTest(key=key), patch.object(h, key, limit), self.assertRaises(h.Refused):
                h.collect(self.source)

    def test_output_cannot_be_inside_source(self):
        with self.assertRaises(h.Refused):
            h.export(self.source, self.source / 'review.zip', *self.pins())
        self.assertFalse((self.source / 'review.zip').exists())

    def test_output_is_exclusive_and_temporary_file_removed(self):
        self.output.write_bytes(b'existing user file')
        with self.assertRaises(FileExistsError):
            h.export(self.source, self.output, *self.pins())
        self.assertEqual(self.output.read_bytes(), b'existing user file')
        self.assertEqual(list(self.base.glob('.review-handoff-*')), [])

    def test_output_parent_symlink_or_world_writable_refused(self):
        alias = self.base / 'alias'; alias.symlink_to(self.base, target_is_directory=True)
        with self.assertRaises(OSError):
            h.export(self.source, alias / 'review.zip', *self.pins())
        public = self.base / 'public'; public.mkdir(); public.chmod(0o777)
        with self.assertRaises(h.Refused):
            h.export(self.source, public / 'review.zip', *self.pins())

    def test_changed_source_between_snapshots_refused(self):
        original = h.collect
        first = original(self.source)
        second = dict(first, **{'app.py': ('100644', b'new bytes')})
        pins = self.pins()
        with patch.object(h, 'collect', side_effect=[first, second]), self.assertRaises(h.Refused):
            h.export(self.source, self.output, *pins)
        self.assertFalse(self.output.exists())

    def test_export_does_not_execute_candidate_files(self):
        marker = self.base / 'must-not-exist'
        (self.source / 'conftest.py').write_text('raise RuntimeError("must never import")\n')
        (self.source / 'setup.py').write_text(f'open({str(marker)!r}, "w").write("unsafe")\n')
        info, pins = self.export()
        h.verify(self.output, *pins)
        self.assertFalse(marker.exists())

    def test_verify_rejects_modified_source(self):
        _, pins = self.export()
        self.rewrite(lambda i, b: [(i, b'replaced' if i.filename == 'source/app.py' else b)])
        with self.assertRaises(h.Refused): h.verify(self.output, *pins)

    def test_verify_rejects_fabricated_acceptance(self):
        _, pins = self.export()
        def rewrite(i, b):
            if i.filename == 'handoff.json':
                value = json.loads(b); value['review'] = 'ACCEPT'; b = h.canonical(value)
            return [(i, b)]
        self.rewrite(rewrite)
        with self.assertRaises(h.Refused): h.verify(self.output, *pins)

    def test_verify_rejects_duplicate_member(self):
        import warnings
        _, pins = self.export()
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)
            self.rewrite(lambda i, b: [(i,b),(i,b)] if i.filename == 'source/app.py' else [(i,b)])
        with self.assertRaises(h.Refused): h.verify(self.output, *pins)

    def test_verify_rejects_path_traversal_and_links(self):
        for name, mode in (('../escape', 0o100644), ('/absolute', 0o100644),
                           ('source/a/../../escape', 0o100644), ('source/link', 0o120777)):
            if self.output.exists(): self.output.unlink()
            _, pins = self.export()
            def change(i, b):
                if i.filename == 'source/app.py':
                    i.filename = name; i.external_attr = mode << 16
                return [(i,b)]
            self.rewrite(change)
            with self.subTest(name=name), self.assertRaises(h.Refused): h.verify(self.output, *pins)
        self.assertFalse((self.base / 'escape').exists())

    def test_verify_rejects_symlink_bundle_and_invalid_zip(self):
        _, pins = self.export()
        alias = self.base / 'alias.zip'; alias.symlink_to(self.output)
        with self.assertRaises(OSError): h.verify(alias, *pins)
        self.output.write_bytes(b'not a zip')
        with self.assertRaises(zipfile.BadZipFile): h.verify(self.output, *pins)

    def test_missing_receipt_or_manifest_refused(self):
        for missing in ('manifest.json', 'handoff.json'):
            if self.output.exists(): self.output.unlink()
            _, pins = self.export()
            self.rewrite(lambda i, b: [] if i.filename == missing else [(i,b)])
            with self.assertRaises(h.Refused): h.verify(self.output, *pins)

    def test_cli_returns_machine_readable_no_authority_receipt(self):
        pins = self.pins()
        args = ['--expect-sha256', pins[0], '--expect-tree', pins[1], '--expect-files', str(pins[2])]
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            self.assertEqual(h.main(['export', '--source', str(self.source), '--output', str(self.output), *args]), 0)
            self.assertEqual(h.main(['verify', '--bundle', str(self.output), *args]), 0)
        for line in stdout.getvalue().splitlines():
            self.assertEqual(json.loads(line)['review'], 'NOT_PERFORMED')
        with redirect_stderr(io.StringIO()):
            self.assertEqual(h.main(['verify', '--bundle', str(self.output), *args[:-1], '999']), 2)

    def test_empty_and_unsafe_names_are_refused(self):
        for name in ('', '.', '../x', 'a//x', './a', 'a\\x', 'a\nx', 'a/.git/x'):
            with self.subTest(name=name), self.assertRaises(h.Refused): h.relative(name)
        empty = self.base / 'empty'; empty.mkdir()
        with self.assertRaises(h.Refused): h.collect(empty)


if __name__ == '__main__':
    unittest.main()
