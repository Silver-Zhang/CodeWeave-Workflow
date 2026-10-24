"""Usable v1 contract tests. Fake services here are not model acceptance."""
import copy
from contextlib import closing
import sqlite3
import hashlib
from http.server import ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch, MagicMock
from urllib.error import HTTPError
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from orchestration.common import Blocked, canonical, digest, save, tree_hash, manifest
from orchestration.process import execute
from orchestration.store import Store
from orchestration.trust import TrustedRelease
from studio.graph import Invalid
from studio.server import Conflict
from studio.usable_graph import template, compile_plan, draft, node
from studio.usable_store import Storage
from studio.usable_verification import specification, specifications
from studio.usable_runtime import Runtime
from studio.usable_server import handler
from test_orchestration import Fixture, FAKE
from orchestration import controller
from orchestration.github_delivery import GitHub


class GraphTests(unittest.TestCase):
    def test_all_starting_templates_are_editable_and_compile(self):
        for mode in "ABC":
            value = template(mode)
            value["name"] += " edited"
            value["nodes"][-1]["label"] = "My delivery"
            self.assertEqual(compile_plan(value)["document"]["template"], mode)

    def test_blank_can_be_built_and_empty_draft_saved(self):
        self.assertEqual(draft(template("blank"))["nodes"], [])
        with self.assertRaises(Invalid):
            compile_plan(template("blank"))
        value = template("A"); value["template"] = "blank"
        self.assertTrue(compile_plan(value)["order"])

    def test_cannot_remove_tests_reviewer_or_human_authorization(self):
        for kind in ("human_gate", "verifier", "reviewer"):
            value = template("A")
            victim = next(n["id"] for n in value["nodes"] if n["type"] == kind)
            value["nodes"] = [n for n in value["nodes"] if n["id"] != victim]
            value["edges"] = [e for e in value["edges"] if victim not in (e["source"], e["target"])]
            with self.assertRaises(Invalid):
                compile_plan(value)

    def test_parallel_cycles_and_wrong_repair_are_rejected(self):
        for edge in (
            {"source": "human-1", "target": "reviewer", "on": "next"},
            {"source": "delivery", "target": "human-1", "on": "next"},
            {"source": "reviewer", "target": "human-1", "on": "repair"},
        ):
            value = template("A");value["edges"].append(edge)
            with self.assertRaises(Invalid):
                compile_plan(value)

    def test_unsupported_capabilities_do_not_silently_disappear(self):
        value = template("A")
        dev = next(n for n in value["nodes"] if n["type"] == "developer")
        dev["config"]["subagents"] = True
        with self.assertRaises(Invalid):
            compile_plan(value)
        dev["config"]["subagents"] = False;dev["config"]["provider"] = "claude";dev["config"]["tools"] = ["Read"]
        with self.assertRaises(Invalid):
            compile_plan(value)

    def test_verifier_does_not_accept_shell_or_traversal(self):
        n = node("verifier")
        for path in ("/etc/passwd", "../outside", ".git/config"):
            n["config"]["target"] = path
            with self.assertRaises(Invalid):
                specification(n)
        n["config"]["target"] = "tests";n["config"]["pattern"] = "test*.py;echo secret"
        with self.assertRaises(Invalid):
            specification(n)

    def test_fixed_verifier_counts_real_failures(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp);(p / "tests").mkdir()
            (p / "tests/test_case.py").write_text("import unittest\nclass T(unittest.TestCase):\n def test_x(self):self.fail('intentional')\n")
            n = node("verifier");n["config"]["profile"]="baseline";spec = specification(n)
            (p / "tools").mkdir();(p / "tools/devflower.py").write_text("raise SystemExit(1)\n")
            from orchestration.verification import verify
            config = dict(policy=dict(verification=[spec], limits=dict(step_timeout_seconds=10, max_log_bytes=1048576)))
            reports = verify(config, p, p.parent / (p.name + '-results'), 'test', 1, tree_hash(p), 'a'*64)
            self.addCleanup(__import__('shutil').rmtree, p.parent / (p.name + '-results'))
            self.assertFalse(reports[0]['passed'])
            self.assertEqual(reports[0]['counts'], dict(tests=1, failures=1, errors=0, skipped=0))


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.store = Storage(Path(self.tmp.name) / "storage")

    def test_metadata_put_survives_real_transient_writer_lock(self):
        self.store.put('session', 'existing', {'unchanged': True})
        with closing(sqlite3.connect(self.store.path)) as writer:
            writer.execute('BEGIN IMMEDIATE')
            original_db = self.store.db
            self.store.db = lambda: closing(sqlite3.connect(self.store.path, timeout=.001))
            # First real SQLITE_BUSY rolls back/closes before releasing the writer.
            with patch('studio.usable_store.time.sleep', side_effect=lambda _: writer.rollback()) as delay:
                self.store.put('session', 'new', {'native_session': 'same-turn'})
            self.assertEqual(delay.call_count, 1)
            self.store.db = original_db
        self.assertEqual(self.store.get('session', 'new'), {'native_session': 'same-turn'})
        self.assertEqual(self.store.get('session', 'existing'), {'unchanged': True})
        self.assertEqual(len(self.store.listing('session')), 2)

    def test_metadata_put_persistent_busy_is_bounded_without_phantom_commit(self):
        with closing(sqlite3.connect(self.store.path)) as writer:
            writer.execute('BEGIN IMMEDIATE')
            opened = []
            def connection():
                db = sqlite3.connect(self.store.path, timeout=.001); opened.append(db)
                return closing(db)
            self.store.db = connection
            with patch('studio.usable_store.time.sleep') as delay:
                with self.assertRaises(sqlite3.OperationalError) as error:
                    self.store.put('session', 'new', {'value': 'not committed'})
            self.assertEqual(error.exception.sqlite_errorcode, sqlite3.SQLITE_BUSY)
            self.assertEqual(delay.call_count, 2); self.assertEqual(len(opened), 3)
            for db in opened:
                with self.assertRaises(sqlite3.ProgrammingError): db.execute('SELECT 1')
            writer.rollback()
        with self.assertRaises(Invalid): self.store.get('session', 'new')
        self.store.put('session', 'new', {'value': 'later independent write'})
        self.assertEqual(self.store.get('session', 'new')['value'], 'later independent write')

    def test_metadata_put_readonly_is_not_retried_and_preserves_previous_data(self):
        self.store.put('session', 'old', {'value': 'original'})
        self.store.db = lambda: closing(sqlite3.connect(self.store.path.as_uri() + '?mode=ro', uri=True))
        with patch('studio.usable_store.time.sleep') as delay:
            with self.assertRaises(sqlite3.OperationalError) as error:
                self.store.put('session', 'old', {'value': 'must not replace'})
        self.assertEqual(error.exception.sqlite_errorcode, sqlite3.SQLITE_READONLY)
        delay.assert_not_called()
        self.assertEqual(self.store.get('session', 'old'), {'value': 'original'})

    def test_immutable_drafts_keep_cas(self):
        first = self.store.save_draft(template("A"))
        second = copy.deepcopy(first["document"]);second["name"] = "second"
        self.store.save_draft(second, first["id"], first["revision"])
        with self.assertRaises(Conflict):
            self.store.save_draft(first["document"], first["id"], first["revision"])
        with self.store.db() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM revisions").fetchone()[0], 2)

    def test_preview_requires_bound_hash_and_human_answers_once(self):
        permit = self.store.prepare({"human_questions": ["Approve scope?"]})
        with self.assertRaises(Conflict):
            self.store.consume(permit["id"], "0" * 64, ["yes"])
        with self.assertRaises(Invalid):
            self.store.consume(permit["id"], permit["sha256"], [""])
        _, receipt = self.store.consume(permit["id"], permit["sha256"], ["Approved for this task"])
        self.assertEqual(receipt["actor"], "user")
        with self.assertRaises(Conflict):
            self.store.consume(permit["id"], permit["sha256"], ["again"])

    def test_symlink_database_is_not_adopted(self):
        root = Path(self.tmp.name) / "attack";root.mkdir()
        (root / "usable.sqlite").symlink_to(self.store.path)
        with self.assertRaises(Invalid):
            Storage(root)


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / "development";self.source.mkdir()
        def git(*args):
            return subprocess.run(["git", "-C", str(self.source), *args], capture_output=True, check=True)
        git("init", "-b", "flow/usable-test")
        git("config", "user.name", "Fixture");git("config", "user.email", "fixture@example.invalid")
        git("remote", "add", "origin", "https://github.com/fixture/project.git")
        (self.source / "README.md").write_text("fixture")
        git("add", "README.md");git("commit", "-m", "fixture")
        authority = self.root / "authority";authority.mkdir()
        self.operator_file = authority / "operator.json"
        profiles = {}
        for provider in ("codex", "claude"):
            credential = self.root / (provider + ".json");credential.write_text("{}")
            profiles["default-" + provider] = dict(provider=provider, executable="/usr/bin/true",
                model="test-model", effort="high", read_paths=["/usr/bin/true"],
                readonly_files=[[str(credential), ".codex/auth.json" if provider == "codex" else ".claude/settings.json"]])
        self.binding = dict(record=str(self.root / "approval.json"), sha256="a" * 64)
        python = str(Path(sys.executable).resolve())
        self.assertion_profiles = {"default": [dict(id="value", argv=[python, "-I", "-c",
            "import json,runpy;print(json.dumps(runpy.run_path('value.py')['VALUE']))"],
            stdin="", expected_json=42, read_paths=[])]}
        operator = dict(stable=self.binding, authority=str(authority), storage=str(self.root / "studio"),
                        native=str(self.root / "native"), allowed_roots=[str(self.source)],
                        dependencies={python: digest(Path(python).read_bytes())}, verification_profiles=self.assertion_profiles,
                        profiles=profiles, github=dict(executable="/usr/bin/true", config_dir=str(self.root / "github"), repository="fixture/project"))
        save(self.operator_file, operator)
        trusted = MagicMock();trusted.record = self.root / "approval.json";trusted.binding.return_value = self.binding
        trusted.data = {"candidate_sha256": "a" * 64}
        p = patch("studio.usable_runtime.TrustedRelease.bound", return_value=trusted);p.start();self.addCleanup(p.stop)
        self.trust_patch = p
        self.runtime = Runtime(self.operator_file, digest(self.operator_file.read_bytes()))
        self.project = self.runtime.open_workspace(str(self.source))

    def request(self):
        return dict(workspace=self.project["id"], workflow=template("A"), task=dict(title="Fixture", body="Change README.",
            scope=["README.md"], acceptance="README has the requested content.", issue_url=""),
            delivery=dict(commit=False, push=False, pr=False))

    def test_F4_ignored_source_artifact_rejected_before_permit_creation(self):
        from orchestration.common import git
        (self.source/'.gitignore').write_text('ignored.log\n')
        git(self.source,'add','.gitignore');git(self.source,'commit','-m','ignore fixture')
        (self.source/'ignored.log').write_text('user artifact must be preserved')
        self.assertEqual(git(self.source,'status','--porcelain=v1','--untracked-files=all'),'')
        with self.assertRaisesRegex(Blocked,'ignored'):
            self.runtime.prepare(self.request())
        with self.runtime.db.db() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM permits').fetchone()[0],0)
        self.assertEqual((self.source/'ignored.log').read_text(),'user artifact must be preserved')

    def test_F2_all_active_stages_without_worker_require_recovery(self):
        store=Store(self.runtime.control);self.addCleanup(store.db.close)
        config=self.runtime.prepare(self.request())['data']['config']
        run=store.create(dict(config=config,source={'root':str(self.source)},round=0,sessions={},acceptance_sha256='a'*64))
        for state in ('CREATED','PREFLIGHT','PLANNING','IMPLEMENTING','SNAPSHOTTING','VERIFYING','REVIEWING','GATING','COMMITTING','PUSHING','RECOVERING'):
            store.transition(run,state)
            snapshot=self.runtime.snapshot(run)
            self.assertEqual(snapshot['state'],'RECOVERY_REQUIRED',state)
            self.assertEqual(snapshot['recorded_state'],state)
        store.transition(run,'BLOCKED');self.assertEqual(self.runtime.snapshot(run)['state'],'BLOCKED')

    def test_prepare_never_starts_an_agent_or_grants_permission(self):
        value = self.runtime.prepare(self.request())
        self.assertEqual(value["data"]["config"]["bindings"]["reviewer"]["model"], "test-model")
        self.assertFalse((self.runtime.control / "state.sqlite").exists())
        with self.runtime.db.db() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM launches").fetchone()[0], 0)

    def test_verification_backend_is_operator_bound_and_defaults_to_landlock(self):
        value = self.runtime.prepare(self.request())
        self.assertEqual(value['data']['config']['verification_isolation'], 'landlock')
        operator = load_json(self.operator_file)
        operator['verification_isolation'] = 'bwrap'
        save(self.operator_file, operator)
        runtime = Runtime(self.operator_file, digest(self.operator_file.read_bytes()))
        value = runtime.prepare(self.request())
        self.assertEqual(value['data']['config']['verification_isolation'], 'bwrap')
        from orchestration.contracts import config_check
        config = value['data']['config']
        config['verification_isolation'] = 'none'
        with self.assertRaisesRegex(Blocked, 'verification isolation'):
            config_check(config)

    def test_C_preview_cannot_pretend_result_interpretation_already_happened(self):
        request = self.request();request["workflow"] = template("C")
        value = self.runtime.prepare(request)
        self.assertEqual(len(value["data"]["human_questions"]), 3)
        self.assertEqual(value["data"]["config"]["human_gate_policy"]["mode"], "node-results")
        self.assertEqual(value["data"]["config"]["policy"]["mode"], "B")

    def test_changed_source_invalidates_preview(self):
        value = self.runtime.prepare(self.request())
        (self.source / "README.md").write_text("changed after preview")
        with self.assertRaisesRegex(Blocked, "changed"):
            self.runtime.authorize_start(value["id"], value["sha256"], ["Approved"])

    def test_unknown_native_session_cannot_be_adopted(self):
        request = self.request()
        request["workflow"]["nodes"][1]["config"]["session"] = "11111111-1111-1111-1111-111111111111"
        with self.assertRaises(Blocked):
            self.runtime.prepare(request)

    def test_unapproved_model_and_partial_delivery_rejected(self):
        request = self.request();request["workflow"]["nodes"][1]["config"]["model"] = "other-model"
        with self.assertRaises(Invalid):
            self.runtime.prepare(request)
        request = self.request();request["delivery"]["push"] = True
        with self.assertRaises(Invalid):
            self.runtime.prepare(request)

    def test_outside_workspace_and_changed_operator_rejected(self):
        with self.assertRaises(Blocked):
            self.runtime.open_workspace("/etc")
        value = load_json(self.operator_file);value["dependencies"]["/missing"] = "x"
        save(self.operator_file, value)
        with self.assertRaisesRegex(Blocked, "binding changed"):
            self.runtime.prepare(self.request())

    def test_http_never_serves_approval_token_or_arbitrary_shell(self):
        token = "capability-only-known-to-user"
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler(self.runtime, token))
        thread = threading.Thread(target=server.serve_forever, daemon=True);thread.start()
        self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
        base = f"http://127.0.0.1:{server.server_port}"
        self.assertNotIn(token.encode(), urlopen(base).read())
        with self.assertRaises(HTTPError) as exc:
            urlopen(base + "/api/status")
        self.assertEqual(exc.exception.code, 403)
        req = Request(base + "/api/shell", data=b'{"argv":["echo","bad"]}',
                      headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"})
        with self.assertRaises(HTTPError) as exc:
            urlopen(req)
        self.assertEqual(exc.exception.code, 404)
        req = Request(base + "/api/status", headers={"Authorization": "Bearer " + token, "Origin": "null"})
        with self.assertRaises(HTTPError) as exc:
            urlopen(req)
        self.assertEqual(exc.exception.code, 403)

    def test_m0_native_discovery_is_callable(self):
        response = self.runtime.sessions(self.project["id"])
        self.assertEqual(response["owned"], [])
        self.assertIn("coverage", response["discovery"])

    def test_reused_native_session_projects_latest_owner_only(self):
        store = Store(self.runtime.control);self.addCleanup(store.db.close)
        binding = dict(home=str(self.runtime.native / "owned"), provider="codex", model="test-model", effort="high")
        data = dict(source={"root": str(self.source)}, config={"bindings": {"implementer": binding}},
                    sessions={"implementer": "11111111-1111-1111-1111-111111111111"})
        old = store.create(data);store.transition(old, "READY")
        current = store.create(data);store.transition(current, "IMPLEMENTING")
        sessions = self.runtime.owned_sessions(self.project["id"])
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0]["run_id"], current)
        self.assertFalse(sessions[0]["resume"])

    def test_detached_worker_fixture_repairs_and_survives_service_reopen(self):
        # Synthetic CLI fixture only; never used as the final real-model evidence.
        self.trust_patch.stop()
        from orchestration.common import git
        (self.source / "value.py").write_text("VALUE = 0\n")
        (self.source / "tests").mkdir()
        (self.source / "tests/test_value.py").write_text(
            "import unittest\nfrom value import VALUE\nclass TestValue(unittest.TestCase):\n def test_value(self):self.assertEqual(VALUE,42)\n")
        git(self.source, "add", "value.py", "tests/test_value.py");git(self.source, "commit", "-m", "fixture test")
        fake = self.root / "fixture-cli"
        script = FAKE.replace("'unit'", "'verifier'")
        old = "'contracts':[{'id':'verifier','status':'PASS' if passed else 'FAIL','evidence_refs':['verifier']}]"
        new = "'contracts':[{'id':identity,'status':'PASS' if passed else 'FAIL','evidence_refs':['verifier']} for identity in ['verifier','task-acceptance','security-boundaries']]"
        self.assertIn(old, script);fake.write_text(script.replace(old, new));fake.chmod(0o755)
        source_root = Path(controller.__file__).resolve().parents[2]
        entries = manifest(source_root);record = self.root / "fixture-approval.json"
        save(record, dict(version=1, root=str(source_root), git_commit="a"*40, git_tree="b"*40,
            candidate_sha256=digest(canonical(entries)), files=entries, review_verdict="ACCEPT",
            review_receipt_sha256="c"*64, approval_ref="UNIT TEST ONLY, not Stable deployment"))
        operator = load_json(self.operator_file)
        operator["stable"] = dict(record=str(record), sha256=digest(record.read_bytes()))
        for profile in operator["profiles"].values():
            profile.update(executable=str(fake), read_paths=[str(fake)])
        save(self.operator_file, operator)
        sha = digest(self.operator_file.read_bytes())
        runtime = Runtime(self.operator_file, sha)
        request = self.request();request["task"].update(scope=["value.py"], body="Change VALUE to 42", acceptance="VALUE must equal 42.")
        preview = runtime.prepare(request)
        launched = runtime.authorize_start(preview["id"], preview["sha256"], ["SYNTHETIC TEST AUTHORIZATION ONLY"])
        child = runtime.children[launched["run_id"]]
        try:
            deadline = time.monotonic() + 20
            while time.monotonic() < deadline:
                store = Store(runtime.control, readonly=True)
                result = store.get(launched["run_id"]);store.db.close()
                if result["state"] in ("READY", "BLOCKED", "CANCELLED"):
                    break
                time.sleep(.05)
            child.wait(timeout=5)
            self.assertEqual(result["state"], "READY", result["data"].get("reason"))
            self.assertEqual(result["data"]["round"], 2)
            reopened = Runtime(self.operator_file, sha)
            view = reopened.snapshot(launched["run_id"])
            self.assertEqual(view["id"], launched["run_id"])
            self.assertEqual(view["verdict"], "ACCEPT")
            self.assertFalse(any(w["alive"] for w in view["workers"]))
            self.assertEqual((self.source / "value.py").read_text(), "VALUE = 0\n")
            with self.assertRaises(Conflict):
                reopened.authorize_start(preview["id"], preview["sha256"], ["REPLAY"])
        finally:
            if child.poll() is None:
                child.terminate();child.wait(timeout=5)


