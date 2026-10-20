"""Versioned canvas -> existing B-mode task, without issuing any authorization.

Only the execution grammar supported by v0.2-A is accepted. Coordinates are UI
metadata; verification order and node parameters really change the exported task.
"""
from __future__ import annotations
import copy
import hashlib
import json
import math
import re

PROFILE = 'b-dual-review-v1'
KINDS = ('authorization', 'implementer', 'freeze', 'verification', 'reviewer', 'gate', 'delivery')
FIXED = tuple(k for k in KINDS if k != 'verification')
ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,79}\Z')


class Invalid(ValueError):
    """Invalid or unsupported Studio document."""


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def text(value, limit=500):
    if not isinstance(value, str) or len(value) > limit or any(ord(c) < 32 and c not in '\n\t' for c in value):
        raise Invalid('Invalid or oversized text field')
    return value


def integer(value, low, high):
    if type(value) is not int or not low <= value <= high:
        raise Invalid(f'Expected integer in [{low}, {high}]')
    return value


def shape(obj, keys):
    if not isinstance(obj, dict) or set(obj) != set(keys):
        raise Invalid('Unexpected or missing document fields')


def validate(document):
    shape(document, ('schema_version', 'profile', 'name', 'goal', 'limits', 'nodes', 'edges'))
    if type(document['schema_version']) is not int or document['schema_version'] != 1 or document['profile'] != PROFILE:
        raise Invalid('Only schema 1 / B dual-review is executable; A/C governance remains external')
    text(document['name'], 120); text(document['goal'], 16000)
    shape(document['limits'], ('max_review_rounds', 'max_infrastructure_retries', 'step_timeout_seconds', 'max_log_bytes'))
    for key, bounds in {'max_review_rounds': (1, 5), 'max_infrastructure_retries': (0, 2),
                        'step_timeout_seconds': (30, 86400), 'max_log_bytes': (4096, 67108864)}.items():
        integer(document['limits'][key], *bounds)
    nodes, edges = document['nodes'], document['edges']
    if not isinstance(nodes, list) or not 7 <= len(nodes) <= 26 or not isinstance(edges, list) or len(edges) > 40:
        raise Invalid('Expected six fixed nodes and 1–20 verification nodes')
    by_id, kinds = {}, {k: [] for k in KINDS}
    for node in nodes:
        shape(node, ('id', 'type', 'label', 'x', 'y', 'config'))
        if not isinstance(node['id'], str) or not ID.fullmatch(node['id']) or node['id'] in by_id or node['type'] not in kinds:
            raise Invalid('Duplicate/unsafe node ID or unsupported node type')
        if node['type'] in FIXED and node['id'] != node['type']:
            raise Invalid('Fixed node identities are reserved')
        text(node['label'], 120)
        for key in ('x', 'y'):
            if type(node[key]) not in (int, float) or not math.isfinite(node[key]) or not 0 <= node[key] <= 10000:
                raise Invalid('Invalid canvas coordinate')
        config = node['config']
        if node['type'] in ('implementer', 'reviewer'):
            shape(config, ('model', 'effort'))
            if not text(config['model'], 160).strip() or not text(config['effort'], 40).strip():
                raise Invalid('Use explicit values or unknown for model/effort')
        elif node['type'] == 'verification':
            shape(config, ('id', 'argv', 'result_format', 'min_cases', 'max_skipped'))
            if not isinstance(config['id'], str) or not ID.fullmatch(config['id']):
                raise Invalid('Invalid verification ID')
            if not isinstance(config['argv'], list) or not 1 <= len(config['argv']) <= 80:
                raise Invalid('Verification argv must be an array, never a shell string')
            for arg in config['argv']:
                if not text(arg, 2000):
                    raise Invalid('Empty command argument')
            if not any('{result}' in a for a in config['argv']) or config['result_format'] not in ('junit', 'controller-json'):
                raise Invalid('Verification must bind {result} and a supported result format')
            integer(config['min_cases'], 1, 1000000); integer(config['max_skipped'], 0, 1000000)
        else:
            shape(config, ())
        by_id[node['id']] = node
        kinds[node['type']].append(node['id'])
    if any(len(kinds[k]) != 1 for k in FIXED) or not kinds['verification']:
        raise Invalid('Authorization, implementation, freeze, review, gate and delivery are mandatory')
    next_nodes, incoming, repairs = {}, {}, []
    for edge in edges:
        shape(edge, ('source', 'target', 'on'))
        source, target = edge['source'], edge['target']
        if source not in by_id or target not in by_id or edge['on'] not in ('next', 'repair'):
            raise Invalid('Dangling or unsupported edge')
        if edge['on'] == 'repair':
            repairs.append((source, target)); continue
        if source in next_nodes or target in incoming:
            raise Invalid('Parallel branches are not supported by the current engine')
        next_nodes[source] = target; incoming[target] = source
    if repairs != [(kinds['gate'][0], kinds['implementer'][0])]:
        raise Invalid('Exactly one bounded gate → implementer repair edge is required')
    order, current = [], kinds['authorization'][0]
    while current is not None:
        if current in order:
            raise Invalid('Unbounded cycle')
        order.append(current); current = next_nodes.get(current)
    if set(order) != set(by_id) or len(next_nodes) != len(nodes) - 1:
        raise Invalid('Disconnected nodes or missing execution edges')
    types = [by_id[n]['type'] for n in order]
    expected = ['authorization', 'implementer', 'freeze'] + ['verification'] * len(kinds['verification']) + ['reviewer', 'gate', 'delivery']
    if types != expected:
        raise Invalid('Unsupported order or attempted bypass of freeze/verification/review/gate')
    tests = [by_id[n]['config']['id'] for n in order if by_id[n]['type'] == 'verification']
    if len(set(tests)) != len(tests):
        raise Invalid('Verification IDs must be unique')
    return order


