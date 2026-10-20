#!/usr/bin/env python3
"""Branch-scoped workflow records. Uses stdlib only; never changes source repositories."""
from __future__ import annotations
import argparse
from contextlib import contextmanager
from datetime import datetime, date, timezone, timedelta
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SLUG = re.compile(r"[a-z0-9][a-z0-9_-]{0,79}\Z")
ID = re.compile(r"(20\d{6})_(\d{2,})_([a-z0-9][a-z0-9_-]{0,79})\Z")
STATES = {"待设计", "待决策", "实施中", "待验证", "待复核", "已完成", "已关闭", "阻塞"}
HEADINGS = ("## 1. 目标与范围", "## 2. 做法与证据", "## 3. 决策记录", "## 4. 结论与边界", "## 5. 过程记录")


def slug(value: str) -> str:
    if not SLUG.fullmatch(value):
        raise ValueError("Use a lowercase slug of letters, digits, _ or - (no path segments).")
    return value


def safe(root: Path, relative: str) -> Path:
    path = root / relative
    if not path.is_relative_to(root) or '..' in Path(relative).parts or Path(relative).is_absolute():
        raise ValueError("Path escapes workflow root")
    for parent in (path, *path.parents):
        if parent == root:
            break
        if parent.is_symlink():
            raise ValueError(f"Symlink is not a writable workflow path: {relative}")
    return path


def git(root: Path, *args: str) -> str:
    env = dict(os.environ, GIT_OPTIONAL_LOCKS='0')
    return subprocess.check_output(['git', '-C', str(root), *args], env=env, text=True, stderr=subprocess.PIPE).strip()


def guard(root: Path, name: str) -> None:
    if Path(git(root, 'rev-parse', '--show-toplevel')).resolve() != root.resolve():
        raise ValueError("Run in this workflow repository, not a parent workspace")
    branch = git(root, 'symbolic-ref', '--quiet', '--short', 'HEAD')
    if branch != f'project/{name}' and not branch.startswith(f'work/{name}/'):
        raise ValueError(f"Project {name} requires project/{name} or work/{name}/..., not {branch}")