def load_json(path):
    return json.loads(path.read_bytes())


class IsolationTests(unittest.TestCase):
    def test_readonly_overlay_cannot_modify_original_credential(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp);source = p / "original.json";source.write_text('{"probe":"no-secret"}')
            work = p / "work";work.mkdir()
            home = p / "home"
            code = "from pathlib import Path;import os\np=Path(os.environ['HOME'])/'.codex/auth.json'\nassert p.read_text()=='{\"probe\":\"no-secret\"}'\ntry:p.write_text('bad')\nexcept OSError:print('denied')\nelse:raise SystemExit(1)"
            process, out, _ = execute(["python3", "-c", code], work, home, read=[str(work)],
                                     backend="bwrap", readonly_files=[(str(source), ".codex/auth.json")])
            self.assertEqual(process["exit"], 0)
            self.assertEqual(out.strip(), b"denied")
            self.assertEqual(source.read_text(), '{"probe":"no-secret"}')

    def test_overlay_symlink_destination_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp);source = p / "original";source.write_text("safe")
            home = p / "home";home.mkdir();(home / ".codex").symlink_to(p)
            with self.assertRaises(Blocked):
                execute(["true"], p, home, backend="bwrap", readonly_files=[(str(source), ".codex/auth.json")])


class TrustTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name);self.stable = self.root / "stable"
        (self.stable / "tools/orchestration").mkdir(parents=True)
        self.engine = self.stable / "tools/orchestration/trust.py"
        self.engine.write_text("# controlled test fixture, not an accepted release\n")
        p = patch("orchestration.trust.__file__", str(self.engine));p.start();self.addCleanup(p.stop)
        self.record = self.root / "external-approval.json"

    def approve_fixture(self):
        entries = manifest(self.stable)
        save(self.record, dict(version=1, root=str(self.stable), git_commit="a"*40, git_tree="b"*40,
             candidate_sha256=digest(canonical(entries)), files=entries, review_verdict="ACCEPT",
             review_receipt_sha256="c"*64, approval_ref="UNIT TEST FIXTURE ONLY"))
        return digest(self.record.read_bytes())

    def test_code_mutation_invalidates_pinned_release(self):
        trusted = TrustedRelease(self.record, self.approve_fixture())
        self.engine.write_text("# changed\n")
        with self.assertRaisesRegex(Blocked, "reviewed release"):
            trusted.verify()

    def test_development_authority_overlap_and_wrong_pin_refused(self):
        sha = self.approve_fixture()
        with self.assertRaises(Blocked):
            TrustedRelease(self.record, "0"*64)
        trusted = TrustedRelease(self.record, sha)
        with self.assertRaises(Blocked):
            trusted.permits(self.stable / "development", self.root / "authority")
        with self.assertRaises(Blocked):
            trusted.permits(self.root / "development", self.root / "development/control")

    def test_symlink_cannot_escape_complete_code_identity(self):
        external = self.root / "outside.py";external.write_text("# mutable external code\n")
        (self.stable / "other.py").symlink_to(external)
        with self.assertRaisesRegex(Blocked, "symlinks"):
            TrustedRelease(self.record, self.approve_fixture())


