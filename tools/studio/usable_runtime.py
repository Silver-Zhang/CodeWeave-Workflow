"""Stable application operations. The browser supplies data, never commands."""
from __future__ import annotations
from contextlib import closing
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import threading

from orchestration.common import Blocked, canonical, controller_hash, digest, git, identity, load, save, tree_hash
from orchestration.contracts import config_check
from orchestration.controller import start, binding_check, overlaps
from orchestration.github_delivery import GitHub
from orchestration.store import Store, alive, process_identity, lease
from orchestration.trust import TrustedRelease
from .graph import Invalid
from .projection import Reader, Unavailable
from .usable_graph import compile_plan, template
from .usable_store import Storage
from .usable_verification import specifications, validate_profiles
from .workspace_sessions import WorkspaceSessions

ROOT = Path(__file__).resolve().parents[2]


class Runtime:
    def __init__(self, operator_file, expected_sha256):
        self.operator_file = Path(operator_file).resolve()
        self.operator_sha256 = expected_sha256
        if digest(self.operator_file.read_bytes()) != expected_sha256:
            raise Blocked("Operator configuration changed")
        self.operator = load(self.operator_file)
        self.trust = TrustedRelease.bound(self.operator["stable"])
        self.authority = Path(self.operator["authority"]).resolve()
        self.storage = Path(self.operator["storage"]).resolve()
        self.native = Path(self.operator["native"]).resolve()
        self.control = self.authority / "control"
        self.lock = threading.RLock()
        self.children = {}
        self.github = GitHub(**self.operator["github"])
        paths = [self.authority, self.storage, self.native, ROOT, self.github.config_dir, self.trust.record]
        if any(overlaps(a, b) for i, a in enumerate(paths) for b in paths[i + 1:]):
            raise Blocked("Authority, Studio storage, Stable, native homes and delivery credentials must be disjoint")
        if not self.operator_file.is_relative_to(self.authority):
            raise Blocked("Operator configuration must be protected by the authority directory")
        for p in (self.authority, self.storage, self.native):
            p.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.db = Storage(self.storage)
        self.check_operator()
        validate_profiles(self.operator.get("verification_profiles", {}))
        protected = [self.authority, self.storage, self.native, ROOT, self.github.config_dir, self.trust.record]
        for profile in self.operator["profiles"].values():
            for path in profile["read_paths"]:
                if any(overlaps(path, value) for value in protected):
                    raise Blocked("Runtime dependency exposes protected authority")
        protected += [src for profile in self.operator["profiles"].values() for src, _ in profile["readonly_files"]]
        for cases in self.operator.get("verification_profiles", {}).values():
            for case in cases:
                for path in [case['argv'][0], *case['read_paths']]:
                    p = Path(path)
                    if any(overlaps(p, value) for value in protected) or not p.is_file() or p.is_symlink():
                        raise Blocked("Verifier dependency exposes authority or is not a regular file")
                    if self.operator['dependencies'].get(str(p)) != digest(p.read_bytes()):
                        raise Blocked("Verifier dependency must be pinned by the operator")

    def check_operator(self):
        if digest(self.operator_file.read_bytes()) != self.operator_sha256:
            raise Blocked("Operator binding changed after startup")
        self.trust.verify()
        for p, sha in self.operator["dependencies"].items():
            if not Path(p).is_file() or digest(Path(p).read_bytes()) != sha:
                raise Blocked("Approved executable or native configuration changed")
        for p, sha in self.operator.get("dependency_trees", {}).items():
            if not Path(p).is_dir() or tree_hash(p) != sha:
                raise Blocked("Approved CLI dependency tree changed")

    def project(self, key):
        row = self.db.get("workspace", key)
        self.validate_source(row["path"])
        return row

    def validate_source(self, path):
        p = Path(path)
        if not p.is_absolute() or any(ord(x) < 32 for x in str(p)):
            raise Invalid("Enter an absolute local project path")
        p = p.resolve()
        if not any(p.is_relative_to(Path(root).resolve()) for root in self.operator["allowed_roots"]):
            raise Blocked("Workspace is outside operator-approved roots")
        for protected in (self.authority, self.storage, self.native, ROOT, self.github.config_dir, self.trust.record):
            if overlaps(p, protected):
                raise Blocked("Workspace overlaps trusted runtime data")
        for profile in self.operator["profiles"].values():
            for src, _ in profile["readonly_files"]:
                if overlaps(p, src):
                    raise Blocked("Workspace overlaps native authentication")
        actual = identity(p)
        remote = git(p, "remote", "get-url", "origin")
        repo = self.github.repository
        if remote not in (f"https://github.com/{repo}.git", f"https://github.com/{repo}", f"git@github.com:{repo}.git"):
            raise Blocked("Workspace remote is outside the operator-approved repository")
        return actual

    def open_workspace(self, path):
        self.check_operator()
        actual = self.validate_source(path)
        row = {"id": digest(actual["root"].encode())[:32], "path": actual["root"],
               "branch": actual["branch"], "head": actual["head"], "repository": self.github.repository}
        self.db.put("workspace", row["id"], row)
        return row

    def profiles(self):
        return [{"id": key, "provider": p["provider"], "model": p["model"], "effort": p["effort"],
                 "resolved_model": "unknown", "resolved_effort": "unknown", "new": True,
                 "resume": "explicit-owned-session", "subagents": False,
                 "buffered_tool_transport": p.get("buffered_tool_transport", False),
                 "tools": ["native"] if p["provider"] == "codex" else ["Read", "Glob", "Grep", "Bash", "Write", "Edit"]}
                for key, p in self.operator["profiles"].items()]

    def owned_sessions(self, workspace):
        project = self.project(workspace)
        result = []
        seen = set()
        if (self.control / "state.sqlite").is_file():
            with closing(Store(self.control, readonly=True).db) as db:
                rows = db.execute("SELECT id,state,data FROM runs ORDER BY rowid DESC").fetchall()
            for row in rows:
                data = json.loads(row["data"])
                if data["source"]["root"] != project["path"]:
                    continue
                for role, sid in data.get("sessions", {}).items():
                    binding = data["config"]["bindings"][role]
                    key = (binding["home"], role, sid)
                    if key in seen:
                        continue
                    seen.add(key)
                    provider = binding.get("provider", "claude" if role == "reviewer" else "codex")
                    item = {"id": sid, "provider": provider,
                            "role": role, "home": binding["home"], "config_root": str(Path(binding["home"]) / (".claude" if provider == "claude" else ".codex")),
                            "run_id": row["id"], "state": row["state"], "origin": "Stable managed",
                            "project": project["path"], "profile": binding.get("provider", "codex"),
                            "model": binding["model"], "effort": binding["effort"],
                            "resume": row["state"] in ("COMPLETED", "CANCELLED", "READY"),
                            "native_records": str(Path(binding["home"]) / (".claude/projects" if binding.get("provider") == "claude" else ".codex/sessions"))}
                    report = data.get({"implementer": "implementation", "reviewer": "review", "planner": "plan"}[role], {})
                    item.update(resolved_model=report.get("resolved_model", "unknown"), resolved_effort=report.get("resolved_effort", "unknown"))
                    result.append(item)
        return result

    def sessions(self, workspace):
        project = self.project(workspace)
        # M0 discovery remains read-only and never infers process liveness.
        directory = self.storage / "discovery"
        directory.mkdir(exist_ok=True)
        discovery = WorkspaceSessions(directory, project_roots=[project["path"]])
        workspace_id = discovery.listing()["workspaces"][0]["id"]
        return {"owned": self.owned_sessions(workspace), "discovery": discovery.snapshot(workspace_id)}

    def agent_binding(self, node, project):
        c = node["config"]
        if c["profile"] not in self.operator["profiles"]:
            raise Invalid("Choose an operator-registered runtime profile")
        p = self.operator["profiles"][c["profile"]]
        if p["provider"] != c["provider"]:
            raise Invalid("Provider/profile mismatch")
        model = p["model"] if c["model"] == "unknown" else c["model"]
        effort = p["effort"] if c["effort"] == "unknown" else c["effort"]
        if (model, effort) != (p["model"], p["effort"]):
            raise Invalid("Requested model/effort is outside this operator-approved profile")
        role = "implementer" if node["type"] == "developer" else node["type"]
        sid = None
        if c["session"] == "new":
            home = str(self.native / secrets.token_hex(16))
        else:
            matches = [s for s in self.owned_sessions(project["id"])
                       if s["id"] == c["session"] and s["role"] == role and s["provider"] == p["provider"] and s["resume"]]
            if len(matches) != 1:
                raise Blocked("Session cannot be safely resumed for this project and role")
            sid, home = matches[0]["id"], matches[0]["home"]
        return dict(project=project["id"], role=role, provider=p["provider"], executable=p["executable"],
                    home=home, read_paths=p["read_paths"], readonly_files=p["readonly_files"],
                    model=model, effort=effort, session_id=sid, isolation="bwrap",
                    external_sandbox=p["provider"] == "codex", tools=c["tools"],
                    buffered_tool_transport=p.get("buffered_tool_transport", False),
                    responsibility=c["responsibility"], background=c["background"],
                    timeout_seconds=c["timeout_seconds"])

    def prepare(self, request):
        self.check_operator()
        if set(request) != {"workspace", "workflow", "task", "delivery"}:
            raise Invalid("Unexpected task request")
        project = self.project(request["workspace"])
        source = self.validate_source(project["path"])
        self.github.branch(source["branch"])
        if git(source["root"], "status", "--porcelain=v1", "--untracked-files=all"):
            raise Blocked("Commit or isolate existing local changes before preparing a run")
        from orchestration.delivery import committed_manifest_hash
        if tree_hash(source["root"]) != committed_manifest_hash(source["root"], source["head"]):
            raise Blocked("Workspace contains ignored or uncommitted files; choose a clean isolated Development clone before authorization")
        plan = compile_plan(request["workflow"])
        task = request["task"]
        if not isinstance(task, dict) or set(task) != {"title", "body", "scope", "acceptance", "issue_url"}:
            raise Invalid("Task title, body, scope, acceptance and source reference required")
        for key in ("title", "body", "acceptance"):
            if not isinstance(task[key], str) or not task[key].strip() or len(task[key]) > (200 if key == "title" else 60000):
                raise Invalid("Invalid task text")
        if not isinstance(task["scope"], list) or not task["scope"]:
            raise Invalid("At least one explicit source-relative scope path is required")
        from orchestration.common import relative
        for path in task["scope"]:
            relative(path)
        delivery = request["delivery"]
        if not isinstance(delivery, dict) or set(delivery) != {"commit", "push", "pr"} or any(type(x) is not bool for x in delivery.values()):
            raise Invalid("Explicit commit/push/PR permissions required")
        if delivery["commit"] != delivery["push"] or delivery["push"] != delivery["pr"]:
            raise Invalid("This GitHub profile supports all three delivery actions together, or review-only")
        bindings = {}
        verifications = []
        verification_ids = {}
        nodes = {n["id"]: n for n in plan["document"]["nodes"]}
        questions = []
        final_question = None
        for key in plan["order"]:
            n = nodes[key]
            if n["type"] in ("developer", "planner", "reviewer"):
                binding = self.agent_binding(n, project)
                bindings[binding["role"]] = binding
            elif n["type"] == "verifier":
                contracts = specifications(n, self.operator.get("verification_profiles", {}))
                verification_ids[key] = [v["id"] for v in contracts]
                verifications.extend(contracts)
            elif n["type"] == "human_gate":
                if plan["document"]["template"] == "C" and key == plan["order"][-2]:
                    final_question = n["config"]["question"]
                else:
                    questions.append(n["config"]["question"])
        mode = plan["document"]["template"]
        policy = dict(schema_version=1, profile="dual-review", mode="B" if mode == "blank" else mode,
                      authorization_required=True,
                      agents={role: dict(adapter=("codex-cli" if role == "implementer" else "claude-cli"),
                                         session_policy="resume-bound" if bindings[role]["session_id"] else "new",
                                         model_policy="approved-local-binding") for role in ("implementer", "reviewer")},
                      limits=dict(max_review_rounds=plan["max_rounds"], max_infrastructure_retries=2,
                                  step_timeout_seconds=max(b["timeout_seconds"] for b in bindings.values()), max_log_bytes=8_000_000),
                      delivery=dict(commit=delivery["commit"], push=delivery["push"], merge=False, force=False, tag=False, release=False),
                      required_contracts=[v["id"] for v in verifications] + ["task-acceptance", "security-boundaries"],
                      verification=verifications)
        config = dict(task_id=secrets.token_hex(16), project=project["id"], source=source["root"],
                      acceptance="pending", goal=task["body"] + "\nAcceptance:\n" + task["acceptance"],
                      scope=task["scope"], excludes=[], policy=policy, bindings=bindings,
                      studio_workflow=dict(document=plan["document"], sha256=plan["sha256"],
                                           verification_ids=verification_ids),
                      verification_isolation=self.operator.get("verification_isolation", "landlock"))
        if final_question:
            config["human_gate_policy"] = {"mode": "deferred-G4", "question": final_question}
        if delivery["pr"]:
            endpoint = (f"repos/{self.github.repository}/pulls?state=open&head="
                        + self.github.repository.split("/")[0] + ":" + source["branch"])
            existing = self.github.api(endpoint)
            if len(existing) > 1:
                raise Blocked("Ambiguous existing PR")
            config["github_delivery"] = dict(root=source["root"], branch=source["branch"], base="main",
                repository=self.github.repository, expected_tip=self.github.tip(source["branch"]),
                existing_pr=existing[0]["number"] if existing else None, title=task["title"], summary=task["body"][:3000])
        config_check(config)
        # The preview itself is the exact data signed by the human; private paths
        # are local UI data, credential bytes are never included.
        value = dict(workspace=project, source=source, source_sha256=tree_hash(source["root"]),
                     workflow=plan, task=task, config=config, human_questions=questions,
                     stable=self.trust.binding(), operator_sha256=self.operator_sha256)
        return self.db.prepare(value)

    def authorize_start(self, permit, expected, answers):
        with self.lock:
            self.check_operator()
            value, receipt = self.db.consume(permit, expected, answers)
            source = self.validate_source(value["source"]["root"])
            if source != value["source"] or tree_hash(source["root"]) != value["source_sha256"]:
                raise Blocked("Workspace changed after the authorization preview")
            if value["operator_sha256"] != self.operator_sha256 or value["stable"] != self.trust.binding():
                raise Blocked("Runtime identity changed after preview")
            config = value["config"]
            folder = self.authority / "tasks" / permit
            folder.mkdir(parents=True, exist_ok=False, mode=0o700)
            acceptance = folder / "acceptance.md"
            acceptance.write_text(value["task"]["acceptance"])
            config["acceptance"] = str(acceptance)
            config_path, auth_path = folder / "task.json", folder / "authorization.json"
            save(config_path, config)
            auth = dict(config_sha256=digest(canonical(config)), acceptance_sha256=digest(acceptance.read_bytes()),
                        controller_sha256=controller_hash(), source=source["root"], head=source["head"], branch=source["branch"],
                        approval_ref="studio-human:" + permit + ":" + expected, external_source_approved=True,
                        commit=config["policy"]["delivery"]["commit"], push=config["policy"]["delivery"]["push"])
            if config["policy"]["mode"] == "C":
                auth["human_events"] = [dict(gate=f"G{i+1}", actor="user", evidence_ref=f"studio-human:{permit}:{i+1}")
                                        for i in range(3)]
            save(folder / "human-receipt.json", receipt)
            save(auth_path, auth)
            result = start(self.control, config_path, auth_path, trust=self.trust, deferred=True)
            run = result["id"]
            self.db.launched(permit, run, "CREATED")
            return self.launch(run, permit)

    def launch(self, run, permit=None):
        if not re.fullmatch(r"[0-9a-f]{32}", run):
            raise Invalid("Invalid run ID")
        self.check_operator()
        store = Store(self.control)
        try:
            data = store.get(run)
            binding_check(store, data["data"])
            if data["state"] in ("COMPLETED", "CANCELLED", "AWAITING_HUMAN"):
                raise Blocked("Terminal run cannot restart")
            # Check actual leases/process identity, not browser state or mtime.
            with lease(self.control / (run + ".launch.lock")):
                with lease(self.control / (run + ".lock")):
                    if any(alive(o["data"].get("process")) for o in store.operations(run) if o["kind"] in ("PROCESS", "WORKER") and o["status"] == "RUNNING"):
                        raise Blocked("An actual Agent or worker process is still alive")
                op = store.intent(run, "WORKER", {"operator_sha256": self.operator_sha256})
                env = {k: v for k, v in os.environ.items() if k in ("PATH", "LANG", "HOME", "DBUS_SESSION_BUS_ADDRESS",
                         "XDG_RUNTIME_DIR", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY")}
                env["PYTHONDONTWRITEBYTECODE"] = "1"
                child = subprocess.Popen([sys.executable, str(ROOT / "tools/devflower_usable.py"), "worker",
                    "--operator", str(self.operator_file), "--operator-sha256", self.operator_sha256, "--run", run],
                    cwd=ROOT, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    start_new_session=True, close_fds=True)
                self.children[run] = child
                actual = process_identity(child.pid)
                store.finish(op, "RUNNING", process=actual)
            if permit:
                self.db.launched(permit, run, "STARTED", worker=actual)
            return {"run_id": run, "worker": actual}
        finally:
            store.db.close()

    def snapshot(self, run):
        result, data, operations = Reader(self.control).snapshot(run, _detail=True)
        if data:
            result["stable"] = data.get("stable")
            result["sessions"] = data.get("sessions", {})
            result["github_receipt"] = data.get("github_receipt")
            result["reason"] = data.get("reason")
            result["human_gate"] = data["config"].get("human_gate_policy") if result["state"] == "AWAITING_HUMAN" else None
            current_review = data.get("review", {}).get("report", {})
            result["findings"] = current_review.get("findings", []) if current_review.get("round") == data["round"] else []
            result["contract_sha256"] = data["acceptance_sha256"]
            result["current_agent"] = None
            for operation in operations:
                context = operation["data"].get("context", {})
                role = context.get("agent_role")
                phase = {"planner": "PLANNING", "implementer": "IMPLEMENTING", "reviewer": "REVIEWING"}.get(role)
                if operation["kind"] == "PROCESS" and phase == result["state"] and operation.get("_round") == (0 if role == "planner" else data["round"]):
                    process = operation["data"].get("process")
                    result["current_agent"] = dict(role=context["agent_role"], provider=context.get("provider"),
                        process=process, alive=operation["status"] == "RUNNING" and alive(process),
                        status=operation["status"])
                    request = next((o["data"] for o in operations if o["kind"] == "AGENT_REQUEST"
                                    and o["data"].get("role") == context["agent_role"]), {})
                    result["current_agent"].update(session_id=request.get("actual_session") or request.get("requested_session") or "unknown",
                        requested_model=request.get("requested_model", "unknown"), requested_effort=request.get("requested_effort", "unknown"))
                    break
            result["agents"] = {}
            for role, key in (("planner", "plan"), ("implementer", "implementation"), ("reviewer", "review")):
                value = data.get(key)
                if value:
                    result["agents"][role] = {k: value.get(k) for k in ("session_id", "requested_model", "resolved_model",
                                                                         "requested_effort", "resolved_effort", "process")}
                    result["agents"][role]["result_round"] = (0 if role == "planner" else
                        value.get("report", {}).get("round") if role == "reviewer" else data.get("implementation_round"))
            result["workers"] = [{"process": o["data"].get("process"), "alive": alive(o["data"].get("process"))}
                                 for o in operations if o["kind"] == "WORKER"]
            if result["state"] in ("CREATED", "PREFLIGHT", "PLANNING", "IMPLEMENTING", "SNAPSHOTTING", "VERIFYING",
                                   "REVIEWING", "GATING", "COMMITTING", "PUSHING", "RECOVERING"):
                result["recorded_state"] = result["state"]
                if not any(w["alive"] for w in result["workers"]):
                    result["state"] = "RECOVERY_REQUIRED"
                    result["reason"] = "Recorded stage has no live Stable worker; explicit recovery must recheck actual side effects"
                    result["current_agent"] = None
            if "studio_workflow" in data["config"]:
                from .usable_projection import workflow_graph
                result["workflow_graph"] = workflow_graph(run, result, data, operations)
                nodes = result["workflow_graph"]["nodes"]
                reviewer = next(n for n in nodes if n["type"] == "reviewer")
                result["verdict"] = reviewer.get("verdict")
                result["findings"] = reviewer.get("findings", [])
                # Retain the independent execution gates without showing weaker
                # legacy phase inference beside the identity-bound canvas.
                kinds = {"authorization": "human_gate", "implementer": "developer",
                         "reviewer": "reviewer", "delivery": "delivery"}
                checks = {r["id"]: r for n in nodes for r in n.get("results", [])}
                execution_checks = {"verify-" + str(i): spec["id"] for i, spec in enumerate(data["config"]["policy"]["verification"])}
                for gate_node in result["graph"]["nodes"]:
                    kind = gate_node["type"]
                    if kind in kinds:
                        gate_node["status"] = next(n["status"] for n in nodes if n["type"] == kinds[kind])
                    elif kind == "verification":
                        # Legacy config.id is a numbered display label. Match
                        # the execution graph's generated identity to policy.
                        check = checks[execution_checks[gate_node["id"]]]
                        gate_node.update(status=check["status"], counts=check["counts"])
                    elif kind == "freeze":
                        gate_node["status"] = "passed" if result["candidate"] else "blocked" if result["state"] == "RECOVERY_REQUIRED" else "pending"
                    elif kind == "gate":
                        complete = all(n["status"] == "passed" for n in nodes if n["type"] in ("verifier", "reviewer", "human_gate"))
                        gate_node["status"] = "passed" if complete and result["state"] in ("READY", "COMMITTING", "PUSHING", "LOCAL_COMMITTED", "COMPLETED") else "blocked" if result["state"] in ("BLOCKED", "RECOVERY_REQUIRED", "AWAITING_HUMAN", "CANCELLED", "PARTIAL_DELIVERY") else "pending"
        return result

    def difference(self, run):
        if not re.fullmatch(r"[0-9a-f]{32}", run):
            raise Invalid("Invalid run identity")
        store = Store(self.control, readonly=True)
        try:
            data = store.get(run)["data"]
            if not data.get("candidate") or data.get("candidate_round") != data["round"]:
                raise Blocked("This round has no frozen candidate")
            candidate = Path(data["candidate_path"])
            if not candidate.resolve().is_relative_to(self.control / run) or tree_hash(candidate) != data["candidate"]["sha256"]:
                raise Blocked("Candidate identity changed")
            diff = candidate.parent / "changes.diff"
            if diff.is_symlink() or not diff.is_file():
                raise Blocked("Candidate difference is not available")
            with diff.open("rb") as stream:
                raw = stream.read(200001)
            return {"run_id": run, "candidate": data["candidate"]["sha256"], "round": data["round"],
                    "truncated": len(raw) > 200000, "text": raw[:200000].decode(errors="replace")}
        finally:
            store.db.close()

    def cancel(self, run):
        from orchestration.controller import cancel_run
        store = Store(self.control)
        try:
            return {"run_id": run, "state": cancel_run(store, run)["state"]}
        finally:
            store.db.close()

    def approve_result(self, run, answer):
        from orchestration.controller import approve_human_gate
        self.check_operator()
        store = Store(self.control)
        try:
            approve_human_gate(store, run, answer, "studio-g4:" + secrets.token_hex(16))
        finally:
            store.db.close()
        return self.launch(run)
