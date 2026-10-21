"""Editable starting templates compiled to a bounded sequential execution plan.

Draft validation is separate from execution validation. Safety transitions are
owned by the trusted runtime and cannot be removed by changing canvas edges.
"""
from __future__ import annotations

import copy
import re

from .graph import Invalid, canonical, digest, integer, text

KINDS = ("human_gate", "planner", "developer", "verifier", "reviewer", "delivery")
AGENTS = {"planner", "developer", "reviewer"}
IDENTIFIER = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,63}\Z")
PROFILES = ("json-assertions", "baseline", "javascript")
TOOLS = {"codex": ["native"], "claude": ["Read", "Glob", "Grep", "Bash", "Write", "Edit"]}


def node(kind, identity=None):
    if kind not in KINDS:
        raise Invalid("Unsupported node kind")
    config = {}
    if kind in AGENTS:
        provider = "claude" if kind == "reviewer" else "codex"
        config = dict(provider=provider, profile="default-" + provider, session="new",
                      model="unknown", effort="unknown", responsibility=kind,
                      background="", tools=TOOLS[provider][:], subagents=False,
                      timeout_seconds=1800)
    elif kind == "verifier":
        config = dict(profile="json-assertions", target="default", pattern="",
                      min_cases=1, max_skipped=0)
    elif kind == "human_gate":
        config = {"question": "请确认本次任务范围、允许修改路径、外部模型使用及交付权限，并说明你的确认意见。"}
    return dict(id=identity or kind, type=kind, label=kind.replace("_", " ").title(),
                x=80, y=100, config=config)