def template():
    nodes = []
    labels = ['任务授权', 'Codex · 实施', '冻结候选', '必需测试', 'Claude Code · 审核', '确定性门禁', '受控交付']
    for index, (kind, label) in enumerate(zip(KINDS, labels)):
        config = {'model': 'unknown', 'effort': 'unknown'} if kind in ('implementer', 'reviewer') else {}
        if kind == 'verification':
            config = {'id': 'unit', 'argv': ['python3', '-m', 'pytest', 'tests', '--junitxml', '{result}'],
                      'result_format': 'junit', 'min_cases': 1, 'max_skipped': 0}
        nodes.append(dict(id=kind, type=kind, label=label, x=60 + (index % 4) * 270,
                          y=110 + (index // 4) * 220, config=config))
    edges = [dict(source=a, target=b, on='next') for a, b in zip(KINDS, KINDS[1:])]
    edges.append(dict(source='gate', target='implementer', on='repair'))
    return dict(schema_version=1, profile=PROFILE, name='B 模式 · 双 Agent 研发', goal='',
                limits=dict(max_review_rounds=5, max_infrastructure_retries=2,
                            step_timeout_seconds=1800, max_log_bytes=16777216), nodes=nodes, edges=edges)


def compile_task(document, task):
    """Emit an unauthorised task candidate, retaining all operator-bound fields."""
    order = validate(document)
    if not isinstance(task, dict) or task.get('policy', {}).get('mode') != 'B':
        raise Invalid('Import a complete B-mode task first; A/C are not silently converted')
    result = copy.deepcopy(task)
    by_id = {n['id']: n for n in document['nodes']}
    for role in ('implementer', 'reviewer'):
        node = next(n for n in by_id.values() if n['type'] == role)
        result['bindings'][role].update(node['config'])
    result['goal'] = document['goal']
    result['policy']['limits'] = copy.deepcopy(document['limits'])
    result['policy']['verification'] = [copy.deepcopy(by_id[n]['config']) for n in order if by_id[n]['type'] == 'verification']
    if {v['id'] for v in task['policy']['verification']} - {v['id'] for v in result['policy']['verification']}:
        raise Invalid('Canvas cannot remove previously required verification IDs')
    # Existing mandatory contracts are never silently removed by the canvas.
    required = result['policy']['required_contracts']
    result['policy']['required_contracts'] = list(dict.fromkeys(required + [v['id'] for v in result['policy']['verification']]))
    try:
        from orchestration.contracts import config_check
        from orchestration.common import Blocked
        try:
            config_check(result)
        except Blocked as exc:
            raise Invalid('Engine configuration validation refused the task') from exc
    except ImportError as exc:
        raise Invalid('Export requires the existing DevFlower v0.2-A engine checkout') from exc
    except (ValueError, KeyError, TypeError) as exc:
        raise Invalid('The compiled task is not a valid engine configuration') from exc
    return result


def from_task(task):
    """Render the actually recorded plan, not the currently edited canvas."""
    graph = template()
    graph['name'] = str(task.get('task_id', 'Recorded run'))[:120]
    graph['goal'] = str(task.get('goal', ''))[:16000]
    graph['limits'].update(task.get('policy', {}).get('limits', {}))
    graph['nodes'] = [n for n in graph['nodes'] if n['type'] != 'verification']
    tests = task.get('policy', {}).get('verification', [])
    for i, spec in enumerate(tests):
        graph['nodes'].append(dict(id=f'verify-{i}', type='verification', label=str(spec.get('id', 'Test'))[:120],
                                   x=870 + i * 250, y=110, config=copy.deepcopy(spec)))
    for n in graph['nodes']:
        if n['type'] in ('implementer', 'reviewer'):
            binding = task.get('bindings', {}).get(n['type'], {})
            n['config'] = {k: str(binding.get(k, 'unknown'))[:160] for k in ('model', 'effort')}
    order = ['authorization', 'implementer', 'freeze'] + [f'verify-{i}' for i in range(len(tests))] + ['reviewer', 'gate', 'delivery']
    graph['edges'] = [dict(source=a, target=b, on='next') for a, b in zip(order, order[1:])]
    graph['edges'].append(dict(source='gate', target='implementer', on='repair'))
    return graph
