"""GitHub transport owned by Stable, with intent/readback and no merge endpoint."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shlex
import subprocess
from urllib.parse import quote

from .common import Blocked, canonical, clean_env, digest, git, identity, tree_hash
from .delivery import commit, make_tree, committed_manifest_hash


class GitHub:
    def __init__(self, executable, config_dir, repository):
        self.executable = Path(executable).resolve()
        self.config_dir = Path(config_dir).resolve()
        if not self.executable.is_file() or not os.access(self.executable, os.X_OK):
            raise Blocked("GitHub CLI unavailable")
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
            raise Blocked("Explicit owner/repository required")
        self.repository = repository

    def environment(self):
        env = dict(clean_env(), GH_CONFIG_DIR=str(self.config_dir), GH_PROMPT_DISABLED="1",
                   GH_HOST="github.com", HOME=str(self.config_dir))
        # gh can use its native OS keyring; this environment never reaches Agents.
        for key in ("DBUS_SESSION_BUS_ADDRESS", "XDG_RUNTIME_DIR"):
            if key in os.environ:
                env[key] = os.environ[key]
        return env

    def api(self, endpoint, payload=None, missing=False):
        if not endpoint.startswith("repos/" + self.repository + "/") and endpoint != "repos/" + self.repository:
            raise Blocked("GitHub endpoint outside the operator repository")
        args = [str(self.executable), "api", "--hostname", "github.com", endpoint]
        if payload is not None:
            args += ["--method", "POST", "--input", "-"]
        try:
            p = subprocess.run(args, input=canonical(payload) if payload is not None else None,
                               capture_output=True, timeout=60, env=self.environment())
        except (OSError, subprocess.TimeoutExpired):
            raise Blocked("GitHub request outcome unknown; inspect readback before retry") from None
        if p.returncode:
            if missing and b"HTTP 404" in p.stderr:
                return None
            raise Blocked("GitHub request failed; credential details omitted")
        if len(p.stdout) > 4_000_000:
            raise Blocked("GitHub response exceeded budget")
        return json.loads(p.stdout)

    def issue(self, url):
        pattern = r"https://github\.com/" + re.escape(self.repository) + r"/issues/([1-9][0-9]*)/?"
        match = re.fullmatch(pattern, url)
        if not match:
            raise Blocked("Issue URL must belong to the explicitly allowed GitHub repository")
        data = self.api(f"repos/{self.repository}/issues/{match[1]}")
        if "pull_request" in data:
            raise Blocked("A task Issue, not a pull request, is required")
        return {key: data.get(key) for key in ("number", "title", "body", "html_url", "updated_at", "state")}

    def tip(self, branch):
        self.branch(branch)
        data = self.api(f"repos/{self.repository}/git/ref/heads/{quote(branch, safe='/')}", missing=True)
        return data["object"]["sha"] if data else None

    @staticmethod
    def branch(value):
        if not isinstance(value, str) or not re.fullmatch(r"(flow|work|feature|fix)/[A-Za-z0-9][A-Za-z0-9_/-]{0,120}", value):
            raise Blocked("Delivery requires an explicit development branch")
        if ".." in value or "//" in value or value.endswith("/"):
            raise Blocked("Invalid development branch")
        return value

    def push(self, store, run, target, sha):
        old = [o for o in store.operations(run) if o["kind"] == "GITHUB_PUSH"]
        data = dict(target, commit=sha)
        if old:
            op = old[-1]["id"]
            if any(old[-1]["data"].get(k) != v for k, v in data.items()):
                raise Blocked("GitHub push intent changed")
        else:
            op = store.intent(run, "GITHUB_PUSH", data)
        observed = self.tip(target["branch"])
        if observed != sha:
            if observed != target["expected_tip"]:
                raise Blocked("Remote branch advanced after human approval")
            if observed and subprocess.run(["git", "-C", target["root"], "merge-base", "--is-ancestor", observed, sha],
                                           env=clean_env(), capture_output=True).returncode:
                raise Blocked("GitHub delivery would not fast-forward")
            args = ["git", "-C", target["root"], "-c", "core.hooksPath=/dev/null",
                    "-c", "credential.helper=", "-c",
                    "credential.helper=!" + shlex.quote(str(self.executable)) + " auth git-credential",
                    "push", f"https://github.com/{self.repository}.git",
                    sha + ":refs/heads/" + target["branch"]]
            try:
                subprocess.run(args, env=self.environment(), capture_output=True, timeout=90)
            except (OSError, subprocess.TimeoutExpired):
                pass
            observed = self.tip(target["branch"])
        if observed != sha:
            store.finish(op, "UNKNOWN", observed_tip=observed)
            raise Blocked("Push not confirmed by remote readback")
        store.finish(op, "PUSHED", readback=sha)
        return sha

    def pr(self, store, run, target, sha):
        marker = f"DevFlower-Run: {run}"
        old = [o for o in store.operations(run) if o["kind"] == "GITHUB_PR"]
        intent = dict(branch=target["branch"], base=target["base"], commit=sha, repository=self.repository)
        if old:
            op = old[-1]["id"]
            if any(old[-1]["data"].get(k) != v for k, v in intent.items()):
                raise Blocked("PR intent changed")
        else:
            op = store.intent(run, "GITHUB_PR", intent)
        endpoint = (f"repos/{self.repository}/pulls?state=open&base={quote(target['base'], safe='')}"
                    f"&head={quote(self.repository.split('/')[0] + ':' + target['branch'], safe='')}")
        def readback():
            found = self.api(endpoint)
            if len(found) > 1:
                raise Blocked("Ambiguous PR identity")
            if found:
                item = found[0]
                if item["head"]["sha"] != sha or item["base"]["ref"] != target["base"]:
                    raise Blocked("PR source or base mismatch")
                # An existing branch PR may be explicitly selected by the human.
                if marker not in (item.get("body") or "") and item["number"] != target.get("existing_pr"):
                    raise Blocked("Existing PR was not bound in this authorization")
                return item
            return None
        item = readback()
        if item is None:
            data = store.get(run)["data"]
            body = (f"{target['summary']}\n\nCandidate: `{data['candidate']['sha256']}`\n"
                    f"Contract: `{data['acceptance_sha256']}`\n"
                    f"Independent verdict: {data['review']['report']['verdict']}; round {data['round']}.\n"
                    f"Tests: {sum(v['counts']['tests'] for v in data['verification'])}; "
                    f"skipped: {sum(v['counts']['skipped'] for v in data['verification'])}.\n\n{marker}")
            try:
                self.api(f"repos/{self.repository}/pulls", {
                    "title": target["title"], "head": target["branch"], "base": target["base"], "body": body})
            except Blocked:
                pass  # A lost POST receipt is resolved by GET, never another blind POST.
            item = readback()
        if item is None:
            store.finish(op, "UNKNOWN")
            raise Blocked("PR creation not confirmed; inspect before explicit resume")
        receipt = {"number": item["number"], "url": item["html_url"], "head": item["head"]["sha"]}
        store.finish(op, "CREATED", **receipt)
        return receipt


def deliver_github(store, run, client):
    """Caller holds run/source leases and rechecks all Controller gates."""
    data = store.get(run)["data"]
    target = data["config"].get("github_delivery")
    required = {"root", "branch", "repository", "base", "expected_tip", "title", "summary", "existing_pr"}
    if not isinstance(target, dict) or set(target) != required or target["repository"] != client.repository:
        raise Blocked("Missing bound GitHub delivery contract")
    client.branch(target["branch"])
    if target["base"] != "main" or target["root"] != data["source"]["root"] or target["branch"] != data["source"]["branch"]:
        raise Blocked("GitHub source or base binding mismatch")
    if not data["config"]["policy"]["delivery"]["push"]:
        raise Blocked("GitHub push and PR creation were not authorized")
    if git(target["root"], "status", "--porcelain=v1", "--untracked-files=all"):
        raise Blocked("Original source has local changes")
    remote = git(target["root"], "remote", "get-url", "origin")
    if remote not in (f"https://github.com/{client.repository}.git", f"https://github.com/{client.repository}",
                       f"git@github.com:{client.repository}.git"):
        raise Blocked("GitHub remote does not match authorization")
    pending = {}
    try:
        tree = make_tree(target["root"], data["candidate_path"])
        if committed_manifest_hash(target["root"], tree) != data["candidate"]["sha256"] or tree_hash(data["candidate_path"]) != data["candidate"]["sha256"]:
            raise Blocked("Prospective Git tree differs from reviewed candidate")
        if store.get(run)["data"].get("cancel_requested"):
            raise Blocked("Delivery cancelled")
        sha = commit(store, run, target, tree)
        pending = {"commit": sha, "tree": tree, "pushed": False, "pr": None}
        store.transition(run, "PUSHING", github_receipt=pending)
        if store.get(run)["data"].get("cancel_requested"):
            raise Blocked("Delivery cancelled after local commit")
        client.push(store, run, target, sha)
        pending["pushed"] = True
        store.transition(run, "PUSHING", github_receipt=pending)
        if store.get(run)["data"].get("cancel_requested"):
            raise Blocked("Delivery cancelled after push")
        pending["pr"] = client.pr(store, run, target, sha)
        store.transition(run, "COMPLETED", github_receipt=pending)
        return pending
    except (Blocked, OSError, ValueError) as exc:
        store.transition(run, "CANCELLED" if store.get(run)["data"].get("cancel_requested") else
                         "PARTIAL_DELIVERY" if pending else "BLOCKED",
                         github_receipt=pending, reason=str(exc))
        raise
