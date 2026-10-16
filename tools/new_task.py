#!/usr/bin/env python3
"""Create a task archive for any registered project; no source-repo operations."""
from __future__ import annotations
import argparse
import datetime as dt
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
VALID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
MARKER = "<!-- TASK_ROWS -->"

def create(project: str, slug: str, mode: str = "B", when: dt.date | None = None) -> Path:
    if not VALID.fullmatch(project) or not VALID.fullmatch(slug):
        raise ValueError("Project and slug must be simple path components (no slashes).")
    if mode not in {"A", "B", "C"}:
        raise ValueError("Mode must be A, B, or C.")
    pdir = ROOT / "projects" / project
    idx = pdir / "INDEX.md"
    if not (pdir / "PROJECT.md").is_file() or not idx.is_file():
        raise FileNotFoundError(f"Register the project and INDEX first: {pdir}")
    text = idx.read_text(encoding="utf-8")
    if text.count(MARKER) != 1:
        raise ValueError("INDEX must contain one TASK_ROWS marker; no files were created.")
    date = when or dt.date.today()
    ym, ymd = date.strftime("%Y-%m"), date.strftime("%Y%m%d")
    month = pdir / ym
    seqs = [
        int(m.group(1))
        for d in month.glob(f"{ymd}_*") if d.is_dir()
        if (m := re.fullmatch(rf"{ymd}_(\d+)_.*", d.name))
    ]
    num = max(seqs, default=0) + 1
    folder = f"{ymd}_{num:02d}_{slug}"
    path = month / folder
    if path.exists():
        raise FileExistsError(path)
    template = (ROOT / "templates" / "TASK.md").read_text(encoding="utf-8")
    template = (template.replace("<TASK_TITLE>", slug)
                .replace("<DATE>", date.isoformat())
                .replace("<PROJECT>", project)
                .replace("<MODE>", mode))
    row = f"| {date.isoformat()} | [{slug}]({ym}/{folder}/README.md) | {mode} | 待设计 | 未提交 |\n"
    month.mkdir(parents=True, exist_ok=True)
    path.mkdir()
    try:
        (path / "README.md").write_text(template, encoding="utf-8")
        idx.write_text(text.replace(MARKER, row + MARKER), encoding="utf-8")
    except BaseException:
        (path / "README.md").unlink(missing_ok=True)
        path.rmdir()
        raise
    return path

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", help="project directory under projects/")
    parser.add_argument("slug", help="short task slug")
    parser.add_argument("--mode", choices="ABC", default="B")
    args = parser.parse_args()
    print(create(args.project, args.slug, args.mode))

if __name__ == "__main__":
    main()