def template(kind="B"):
    if kind not in ("A", "B", "C", "blank"):
        raise Invalid("Unknown starting template")
    nodes = []
    if kind != "blank":
        for i in range(3 if kind == "C" else 1):
            n = node("human_gate", f"human-{i + 1}")
            if kind == "C":
                n["config"]["question"] = [
                    "G1：请说明问题、任务边界与成功判据。",
                    "G2：请说明要验证的解释及替代方案。",
                    "G3：请说明什么实验结果可以证伪当前解释。",
                    "G4：请解释实际结果及适用边界。",
                ][i]
            nodes.append(n)
        if kind != "A":
            nodes.append(node("planner"))
        nodes += [node(k) for k in ("developer", "verifier", "reviewer")]
        if kind == "C":
            final = node("human_gate", "human-4")
            final["config"]["question"] = "G4：请审阅本轮实际结果，解释其意义和边界，并确认这个固定候选。"
            nodes.append(final)
        nodes.append(node("delivery"))
    for i, n in enumerate(nodes):
        n.update(x=60 + (i % 4) * 240, y=100 + (i // 4) * 180)
    edges = [dict(source=a["id"], target=b["id"], on="next") for a, b in zip(nodes, nodes[1:])]
    if nodes:
        edges.append(dict(source="reviewer", target="developer", on="repair"))
    return dict(version=2, name="自定义工作流" if kind == "blank" else f"{kind} 起始模板（可编辑）", template=kind,
                max_rounds=5, nodes=nodes, edges=edges)


def draft(document):
    if not isinstance(document, dict) or set(document) != {
        "version", "name", "template", "max_rounds", "nodes", "edges"
    }:
        raise Invalid("Unexpected workflow fields")
    if type(document["version"]) is not int or document["version"] not in (1, 2) or document["template"] not in ("A", "B", "C", "blank"):
        raise Invalid("Unsupported workflow version/template")
    text(document["name"], 120)
    integer(document["max_rounds"], 1, 5)
    if not isinstance(document["nodes"], list) or len(document["nodes"]) > 24:
        raise Invalid("At most 24 nodes are supported")
    if not isinstance(document["edges"], list) or len(document["edges"]) > 32:
        raise Invalid("At most 32 edges are supported")
    ids = set()
    for n in document["nodes"]:
        if not isinstance(n, dict) or set(n) != {"id", "type", "label", "x", "y", "config"}:
            raise Invalid("Unexpected node fields")
        if not isinstance(n["id"], str) or not IDENTIFIER.fullmatch(n["id"]) or n["id"] in ids:
            raise Invalid("Node IDs must be unique simple identifiers")
        ids.add(n["id"])
        if n["type"] not in KINDS:
            raise Invalid("Unsupported node type")
        text(n["label"], 120)
        for axis in ("x", "y"):
            integer(n[axis], 0, 10000)
        c = n["config"]
        if not isinstance(c, dict):
            raise Invalid("Node configuration must be an object")
        if n["type"] in AGENTS:
            if set(c) != {"provider", "profile", "session", "model", "effort", "responsibility",
                          "background", "tools", "subagents", "timeout_seconds"}:
                raise Invalid("Unexpected Agent fields")
            for key, limit in (("provider", 20), ("profile", 80), ("session", 80),
                               ("model", 160), ("effort", 40), ("responsibility", 4000), ("background", 12000)):
                text(c[key], limit)
            if c["provider"] not in TOOLS or type(c["subagents"]) is not bool:
                raise Invalid("Unsupported provider/capability")
            if not isinstance(c["tools"], list) or len(c["tools"]) > 8 or any(
                    not isinstance(t, str) or t not in TOOLS[c["provider"]] for t in c["tools"]):
                raise Invalid("Unsupported tool capability")
            integer(c["timeout_seconds"], 30, 3600)
        elif n["type"] == "verifier":
            if set(c) != {"profile", "target", "pattern", "min_cases", "max_skipped"}:
                raise Invalid("Unexpected verification fields")
            if c["profile"] not in PROFILES:
                raise Invalid("Verifier must use a trusted built-in profile")
            text(c["target"], 300); text(c["pattern"], 100)
            integer(c["min_cases"], 1, 1000000); integer(c["max_skipped"], 0, 1000000)
        elif n["type"] == "human_gate":
            if set(c) != {"question"}:
                raise Invalid("Unexpected Human Gate fields")
            text(c["question"], 2000)
        elif c:
            raise Invalid("Delivery permissions are granted in the separate human authorization")
    for e in document["edges"]:
        if not isinstance(e, dict) or set(e) != {"source", "target", "on"}:
            raise Invalid("Unexpected edge fields")
        if e["source"] not in ids or e["target"] not in ids or e["on"] not in ("next", "repair"):
            raise Invalid("Dangling or unsupported edge")
    if len(canonical(document)) > 128000:
        raise Invalid("Workflow exceeds the size budget")
    return copy.deepcopy(document)


def compile_plan(document):
    document = draft(document)
    nodes = {n["id"]: n for n in document["nodes"]}
    outgoing, incoming, repairs = {}, {}, []
    for e in document["edges"]:
        if e["on"] == "repair":
            repairs.append((e["source"], e["target"]))
            continue
        if e["source"] in outgoing or e["target"] in incoming:
            raise Invalid("Only sequential graphs are executable; parallel branches are unsupported")
        outgoing[e["source"]] = e["target"]
        incoming[e["target"]] = e["source"]
    roots = set(nodes) - set(incoming)
    if len(roots) != 1:
        raise Invalid("Exactly one connected sequential graph is required")
    order, current = [], next(iter(roots))
    while current is not None:
        if current in order:
            raise Invalid("Unbounded workflow cycle")
        order.append(current)
        current = outgoing.get(current)
    if len(order) != len(nodes):
        raise Invalid("Disconnected workflow")
    kinds = [nodes[n]["type"] for n in order]
    cursor = 0
    while cursor < len(kinds) and kinds[cursor] == "human_gate":
        cursor += 1
    initial_gates = order[:cursor]
    if document["version"] == 1:
        # Immutable legacy runs retain their exact historical authorization rules.
        required_gates = 3 if document["template"] == "C" else 1
        if cursor != required_gates:
            raise Invalid(f"Legacy workflow requires {required_gates} initial Human Gate(s); migrate the draft before editing")
    elif not initial_gates:
        raise Invalid("At least one explicit initial authorization node is required, independently of templates")
    if cursor < len(kinds) and kinds[cursor] == "planner":
        cursor += 1
    if kinds[cursor:cursor + 1] != ["developer"]:
        raise Invalid("One Developer must follow the authorization and optional Planner")
    cursor += 1
    first_test = cursor
    while cursor < len(kinds) and kinds[cursor] == "verifier":
        cursor += 1
    if cursor == first_test or kinds[cursor:cursor + 1] != ["reviewer"]:
        raise Invalid("Developer → nonzero verification → independent Reviewer is mandatory")
    cursor += 1
    result_start = cursor
    while cursor < len(kinds) and kinds[cursor] == "human_gate":
        cursor += 1
    result_gates = order[result_start:cursor]
    if kinds[cursor:] != ["delivery"]:
        raise Invalid("Only explicit result-confirmation nodes may occur between Reviewer and Delivery")
    if document["version"] == 1 and len(result_gates) != (1 if document["template"] == "C" else 0):
        raise Invalid("Legacy result gates cannot be changed without migrating the draft")
    if document["version"] == 2 and any(not nodes[key]["config"]["question"].strip()
                                        for key in initial_gates + result_gates):
        raise Invalid("Each authorization/result node requires a nonempty human question")
    developer = next(n for n in nodes.values() if n["type"] == "developer")
    reviewer = next(n for n in nodes.values() if n["type"] == "reviewer")
    if repairs != [(reviewer["id"], developer["id"])]:
        raise Invalid("Exactly one bounded Reviewer → Developer repair edge is required")
    for n in nodes.values():
        if n["type"] in AGENTS:
            c = n["config"]
            if c["subagents"]:
                raise Invalid("Sub-agent delegation is not supported by this execution profile")
            if not c["tools"] or len(set(c["tools"])) != len(c["tools"]):
                raise Invalid("At least one supported non-duplicate tool is required")
            if c["provider"] == "codex" and c["tools"] != ["native"]:
                raise Invalid("Codex supports the native tool set inside the outer sandbox only")
            if n["type"] == "developer" and c["provider"] != "codex":
                raise Invalid("Developer execution currently supports Codex")
            if n["type"] == "reviewer" and c["provider"] != "claude":
                raise Invalid("Independent Reviewer execution currently supports Claude Code")
    return {"document": document, "order": order, "sha256": digest(document),
            "max_rounds": document["max_rounds"], "initial_gates": initial_gates,
            "result_gates": result_gates,
            "runtime_gates": ["freeze", "verify", "independent-review", "delivery"]}


def governance(plan):
    """Derive authority from nodes, never from a v2 template's provenance label.

    Engine mode B is a backward-compatible serialization value for v2, not a
    selectable product mode. v1 is interpreted unchanged for existing runs.
    """
    document = plan["document"]
    nodes = {n["id"]: n for n in document["nodes"]}
    if document["version"] == 1:
        mode = "B" if document["template"] == "blank" else document["template"]
        result_policy = ({"mode": "deferred-G4", "question": nodes[plan["result_gates"][0]]["config"]["question"]}
                         if plan["result_gates"] else None)
    else:
        mode = "B"
        result_policy = ({"mode": "node-results", "gates": [
            {"id": key, "question": nodes[key]["config"]["question"]} for key in plan["result_gates"]]}
            if plan["result_gates"] else None)
    return {"mode": mode, "result_policy": result_policy}


def upgrade_draft(document):
    """Explicit copy for editing only; never migrate a stored run/authorization."""
    value = draft(document)
    value["version"] = 2
    return value