class PlannerTests(Fixture):
    def test_optional_planner_has_separate_readonly_home_and_session(self):
        script = FAKE.replace(" (cwd/'value.py').write_text(", " if 'Role: planner.' not in prompt: (cwd/'value.py').write_text(")
        self.fake.write_text(script)
        self.config["bindings"]["planner"] = dict(self.config["bindings"]["implementer"],
            role="planner", provider="codex", home=str(self.base / "home-planner"),
            responsibility="planner", isolation="bwrap", external_sandbox=True)
        self.authorize()
        result = controller.start(self.control, self.config_path, self.auth_path)
        self.assertEqual(result["state"], "READY", result["data"].get("reason"))
        self.assertIn("planner", result["data"]["sessions"])
        self.assertEqual(len(set(result["data"]["sessions"].values())), 3)
        self.assertEqual((self.source / "value.py").read_text(), "VALUE = 0\n")

    def test_third_home_overlap_is_blocked(self):
        self.config["bindings"]["planner"] = dict(self.config["bindings"]["implementer"], role="planner")
        self.authorize()
        result = controller.start(self.control, self.config_path, self.auth_path)
        self.assertEqual(result["state"], "BLOCKED")
        self.assertIn("home overlaps", result["data"]["reason"])


class StagedHumanTests(Fixture):
    def prepare_C(self):
        self.config["policy"]["mode"] = "C"
        python = str(Path(sys.executable).resolve())
        spec = specifications(node("verifier"), {"default": [dict(id="value", argv=[python, "-I", "-c",
            "import json,runpy;print(json.dumps(runpy.run_path('value.py')['VALUE']))"], stdin="", expected_json=42, read_paths=[])]})[0]
        spec["id"] = "unit";self.config["policy"]["verification"] = [spec]
        self.config["human_gate_policy"] = {"mode": "deferred-G4", "question": "Interpret the observed results"}
        self.authorize()
        self.auth["human_events"] = [dict(gate=f"G{i}", actor="user", evidence_ref="unit-fixture-only") for i in range(1, 4)]
        save(self.auth_path, self.auth)
        root = Path(controller.__file__).resolve().parents[2]
        entries = manifest(root)
        record = self.base / "fixture-approval.json"
        save(record, dict(version=1, root=str(root), git_commit="a"*40, git_tree="b"*40,
            candidate_sha256=digest(canonical(entries)), files=entries, review_verdict="ACCEPT",
            review_receipt_sha256="c"*64, approval_ref="UNIT TEST ONLY; no production Stable promotion"))
        trust = TrustedRelease(record, digest(record.read_bytes()))
        result = controller.start(self.control, self.config_path, self.auth_path, trust=trust)
        self.assertEqual(result["state"], "AWAITING_HUMAN", result["data"].get("reason"))
        return result

    def test_F3_Stable_rejects_legacy_four_upfront_C_references(self):
        self.prepare_C()
        del self.config['human_gate_policy']
        self.authorize()
        self.auth['human_events']=[dict(gate=f'G{i}',actor='user',evidence_ref='upfront-fixture') for i in range(1,5)]
        save(self.auth_path,self.auth)
        record=self.base/'fixture-approval.json';trust=TrustedRelease(record,digest(record.read_bytes()))
        with self.assertRaisesRegex(Blocked,'post-review G4'):
            controller.start(self.base/'must-not-start',self.config_path,self.auth_path,trust=trust)
        self.assertFalse((self.base/'must-not-start').exists())

    def test_C_waits_after_actual_review_and_resume_cannot_skip_G4(self):
        result = self.prepare_C();store = Store(self.control);self.addCleanup(store.db.close)
        operations = len(store.operations(result["id"]))
        self.assertEqual(controller.resume(store, result["id"])["state"], "AWAITING_HUMAN")
        self.assertEqual(len(store.operations(result["id"])), operations)
        with self.assertRaisesRegex(Blocked, "G4"):
            controller.deliver_run(store, result["id"])
        with self.assertRaises(Blocked):
            controller.approve_human_gate(store, result["id"], "", "studio-g4:unit-test")
        approved = controller.approve_human_gate(store, result["id"], "Fixture human interpretation of the actual passing result", "studio-g4:unit-test")
        self.assertEqual(approved["state"], "READY")
        self.assertTrue(controller.human_result_bound(approved["data"]))
        changed = dict(approved["data"], round=approved["data"]["round"] + 1)
        self.assertFalse(controller.human_result_bound(changed))

    def test_C_candidate_change_before_human_gate_is_refused(self):
        result = self.prepare_C();store = Store(self.control);self.addCleanup(store.db.close)
        (Path(result["data"]["candidate_path"]) / "value.py").write_text("VALUE = 999\n")
        with self.assertRaisesRegex(Blocked, "candidate changed"):
            controller.approve_human_gate(store, result["id"], "Approved", "studio-g4:unit-test")

    def test_C_staged_mode_cannot_bypass_legacy_self_source_guard(self):
        self.config["policy"]["mode"] = "C"
        python = str(Path(sys.executable).resolve())
        spec = specifications(node("verifier"), {"default": [dict(id="value", argv=[python, "-I", "-c",
            "import json,runpy;print(json.dumps(runpy.run_path('value.py')['VALUE']))"], stdin="", expected_json=42, read_paths=[])]})[0]
        spec["id"] = "unit";self.config["policy"]["verification"] = [spec]
        self.config["human_gate_policy"] = {"mode": "deferred-G4", "question": "Interpret"}
        self.authorize()
        self.auth["human_events"] = [dict(gate=f"G{i}", actor="user", evidence_ref="unit-fixture-only") for i in range(1, 4)]
        save(self.auth_path, self.auth)
        with self.assertRaisesRegex(Blocked, "Stable"):
            controller.start(self.control, self.config_path, self.auth_path)


class GitHubTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name);self.store = Store(self.root / "control")
        self.addCleanup(self.store.db.close)
        self.run = self.store.create({})
        self.client = GitHub("/usr/bin/true", self.root / "gh", "fixture/project")
        self.target = dict(root=str(self.root), branch="flow/test", expected_tip=None, base="main",
                           title="Fixture", summary="Summary", existing_pr=None)

    def test_protected_branch_and_foreign_issue_or_api_refused(self):
        for branch in ("main", "master", "flow/a/../main", "flow/a//b"):
            with self.assertRaises(Blocked):
                self.client.branch(branch)
        for url in ("http://127.0.0.1/private", "https://github.com/other/project/issues/1"):
            with self.assertRaises(Blocked):
                self.client.issue(url)
        with self.assertRaises(Blocked):
            self.client.api("user")

    def test_push_success_with_lost_receipt_uses_readback(self):
        sha = "a" * 40
        with patch.object(self.client, "tip", side_effect=[None, sha]) as readback, patch(
                "orchestration.github_delivery.subprocess.run", side_effect=subprocess.TimeoutExpired("git push", 90)) as push:
            self.assertEqual(self.client.push(self.store, self.run, self.target, sha), sha)
            self.assertEqual(push.call_count, 1);self.assertEqual(readback.call_count, 2)
        with patch.object(self.client, "tip", return_value=sha), patch("orchestration.github_delivery.subprocess.run") as push:
            self.client.push(self.store, self.run, self.target, sha)
            push.assert_not_called()

    def test_remote_competition_prevents_push(self):
        with patch.object(self.client, "tip", return_value="b" * 40), patch("orchestration.github_delivery.subprocess.run") as push:
            with self.assertRaisesRegex(Blocked, "advanced"):
                self.client.push(self.store, self.run, self.target, "a" * 40)
            push.assert_not_called()

    def test_lost_pr_receipt_reads_existing_pr_once(self):
        sha = "a" * 40
        self.store.transition(self.run, "READY", candidate={"sha256": "c" * 64}, acceptance_sha256="d" * 64,
                              review={"report": {"verdict": "ACCEPT"}}, round=2,
                              verification=[{"counts": {"tests": 2, "skipped": 0}}])
        item = dict(number=7, html_url="https://github.com/fixture/project/pull/7", head={"sha": sha}, base={"ref": "main"},
                    body="DevFlower-Run: " + self.run)
        with patch.object(self.client, "api", side_effect=[[], Blocked("lost POST receipt"), [item]]) as api:
            self.assertEqual(self.client.pr(self.store, self.run, self.target, sha)["number"], 7)
            self.assertEqual(sum(call.args[1:] != () for call in api.call_args_list), 1)


if __name__ == "__main__":
    unittest.main()
