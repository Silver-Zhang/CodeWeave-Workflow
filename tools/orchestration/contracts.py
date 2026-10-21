"""Strict validation for the shipped contracts and locally approved bindings."""
from pathlib import Path
import re
import uuid
from .common import Blocked, canonical, controller_hash, digest, identity, load, relative

DESIGN = Path(__file__).resolve().parents[2] / 'docs/design/v0.2-a'


def validate(value, schema, path='$'):
    """Small closed subset used by our two schemas; unsupported keywords fail closed."""
    supported = {'$schema', 'title', 'description', 'type', 'const', 'enum', 'required', 'properties',
                 'additionalProperties', 'items', 'minItems', 'uniqueItems', 'minLength', 'pattern',
                 'minimum', 'maximum', 'allOf', 'if', 'then'}
    if set(schema) - supported:
        raise Blocked('unsupported schema keyword')
    types = {'object': dict, 'array': list, 'string': str, 'integer': int, 'boolean': bool}
    if 'type' in schema and type(value) is not types[schema['type']]:
        raise Blocked(path + ': wrong type')
    if 'const' in schema and value != schema['const'] or 'enum' in schema and value not in schema['enum']:
        raise Blocked(path + ': invalid value')
    if isinstance(value, dict):
        if set(schema.get('required', ())) - value.keys():
            raise Blocked(path + ': missing fields')
        props = schema.get('properties', {})
        if schema.get('additionalProperties') is False and value.keys() - props.keys():
            raise Blocked(path + ': unknown fields')
        for k in value.keys() & props.keys():
            validate(value[k], props[k], path + '.' + k)
    if isinstance(value, list):
        if len(value) < schema.get('minItems', 0):
            raise Blocked(path + ': too few items')
        if schema.get('uniqueItems') and len({canonical(x) for x in value}) != len(value):
            raise Blocked(path + ': duplicate items')
        for x in value:
            if 'items' in schema:
                validate(x, schema['items'], path + '[]')
    if isinstance(value, str):
        if len(value) < schema.get('minLength', 0) or ('pattern' in schema and not re.search(schema['pattern'], value)):
            raise Blocked(path + ': invalid string')
    if type(value) is int and (value < schema.get('minimum', value) or value > schema.get('maximum', value)):
        raise Blocked(path + ': out of bounds')
    for s in schema.get('allOf', []):
        validate(value, s, path)
    if 'if' in schema:
        try:
            validate(value, schema['if'], path)
        except Blocked:
            pass
        else:
            validate(value, schema.get('then', {}), path)


def schema(name):
    return load(DESIGN / 'schemas' / (name + '.schema.json'))


def require_keys(obj, required, optional=()):
    if type(obj) is not dict or set(required) - obj.keys() or obj.keys() - set(required) - set(optional):
        raise Blocked('invalid local binding fields')


