"""Real HTTP/Chromium UI regressions with SQLite fixtures, not model acceptance."""
import argparse
from http.server import ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import sys
import threading

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from test_usable import RuntimeTests
from test_studio import database_fixture
from studio.usable_server import handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chromium", required=True)
    parser.add_argument("--node", default="node")
    parser.add_argument("--playwright-module", default="playwright")
    parser.add_argument("--artifacts", required=True)
    args = parser.parse_args()
    output = Path(args.artifacts).resolve()
    root = Path(__file__).resolve().parents[1]
    if output.is_relative_to(root) or root.is_relative_to(output):
        parser.error("Artifacts must be outside source")
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    fixture = RuntimeTests()
    fixture.setUp()
    runtime = fixture.runtime
    # Fixed GitHub data for preview-only HTTP/Chromium tests; no model or delivery.
    runtime.github.api = lambda *args, **kwargs: [dict(number=42)]
    runtime.github.tip = lambda *args: "f" * 40
    db, run_a, data = database_fixture(runtime.control, state="READY")
    data["config"]["project"] = fixture.project["id"]
    data["source"] = {"root": str(fixture.source)}
    data["acceptance_sha256"] = "c" * 64
    data["config"]["bindings"] = {}
    data["sessions"] = {}
    data["round"] = data["candidate_round"] = 1
    data["review"] = {"report": {"round": 1, "verdict": "ACCEPT", "findings": []}}
    db.execute("UPDATE runs SET data=? WHERE id=?", (json.dumps(data), run_a))
    run_b = "b" * 32
    other = json.loads(json.dumps(data))
    other["round"] = other["candidate_round"] = 2
    other["review"]["report"].update(round=2, verdict="BLOCKED")
    db.execute("INSERT INTO runs VALUES(?,?,?)", (run_b, "BLOCKED", json.dumps(other)))
    db.commit();db.close()
    token = "test-fixture-only-capability-not-a-real-operator-permit"
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler(runtime, token))
    thread = threading.Thread(target=server.serve_forever, daemon=True);thread.start()
    (output / "access.json").write_text(json.dumps(dict(
        url=f"http://127.0.0.1:{server.server_port}/", token=token, source=str(fixture.source), a=run_a, b=run_b)))
    try:
        result = subprocess.run([args.node, str(Path(__file__).with_suffix(".cjs")), str(output)],
                                env=dict(os.environ, CHROMIUM=args.chromium, PLAYWRIGHT_MODULE=args.playwright_module),
                                timeout=180)
        return result.returncode
    finally:
        server.shutdown();server.server_close();thread.join()
        fixture.doCleanups()


if __name__ == "__main__":
    raise SystemExit(main())
