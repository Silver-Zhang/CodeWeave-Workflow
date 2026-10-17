"""Failure and ordering regression tests for the workflow helper."""
import unittest
from unittest.mock import patch
import test_devflower as original


df = original.df


class FailureModeTests(unittest.TestCase):
    setUp = original.WorkflowTests.setUp
    tearDown = original.WorkflowTests.tearDown
    git = original.WorkflowTests.git
    init = original.WorkflowTests.init
    new = original.WorkflowTests.new

    def test_initialize_failure_does_not_publish_partial_project(self):
        self.git('switch', '-c', 'project/demo')
        with patch.object(df, 'atomic', side_effect=OSError('simulated write failure')):
            with self.assertRaises(OSError):
                df.initialize(self.root, 'demo')
        self.assertFalse((self.root / 'project').exists())
        self.assertEqual(list(self.root.glob('.devflower-tmp-*')), [])
        self.assertFalse((self.root / '.devflower.lock').exists())

    def test_numeric_index_order(self):
        self.init()
        path = self.new()
        data = df.read_json(path / 'task.json')
        data['id'] = data['id'].replace('_01_', '_99_')
        (path / 'task.json').write_text(df.dump(data), encoding='utf-8')
        path.rename(path.with_name(data['id']))
        df.atomic(self.root / 'project/INDEX.md', df.index_text(self.root))
        self.new('hundred')
        index = df.index_text(self.root)
        self.assertLess(index.index('_100_'), index.index('_99_'))

    def test_orphan_task_directory_rejected(self):
        self.init()
        (self.root / 'project/tasks/2026-10/20261018_01_orphan').mkdir(parents=True)
        self.assertTrue(df.check(self.root))

    def test_index_failure_keeps_previous_records(self):
        self.init(); first = self.new()
        previous = (self.root / 'project/INDEX.md').read_bytes()
        actual = df.atomic
        def fail_index(path, content):
            if path.name == 'INDEX.md':
                raise OSError('index update failed')
            actual(path, content)
        with patch.object(df, 'atomic', side_effect=fail_index):
            with self.assertRaises(OSError):
                self.new('failed')
        self.assertTrue(first.is_dir())
        self.assertEqual(previous, (self.root / 'project/INDEX.md').read_bytes())
        self.assertEqual(df.check(self.root), [])


if __name__ == '__main__':
    unittest.main()