def config_check(config, *, execution=False):
    require_keys(config, ('task_id', 'project', 'source', 'acceptance', 'goal', 'scope', 'excludes', 'policy', 'bindings'), ('delivery_targets', 'prior_reviews', 'github_delivery', 'human_gate_policy', 'verification_isolation', 'studio_workflow'))
    if config.get('verification_isolation', 'landlock') not in ('landlock', 'bwrap'):
        raise Blocked('unknown verification isolation backend')
    if 'human_gate_policy' in config:
        rule = config['human_gate_policy']
        require_keys(rule, ('mode', 'question'))
        if config['policy'].get('mode') != 'C' or rule['mode'] != 'deferred-G4' or not isinstance(rule['question'], str) or not rule['question'].strip():
            raise Blocked('invalid staged C human gate policy')
    if not isinstance(config.get('prior_reviews', []), list):
        raise Blocked('prior_reviews must be an operator-bound list')
    for report in config.get('prior_reviews', []):
        validate(report, schema('review-result'))
    validate(config['policy'], schema('workflow-policy'))
    if any(not isinstance(config[x], str) or not config[x].strip() for x in ('task_id', 'project', 'goal')):
        raise Blocked('task/project/goal required')
    for key in ('scope', 'excludes'):
        if type(config[key]) is not list or (key == 'scope' and not config[key]):
            raise Blocked('path list required')
        for x in config[key]:
            relative(x)
    ids = [v['id'] for v in config['policy']['verification']]
    if len(ids) != len(set(ids)) or set(ids) - set(config['policy']['required_contracts']):
        raise Blocked('verification contract ids must be unique and required')
    for spec in config['policy']['verification']:
        runner = spec.get('runner')
        if execution and runner not in ('json-assertion', 'exit-code'):
            raise Blocked('Execution requires parent-owned assertions; legacy candidate-reported counters are read-only history')
        if runner and spec['result_format'] != 'controller-json':
            raise Blocked('Parent-owned assertions require controller-json results')
        if runner == 'json-assertion' and not {'stdin', 'expected_json', 'read_paths', 'dependency_sha256'} <= spec.keys():
            raise Blocked('JSON assertion requires bound input, expected value and dependencies')
        if not runner and any(key in spec for key in ('stdin', 'expected_json', 'read_paths', 'dependency_sha256')):
            raise Blocked('Legacy reporters cannot acquire assertion capabilities')
        if runner == 'json-assertion':
            deps = spec['dependency_sha256']
            if type(deps) is not dict or set(deps) != {spec['argv'][0], *spec['read_paths']} or any(
                    not isinstance(h, str) or not re.fullmatch(r'[0-9a-f]{64}', h) for h in deps.values()):
                raise Blocked('Verifier dependencies must have exact pinned hashes')
        if runner == 'exit-code':
            argv = spec['argv']
            baseline = argv == ['python3', '-I', 'tools/devflower.py', 'check', '--baseline']
            syntax = len(argv) == 4 and argv[:3] == ['node', '--check', '--']
            if syntax:
                relative(argv[3]);syntax = argv[3].endswith(('.js', '.cjs', '.mjs'))
            if not (baseline or syntax):
                raise Blocked('Exit-code verification only supports fixed baseline/JavaScript commands')
        for value in spec.get('read_paths', []):
            if not Path(value).is_absolute() or not Path(value).is_file() or Path(value).is_symlink():
                raise Blocked('Verifier dependency must be an absolute regular file')
    require_keys(config['bindings'], ('implementer', 'reviewer'), ('planner',))
    for role, binding in config['bindings'].items():
        require_keys(binding, ('project', 'role', 'executable', 'home', 'read_paths', 'model', 'effort', 'session_id'), ('isolation', 'external_sandbox', 'provider', 'tools',
            'responsibility', 'background', 'timeout_seconds', 'readonly_files', 'buffered_tool_transport'))
        if binding.get('isolation', 'landlock') not in ('landlock', 'bwrap'):
            raise Blocked('unknown isolation backend')
        if type(binding.get('external_sandbox', False)) is not bool or binding.get('external_sandbox') and (
                role not in ('implementer', 'planner') or binding.get('isolation') != 'bwrap'):
            raise Blocked('external CLI sandbox requires explicit outer bwrap implementer binding')
        if binding['project'] != config['project'] or binding['role'] != role:
            raise Blocked('cross-project/role session binding')
        if binding['session_id'] is not None:
            try:
                uuid.UUID(binding['session_id'])
            except (ValueError, TypeError):
                raise Blocked('explicit session UUID required') from None
        if role != 'planner' and config['policy']['agents'][role]['session_policy'] == 'resume-bound' and not binding['session_id']:
            raise Blocked('resume requires bound UUID')
        if role != 'planner' and config['policy']['agents'][role]['session_policy'] == 'new' and binding['session_id'] is not None:
            raise Blocked('new-session policy cannot resume a supplied UUID')
        if not Path(binding['executable']).is_absolute() or not Path(binding['home']).is_absolute():
            raise Blocked('absolute executable and dedicated runtime home required')
        if not isinstance(binding['read_paths'], list) or any(not isinstance(p, str) or not Path(p).is_absolute() for p in binding['read_paths']):
            raise Blocked('absolute read_paths required')
        provider = binding.get('provider', 'claude' if role == 'reviewer' else 'codex')
        if provider not in ('codex', 'claude') or role == 'reviewer' and provider != 'claude' or role == 'implementer' and provider != 'codex':
            raise Blocked('unsupported role/provider')
        if type(binding.get('buffered_tool_transport', False)) is not bool:
            raise Blocked('buffered_tool_transport must be an explicit boolean')
        if binding.get('buffered_tool_transport') and (provider != 'claude' or binding.get('isolation') != 'bwrap'):
            raise Blocked('buffered tool compatibility requires a Claude bwrap binding')
        tools = binding.get('tools', ['Read', 'Glob', 'Grep'] if provider == 'claude' else ['native'])
        allowed = {'Read', 'Glob', 'Grep', 'Bash', 'Write', 'Edit'} if provider == 'claude' else {'native'}
        if not isinstance(tools, list) or not tools or any(t not in allowed for t in tools) or len(set(tools)) != len(tools):
            raise Blocked('unsupported tools')
        if provider == 'claude' and set(tools) - {'Read', 'Glob', 'Grep'} and binding.get('isolation') != 'bwrap':
            raise Blocked('dynamic reviewer tools require mandatory outer bwrap')
        for k in ('responsibility', 'background'):
            if k in binding and (not isinstance(binding[k], str) or len(binding[k]) > 12000):
                raise Blocked('invalid role context')
        if 'timeout_seconds' in binding and (type(binding['timeout_seconds']) is not int or not 30 <= binding['timeout_seconds'] <= 3600):
            raise Blocked('invalid Agent timeout')
        files = binding.get('readonly_files', [])
        if not isinstance(files, list) or len(files) > 2 or files and binding.get('isolation') != 'bwrap':
            raise Blocked('invalid credential overlay')
        destinations = set()
        for entry in files:
            if not isinstance(entry, list) or len(entry) != 2 or not all(isinstance(p, str) for p in entry):
                raise Blocked('invalid credential overlay entry')
            src, dest = entry
            if not Path(src).is_absolute() or dest not in ('.codex/auth.json', '.claude/settings.json', '.claude/.credentials.json') or dest in destinations:
                raise Blocked('unapproved credential destination')
            destinations.add(dest)
        if any(not x.startswith('.codex/' if provider == 'codex' else '.claude/') for x in destinations):
            raise Blocked('credential provider mismatch')
    if 'studio_workflow' in config:
        studio_workflow_check(config)
    return config


