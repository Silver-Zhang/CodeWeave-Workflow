"""Parent-owned assertions; browser data can select, never define, commands."""
from pathlib import Path, PurePosixPath
import re
from .graph import Invalid
from orchestration.common import digest


def relative(value):
    if not isinstance(value, str) or not value or len(value) > 300 or '\\' in value or '\0' in value:
        raise Invalid('Invalid verification path')
    p = PurePosixPath(value)
    if p.is_absolute() or any(x in ('..', '.git') for x in p.parts) or not p.parts:
        raise Invalid('Verifier target must be a source-relative path')
    return value


def validate_profiles(profiles):
    if not isinstance(profiles, dict) or len(profiles) > 32:
        raise Invalid('Verification profiles must be an operator-registered mapping')
    for name, cases in profiles.items():
        if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,63}', name):
            raise Invalid('Invalid verification profile identity')
        if not isinstance(cases, list) or not 1 <= len(cases) <= 100:
            raise Invalid('A verification profile requires 1 to 100 actual assertions')
        ids = set()
        for case in cases:
            if not isinstance(case, dict) or set(case) != {'id', 'argv', 'stdin', 'expected_json', 'read_paths'}:
                raise Invalid('Unexpected operator assertion fields')
            if not isinstance(case['id'], str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,63}', case['id']) or case['id'] in ids:
                raise Invalid('Assertion IDs must be unique')
            ids.add(case['id'])
            argv = case['argv']
            if not isinstance(argv, list) or not argv or len(argv) > 100 or any(not isinstance(x, str) or not x or '\0' in x for x in argv):
                raise Invalid('Operator assertion argv required')
            if not Path(argv[0]).is_absolute():
                raise Invalid('Assertion executable must be an explicit absolute path')
            if not isinstance(case['stdin'], str) or len(case['stdin']) > 60000:
                raise Invalid('Bounded assertion input required')
            paths = case['read_paths']
            if not isinstance(paths, list) or len(paths) > 20 or any(not isinstance(x, str) or not Path(x).is_absolute() for x in paths):
                raise Invalid('Assertion dependencies require explicit absolute files')
    return profiles


def specifications(node, profiles):
    c = node['config']
    if c['profile'] != 'json-assertions':
        return [specification(node)]
    validate_profiles(profiles)
    if c['target'] not in profiles or c['pattern'] or c['max_skipped'] != 0:
        raise Invalid('Select an operator-registered assertion profile; patterns and skipped assertions are unsupported')
    cases = profiles[c['target']]
    if len(cases) < c['min_cases']:
        raise Invalid('Registered profile has fewer assertions than the required minimum')
    return [dict(id=node['id'] if len(cases) == 1 else node['id'] + '-' + case['id'],
                 argv=case['argv'][:], stdin=case['stdin'], expected_json=case['expected_json'],
                 read_paths=case['read_paths'][:],
                 dependency_sha256={path: digest(Path(path).read_bytes()) for path in [case['argv'][0], *case['read_paths']]},
                 runner='json-assertion', result_format='controller-json',
                 min_cases=1, max_skipped=0) for case in cases]


def specification(node):
    c = node['config']
    if c['min_cases'] != 1 or c['max_skipped'] != 0:
        raise Invalid('A syntax/baseline command is exactly one check with no skipped checks')
    target = relative(c['target'])
    if c['pattern']:
        raise Invalid('These verification profiles do not use a test discovery pattern')
    if c['profile'] == 'baseline':
        argv = ['python3', '-I', 'tools/devflower.py', 'check', '--baseline']
    elif c['profile'] == 'javascript':
        if not target.endswith(('.js', '.cjs', '.mjs')):
            raise Invalid('JavaScript verifier requires a JavaScript file')
        argv = ['node', '--check', '--', target]
    else:
        raise Invalid('Candidate in-process unittest counters cannot establish trusted verification; choose registered JSON assertions')
    return dict(id=node['id'], argv=argv, result_format='controller-json', min_cases=c['min_cases'],
                max_skipped=c['max_skipped'], runner='exit-code')
