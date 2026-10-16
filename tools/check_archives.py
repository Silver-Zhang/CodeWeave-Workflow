#!/usr/bin/env python3
"""Read-only consistency check of project INDEX tables and task archives."""
from __future__ import annotations
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
LINK = re.compile(r"\]\((20\d\d-\d\d/20\d{6}_\d{2}_[^/]+/README\.md)\)")
REQUIRED = ("## 1. 目标与范围", "## 2. 做法与证据",
            "## 3. 决策记录", "## 4. 结论与边界", "## 5. 过程记录")

def check() -> list[str]:
    issues = []
    for project in sorted((ROOT / "projects").iterdir()):
        if not project.is_dir() or project.name.startswith("_"):
            continue
        idx = project / "INDEX.md"
        if not idx.is_file() or not (project / "PROJECT.md").is_file():
            issues.append(f"{project.name}: missing PROJECT.md or INDEX.md")
            continue
        content = idx.read_text(encoding="utf-8")
        refs = set(LINK.findall(content))
        archives = {
            str(p.relative_to(project)) for p in project.glob("20??-??/20??????_*" + "/README.md")
        }
        for ref in sorted(refs - archives):
            issues.append(f"{project.name}: dangling INDEX reference {ref}")
        for ref in sorted(archives - refs):
            issues.append(f"{project.name}: unlisted task {ref}")
        for ref in sorted(archives):
            body = (project / ref).read_text(encoding="utf-8")
            for heading in REQUIRED:
                if heading not in body:
                    issues.append(f"{project.name}/{ref}: missing {heading}")
            if "| 状态 |" not in body or "| 模式 |" not in body:
                issues.append(f"{project.name}/{ref}: missing task metadata")
    return issues

if __name__ == "__main__":
    errs = check()
    for e in errs:
        print("ERROR:", e)
    print(f"Archive check: {len(errs)} issue(s)")
    sys.exit(bool(errs))
