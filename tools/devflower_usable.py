#!/usr/bin/env python3
"""Launch an externally accepted Stable release; never promote this candidate."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import sys
import time

sys.dont_write_bytecode = True
from orchestration.common import Blocked, digest, save, load, tree_hash
from orchestration.store import Store, lease, alive
from orchestration.trust import TrustedRelease


def worker(args):
    from studio.usable_runtime import Runtime
    from orchestration.controller import resume, deliver_run
    runtime = Runtime(args.operator, args.operator_sha256)
    store = Store(runtime.control)
    try:
        result = resume(store, args.run)
        if result["state"] in ("READY", "PARTIAL_DELIVERY") and result["data"]["config"]["policy"]["delivery"]["push"]:
            deliver_run(store, args.run, github=runtime.github)
    finally:
        store.db.close()


def configure(args):
    from studio.usable_runtime import Runtime
    trust = TrustedRelease(args.stable_approval, args.stable_sha256)
    authority = Path(args.authority).resolve()
    operator = authority / "operator.json"
    if operator.exists():
        raise Blocked("Operator configuration already exists; use serve with its pinned hash")
    from orchestration.controller import overlaps
    private = [authority, Path(args.workspace).resolve(), Path(args.native_homes).resolve()]
    protected = [trust.root, trust.record, Path(args.gh_config).resolve(),
                 Path(args.codex_credential).resolve(), Path(args.claude_credential).resolve()]
    if any(p.exists() for p in private):
        raise Blocked("Initial setup requires three new private directories")
    if any(overlaps(a, b) for i, a in enumerate(private) for b in private[i+1:] + protected):
        raise Blocked("Private runtime directories overlap protected input")
    profiles = {}
    dependencies = {}
    dependency_trees = {}
    for provider in ("codex", "claude"):
        executable = Path(getattr(args, provider)).resolve()
        credential = Path(getattr(args, provider + "_credential")).resolve()
        if not executable.is_file() or not credential.is_file():
            raise Blocked("Explicit executable and existing native credential file required")
        dependencies[str(executable)] = digest(executable.read_bytes())
        dependencies[str(credential)] = digest(credential.read_bytes())
        read_paths = [str(executable)]
        if provider == "codex":
            # Native JS distribution resolves its bundled architecture package.
            dependency = Path(args.codex_dependencies).resolve()
            if not dependency.is_dir():
                raise Blocked("Codex dependency directory is required")
            read_paths.append(str(dependency))
            dependency_trees[str(dependency)] = tree_hash(dependency)
        profiles["default-" + provider] = dict(provider=provider, executable=str(executable),
            model=getattr(args, provider + "_model"), effort=getattr(args, provider + "_effort"),
            read_paths=read_paths, readonly_files=[[str(credential), ".codex/auth.json" if provider == "codex" else ".claude/settings.json"]])
    if args.claude_buffered_tools:
        profiles["default-claude"]["buffered_tool_transport"] = True
    from studio.usable_verification import validate_profiles
    verification_profiles = validate_profiles(load(args.verification_profiles))
    if 'default' not in verification_profiles:
        raise Blocked('A default operator verification profile is required')
    for cases in verification_profiles.values():
        for case in cases:
            case['argv'][0] = str(Path(case['argv'][0]).resolve())
            case['read_paths'] = [str(Path(value).resolve()) for value in case['read_paths']]
            for value in [case['argv'][0], *case['read_paths']]:
                path = Path(value)
                if not path.is_file() or path.is_symlink() or any(overlaps(path, x) for x in private + protected):
                    raise Blocked('Verifier dependencies must be separate explicit regular files')
                dependencies[str(path)] = digest(path.read_bytes())
    gh = Path(args.gh).resolve()
    dependencies[str(gh)] = digest(gh.read_bytes())
    value = dict(version=1, stable=trust.binding(), authority=str(authority),
                 storage=str(Path(args.workspace).resolve()), native=str(Path(args.native_homes).resolve()),
                 allowed_roots=[str(Path(p).resolve()) for p in args.allow_root],
                 profiles=profiles, dependencies=dependencies, dependency_trees=dependency_trees,
                 verification_isolation=args.verification_isolation, verification_profiles=verification_profiles,
                 github=dict(executable=str(gh), config_dir=str(Path(args.gh_config).resolve()), repository=args.repository))
    authority.mkdir(parents=True, exist_ok=True, mode=0o700)
    save(operator, value)
    operator.chmod(0o600)
    sha = digest(operator.read_bytes())
    runtime = Runtime(operator, sha)
    print(json.dumps(dict(operator=str(operator), operator_sha256=sha)))
    return runtime


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    setup = commands.add_parser("configure", help="Operator-only setup of an externally accepted release")
    for name in ("stable-approval", "stable-sha256", "authority", "workspace", "native-homes", "codex",
                 "codex-credential", "codex-dependencies", "codex-model", "codex-effort", "claude",
                 "claude-credential", "claude-model", "claude-effort", "gh", "gh-config", "repository", "verification-profiles"):
        setup.add_argument("--" + name, required=True)
    setup.add_argument("--verification-isolation", choices=("landlock", "bwrap"), default="landlock",
                       help="Operator-bound test backend; bwrap supports supervised child sessions")
    setup.add_argument("--allow-root", action="append", required=True)
    setup.add_argument("--claude-buffered-tools", action="store_true",
                       help="Explicit compatibility for a gateway that loses parallel streaming tool inputs")
    for name in ("serve", "worker"):
        command = commands.add_parser(name)
        command.add_argument("--operator", required=True)
        command.add_argument("--operator-sha256", required=True)
        if name == "serve":
            command.add_argument("--port", type=int, default=8765)
        else:
            command.add_argument("--run", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "configure":
            configure(args)
        elif args.command == "worker":
            worker(args)
        else:
            from studio.usable_runtime import Runtime
            from studio.usable_server import serve
            runtime = Runtime(args.operator, args.operator_sha256)
            with lease(runtime.authority / "service.lock"):
                serve(runtime, args.port)
    except (Blocked, OSError, ValueError) as exc:
        print("BLOCKED: " + str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