def studio_workflow_check(config):
    """Bind display identity to the complete graph and existing execution contracts.

    The document never supplies executable commands, permissions or gate decisions.
    Operator-approved policy/bindings remain the sole execution authority.
    """
    from studio.usable_graph import compile_plan
    from studio.graph import Invalid
    from studio.usable_verification import specification
    value = config['studio_workflow']
    require_keys(value, ('document', 'sha256', 'verification_ids'))
    try:
        plan = compile_plan(value['document'])
    except (Invalid, ValueError, KeyError, TypeError, IndexError):
        raise Blocked('invalid studio workflow graph') from None
    if value['sha256'] != plan['sha256']:
        raise Blocked('studio workflow hash mismatch')
    nodes = {n['id']: n for n in plan['document']['nodes']}
    verifier_ids = [key for key in plan['order'] if nodes[key]['type'] == 'verifier']
    mapping = value['verification_ids']
    if type(mapping) is not dict or set(mapping) != set(verifier_ids):
        raise Blocked('studio verifier mapping coverage mismatch')
    flattened = []
    for key in verifier_ids:
        ids = mapping[key]
        if type(ids) is not list or not ids or any(not isinstance(x, str) for x in ids):
            raise Blocked('invalid studio verifier mapping')
        if len(set(ids)) != len(ids):
            raise Blocked('duplicate studio verifier mapping')
        # specifications() assigns exact node IDs for single checks, and node-ID
        # prefixes for multi-case operator profiles. Swapping ownership is invalid.
        if len(ids) == 1 and ids != [key] or len(ids) > 1 and any(
                not re.fullmatch(re.escape(key) + r'-[A-Za-z][A-Za-z0-9_-]{0,63}', x) for x in ids):
            raise Blocked('studio verifier mapping ownership mismatch')
        flattened.extend(ids)
    specs = config['policy']['verification']
    if flattened != [s['id'] for s in specs] or len(set(flattened)) != len(flattened):
        raise Blocked('studio verifier mapping differs from policy verification')
    for key in verifier_ids:
        n = nodes[key]; c = n['config']
        bound = [s for s in specs if s['id'] in mapping[key]]
        if c['profile'] == 'json-assertions':
            if c['pattern'] or c['max_skipped'] != 0 or len(bound) < c['min_cases'] or any(
                    s.get('runner') != 'json-assertion' or s['min_cases'] != 1 or s['max_skipped'] != 0 for s in bound):
                raise Blocked('studio verifier profile differs from policy')
        else:
            try:
                expected = specification(n)
            except Invalid:
                raise Blocked('invalid studio verifier profile') from None
            if bound != [expected]:
                raise Blocked('studio verifier profile differs from policy')
    mode = plan['document']['template']
    if config['policy']['mode'] != ('B' if mode == 'blank' else mode) or config['policy']['limits']['max_review_rounds'] != plan['max_rounds']:
        raise Blocked('studio workflow limits differ from policy')
    roles = {'implementer' if n['type'] == 'developer' else n['type'] for n in nodes.values()
             if n['type'] in ('developer', 'planner', 'reviewer')}
    if roles != set(config['bindings']):
        raise Blocked('studio workflow roles differ from bindings')
    return plan


def authorized(config, authorization):
    config_check(config, execution=True)
    auth = load(authorization)
    require_keys(auth, ('config_sha256', 'acceptance_sha256', 'controller_sha256', 'source', 'head', 'branch',
                        'approval_ref', 'external_source_approved', 'commit', 'push'), ('human_events',))
    if config['policy']['mode'] == 'C':
        events = auth.get('human_events', [])
        expected = {'G1', 'G2', 'G3'} if config.get('human_gate_policy') else {'G1', 'G2', 'G3', 'G4'}
        if len(events) != len(expected) or {x.get('gate') for x in events} != expected or any(
                x.get('actor') != 'user' or not isinstance(x.get('evidence_ref'), str) or not x['evidence_ref'].strip() for x in events):
            raise Blocked('C requires actual human gate evidence; deferred G4 must be completed after review')
    actual = identity(config['source'])
    checks = (auth['config_sha256'] == digest(canonical(config)),
              auth['acceptance_sha256'] == digest(Path(config['acceptance']).read_bytes()),
              auth['controller_sha256'] == controller_hash(),
              auth['source'] == actual['root'], auth['head'] == actual['head'], auth['branch'] == actual['branch'],
              isinstance(auth['approval_ref'], str) and bool(auth['approval_ref'].strip()),
              auth['external_source_approved'] is True)
    if not all(checks):
        raise Blocked('authorization binding mismatch or external-source approval absent')
    for action in ('commit', 'push'):
        if type(auth[action]) is not bool or config['policy']['delivery'][action] and not auth[action]:
            raise Blocked('delivery action not authorized')
    return auth, actual