def atomic(path: Path, text: str) -> None:
    fd, tmp = tempfile.mkstemp(prefix='.devflower-tmp-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


@contextmanager
def lock(root: Path):
    path = safe(root, '.devflower.lock')
    path.mkdir()  # Existing lock fails closed; never remove another process's lock.
    try:
        yield
    finally:
        path.rmdir()


def read_json(path: Path) -> dict:
    data = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(data, dict):
        raise ValueError(f"Expected object: {path}")
    return data


def dump(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2) + '\n'


def project(root: Path) -> dict:
    data = read_json(safe(root, 'project/project.json'))
    slug(data['slug'])
    if data.get('schema_version') != 1:
        raise ValueError('Unsupported project schema')
    return data


def records(root: Path) -> list[tuple[Path, dict]]:
    base = safe(root, 'project/tasks')
    output = []
    seen = set()
    if not base.is_dir():
        raise ValueError('Missing project/tasks')
    # Reject symlinks even if they point inside the checkout; do not follow them.
    if any(p.is_symlink() for p in base.rglob('*')):
        raise ValueError('Symlink in task records')
    for path in sorted(base.glob('*/*/task.json')):
        data = read_json(path)
        identity = data.get('id', '')
        match = ID.fullmatch(identity)
        if not match or identity != path.parent.name or identity in seen:
            raise ValueError(f'Invalid or duplicate task id: {identity}')
        d = date.fromisoformat(data['date'])
        if d.strftime('%Y%m%d') != match[1] or path.parent.parent.name != d.strftime('%Y-%m'):
            raise ValueError(f'Task date/path mismatch: {identity}')
        if data.get('schema_version') != 1 or data.get('mode') not in ('A', 'B', 'C') or data.get('status') not in STATES:
            raise ValueError(f'Invalid task metadata: {identity}')
        if not isinstance(data.get('source_refs', []), list):
            raise ValueError(f'Invalid source_refs: {identity}')
        seen.add(identity)
        output.append((path, data))
    task_dirs = {p.parent for p in base.glob('*/*/README.md')}
    if task_dirs != {p.parent for p, _ in output}:
        raise ValueError('README/task.json pairing mismatch')
    folders = {p for p in base.glob('*/*') if p.is_dir()}
    if folders != {p.parent for p, _ in output}:
        raise ValueError('Orphan task directory without metadata and README')
    return sorted(output, key=lambda item: (item[1]['date'], int(ID.fullmatch(item[1]['id'])[2])))


def index_text(root: Path) -> str:
    rows = ['# 任务台账（自动生成）', '', '模式与状态来自 task.json；结论、证据和授权见任务 README。', '',
            '| 日期 | 任务 | 模式 | 状态 |', '|---|---|---|---|']
    for path, data in reversed(records(root)):
        link = str((path.parent / 'README.md').relative_to(root / 'project'))
        rows.append(f"| {data['date']} | [{data['id']}]({link}) | {data['mode']} | {data['status']} |")
    return '\n'.join(rows) + '\n'


def initialize(root: Path, name: str) -> None:
    slug(name)
    guard(root, name)
    with lock(root):
        dest = safe(root, 'project')
        if dest.exists():
            raise FileExistsError('project already exists; no overwrite')
        tmp = Path(tempfile.mkdtemp(prefix='.devflower-tmp-', dir=root))
        try:
            (tmp / 'tasks').mkdir()
            (tmp / 'plans').mkdir()
            (tmp / 'tasks' / '.gitkeep').write_text('', encoding='utf-8')
            (tmp / 'plans' / '.gitkeep').write_text('', encoding='utf-8')
            (tmp / 'project.json').write_text(dump({'schema_version': 1, 'slug': name, 'framework_base': git(root, 'rev-parse', 'HEAD')}), encoding='utf-8')
            (tmp / 'PROJECT.md').write_text((root / 'templates/PROJECT.md').read_text(encoding='utf-8').replace('<PROJECT>', name), encoding='utf-8')
            (tmp / 'STATUS.md').write_text('# 当前状态\n\n项目实例已创建；尚未授权任何实现。下一步明确基线、目标和首项任务。\n', encoding='utf-8')
            (tmp / 'AGENT_CONTEXT.md').write_text('# 接手入口\n\n先读 STATUS.md 与 PROJECT.md，再定位 INDEX.md 中的当前任务 §1/§3/§4。不通读历史。\n', encoding='utf-8')
            # Complete the initial index before publishing the project directory.
            empty_index = '# 任务台账（自动生成）\n\n模式与状态来自 task.json；结论、证据和授权见任务 README。\n\n| 日期 | 任务 | 模式 | 状态 |\n|---|---|---|---|\n'
            atomic(tmp / 'INDEX.md', empty_index)
            guard(root, name)
            os.rename(tmp, dest)
        except BaseException:
            if tmp.exists():
                shutil.rmtree(tmp)
            raise


def new_task(root: Path, name: str, mode: str, day: date) -> Path:
    slug(name)
    if mode not in ('A', 'B', 'C') or not 2000 <= day.year <= 2099:
        raise ValueError('Invalid mode or unsupported date')
    owner = project(root)['slug']
    guard(root, owner)
    with lock(root):
        old_index = safe(root, 'project/INDEX.md').read_text(encoding='utf-8')
        if old_index != index_text(root):
            raise ValueError('INDEX is stale; inspect records and run index before creating a task')
        month = safe(root, 'project/tasks/' + day.strftime('%Y-%m'))
        prefix = day.strftime('%Y%m%d')
        previous = [int(ID.fullmatch(d['id'])[2]) for _, d in records(root) if d['date'] == day.isoformat()]
        identity = f"{prefix}_{max(previous, default=0) + 1:02d}_{name}"
        month.mkdir(parents=True, exist_ok=True)
        dest = month / identity
        dest.mkdir()  # Never replace an existing task.
        try:
            body = (root / 'templates/TASK.md').read_text(encoding='utf-8').replace('<TASK_TITLE>', name).replace('<TASK_ID>', identity).replace('<DATE>', day.isoformat())
            atomic(dest / 'README.md', body)
            atomic(dest / 'task.json', dump({'schema_version': 1, 'id': identity, 'date': day.isoformat(), 'mode': mode, 'status': '待设计', 'source_refs': []}))
            guard(root, owner)
            atomic(root / 'project/INDEX.md', index_text(root))
        except BaseException:
            shutil.rmtree(dest)
            raise
        return dest


def check(root: Path, baseline: bool = False) -> list[str]:
    errors = []
    for path in ('README.md', 'AGENTS.md', 'WORKFLOW.md', 'templates/TASK.md', 'templates/PROJECT.md'):
        if not safe(root, path).is_file():
            errors.append('Missing ' + path)
    if baseline:
        for path in ('project', 'projects', 'STATUS.md', 'INDEX.md', 'tasks', 'plans'):
            if safe(root, path).exists():
                errors.append('Project-specific root path in baseline: ' + path)
        return errors
    try:
        project(root)
        for path in ('PROJECT.md', 'STATUS.md', 'AGENT_CONTEXT.md', 'INDEX.md'):
            if not safe(root, 'project/' + path).is_file():
                errors.append('Missing project/' + path)
        for path, data in records(root):
            body = (path.parent / 'README.md').read_text(encoding='utf-8')
            for heading in HEADINGS:
                if heading not in body:
                    errors.append(f"{data['id']}: missing {heading}")
        if safe(root, 'project/INDEX.md').read_text(encoding='utf-8') != index_text(root):
            errors.append('INDEX differs from task metadata; inspect and run index')
    except (ValueError, KeyError, OSError, TypeError) as exc:
        errors.append(str(exc))
    return errors


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] in {'doctor', 'run', 'status', 'resume', 'cancel', 'audit', 'deliver'}:
        from orchestration.cli import main as orchestrate
        return orchestrate()
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='cmd', required=True)
    init = sub.add_parser('init'); init.add_argument('slug')
    new = sub.add_parser('new'); new.add_argument('slug'); new.add_argument('--mode', choices='ABC', default='B')
    new.add_argument('--date', type=date.fromisoformat, default=datetime.now(timezone(timedelta(hours=8))).date())
    sub.add_parser('index')
    validate = sub.add_parser('check'); validate.add_argument('--baseline', action='store_true')
    args = parser.parse_args()
    try:
        if args.cmd == 'init':
            initialize(ROOT, args.slug)
        elif args.cmd == 'new':
            print(new_task(ROOT, args.slug, args.mode, args.date))
        elif args.cmd == 'index':
            guard(ROOT, project(ROOT)['slug'])
            with lock(ROOT):
                atomic(safe(ROOT, 'project/INDEX.md'), index_text(ROOT))
        else:
            errors = check(ROOT, args.baseline)
            print('\n'.join(errors) if errors else 'OK: structural checks only; not an approval or correctness proof')
            return int(bool(errors))
        return 0
    except (ValueError, OSError, KeyError, TypeError, subprocess.CalledProcessError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
