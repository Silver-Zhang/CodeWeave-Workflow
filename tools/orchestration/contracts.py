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


def config_check(config):
    require_keys(config, ('task_id', 'project', 'source', 'acceptance', 'goal', 'scope', 'excludes', 'policy', 'bindings'), ('delivery_targets', 'prior_reviews'))
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
    require_keys(config['bindings'], ('implementer', 'reviewer'))
    for role, binding in config['bindings'].items():
        require_keys(binding, ('project', 'role', 'executable', 'home', 'read_paths', 'model', 'effort', 'session_id'), ('isolation', 'external_sandbox'))
        if binding.get('isolation', 'landlock') not in ('landlock', 'bwrap'):
            raise Blocked('unknown isolation backend')
        if type(binding.get('external_sandbox', False)) is not bool or binding.get('external_sandbox') and (
                role != 'implementer' or binding.get('isolation') != 'bwrap'):
            raise Blocked('external CLI sandbox requires explicit outer bwrap implementer binding')
        if binding['project'] != config['project'] or binding['role'] != role:
            raise Blocked('cross-project/role session binding')
        if binding['session_id'] is not None:
            try:
                uuid.UUID(binding['session_id'])
            except (ValueError, TypeError):
                raise Blocked('explicit session UUID required') from None
        if config['policy']['agents'][role]['session_policy'] == 'resume-bound' and not binding['session_id']:
            raise Blocked('resume requires bound UUID')
        if config['policy']['agents'][role]['session_policy'] == 'new' and binding['session_id'] is not None:
            raise Blocked('new-session policy cannot resume a supplied UUID')
        if not Path(binding['executable']).is_absolute() or not Path(binding['home']).is_absolute():
            raise Blocked('absolute executable and dedicated runtime home required')
        if not isinstance(binding['read_paths'], list):
            raise Blocked('read_paths required')
    return config


def authorized(config, authorization):
    config_check(config)
    auth = load(authorization)
    require_keys(auth, ('config_sha256', 'acceptance_sha256', 'controller_sha256', 'source', 'head', 'branch',
                        'approval_ref', 'external_source_approved', 'commit', 'push'), ('human_events',))
    if config['policy']['mode'] == 'C':
        events = auth.get('human_events', [])
        if len(events) != 4 or {x.get('gate') for x in events} != {'G1', 'G2', 'G3', 'G4'} or any(
                x.get('actor') != 'user' or not isinstance(x.get('evidence_ref'), str) or not x['evidence_ref'].strip() for x in events):
            raise Blocked('C requires operator-bound actual human G1-G4 evidence')
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
