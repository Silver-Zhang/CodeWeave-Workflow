"""Isolated real-Git tests; never touch production or remote repositories."""
import importlib.util
import json
from datetime import date
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

BASE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('devflower', BASE / 'tools/devflower.py')
df = importlib.util.module_from_spec(spec)
spec.loader.exec_module(df)


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        for path in ('README.md', 'AGENTS.md', 'WORKFLOW.md', 'templates/TASK.md', 'templates/PROJECT.md'):
            target = self.root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(BASE / path, target)
        self.git('init', '-b', 'main')
        self.git('config', 'user.name', 'Fixture')
        self.git('config', 'user.email', 'fixture@example.invalid')
        self.git('add', '.')
        self.git('-c', 'commit.gpgsign=false', 'commit', '-m', 'fixture')

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.root), *args], text=True, stderr=subprocess.PIPE).strip()

    def init(self, name='demo'):
        self.git('switch', '-c', 'project/' + name)
        df.initialize(self.root, name)

    def new(self, name='smoke', day=date(2026, 10, 18)):
        return df.new_task(self.root, name, 'B', day)

    def test_baseline_clean(self):
        self.assertEqual(df.check(self.root, True), [])

    def test_refuse_main(self):
        with self.assertRaises(ValueError):
            df.initialize(self.root, 'demo')
        self.assertFalse((self.root / 'project').exists())

    def test_initialize(self):
        self.init()
        self.assertEqual(df.check(self.root), [])
        self.assertEqual(df.project(self.root)['framework_base'], self.git('rev-parse', 'HEAD'))

    def test_no_overwrite(self):
        self.init()
        with self.assertRaises(FileExistsError):
            df.initialize(self.root, 'demo')
        self.assertEqual(df.check(self.root), [])

    def test_invalid_slug(self):
        for name in ('../x', '/tmp/x', 'x/y', '', '.hidden', 'x|y', 'x\ny'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                df.slug(name)

    def test_two_tasks(self):
        self.init()
        first, second = self.new(), self.new('next')
        self.assertIn('_01_', first.name)
        self.assertIn('_02_', second.name)
        self.assertEqual(df.check(self.root), [])

    def test_sequence_above_99(self):
        self.init()
        first = self.new()
        data = df.read_json(first / 'task.json')
        data['id'] = data['id'].replace('_01_', '_99_')
        (first / 'task.json').write_text(df.dump(data), encoding='utf-8')
        first.rename(first.with_name(data['id']))
        df.atomic(self.root / 'project/INDEX.md', df.index_text(self.root))
        self.assertIn('_100_', self.new('hundred').name)
        self.assertEqual(df.check(self.root), [])

    def test_stale_index_detected(self):
        self.init()
        path = self.new()
        data = df.read_json(path / 'task.json'); data['status'] = '待验证'
        (path / 'task.json').write_text(df.dump(data), encoding='utf-8')
        self.assertTrue(df.check(self.root))
        with self.assertRaises(ValueError):
            self.new('blocked')
        df.atomic(self.root / 'project/INDEX.md', df.index_text(self.root))
        self.assertEqual(df.check(self.root), [])

    def test_invalid_state(self):
        self.init()
        path = self.new()
        data = df.read_json(path / 'task.json'); data['status'] = 'probably fine'
        (path / 'task.json').write_text(df.dump(data), encoding='utf-8')
        self.assertTrue(df.check(self.root))

    def test_wrong_project_branch(self):
        self.init()
        self.git('switch', '-c', 'project/other')
        with self.assertRaises(ValueError):
            self.new()

    def test_work_branch(self):
        self.init()
        self.git('switch', '-c', 'work/demo/smoke')
        self.new()
        self.assertEqual(df.check(self.root), [])

    def test_symlink_rejected(self):
        self.git('switch', '-c', 'project/demo')
        (self.root / 'project').symlink_to(self.root / 'elsewhere', target_is_directory=True)
        with self.assertRaises(ValueError):
            df.initialize(self.root, 'demo')

    def test_locked_no_write(self):
        self.init()
        (self.root / '.devflower.lock').mkdir()
        with self.assertRaises(FileExistsError):
            self.new()
        self.assertTrue((self.root / '.devflower.lock').is_dir())

    def test_failed_write_removes_only_new_task(self):
        self.init()
        first = self.new()
        before = (self.root / 'project/INDEX.md').read_bytes()
        with patch.object(df, 'atomic', side_effect=OSError('simulated write failure')):
            with self.assertRaises(OSError):
                self.new('failed')
        self.assertTrue(first.is_dir())
        self.assertEqual(before, (self.root / 'project/INDEX.md').read_bytes())
        self.assertEqual(df.check(self.root), [])

    def test_missing_heading(self):
        self.init()
        path = self.new()
        text = (path / 'README.md').read_text(encoding='utf-8').replace('## 4. 结论与边界', 'removed')
        (path / 'README.md').write_text(text, encoding='utf-8')
        self.assertTrue(df.check(self.root))

    def test_missing_metadata(self):
        self.init()
        path = self.new()
        (path / 'task.json').unlink()
        self.assertTrue(df.check(self.root))

    def test_readonly_check(self):
        self.init(); self.new()
        before = {str(p): p.read_bytes() for p in (self.root / 'project').rglob('*') if p.is_file()}
        df.check(self.root)
        after = {str(p): p.read_bytes() for p in (self.root / 'project').rglob('*') if p.is_file()}
        self.assertEqual(before, after)

    def test_baseline_rejects_project(self):
        self.init()
        self.assertTrue(df.check(self.root, True))

    def test_detached_refused(self):
        self.init(); self.git('switch', '--detach', 'HEAD')
        with self.assertRaises(subprocess.CalledProcessError):
            self.new()

    def test_source_and_history_unchanged(self):
        head = self.git('rev-parse', 'HEAD')
        self.init(); self.new()
        self.assertEqual(self.git('rev-parse', 'HEAD'), head)
        self.assertEqual(self.git('diff', '--cached', '--name-only'), '')


if __name__ == '__main__':
    unittest.main()
