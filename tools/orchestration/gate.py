"""Mechanical gate: model text, format and exit zero never authorize delivery."""
from .common import Blocked
from .contracts import schema, validate


def gate(run, round_number, candidate, acceptance, required, verification, implementation, review, history=(), expected_verification=None):
    report = review['report']
    validate(report, schema('review-result'))
    if report['run_id'] != run or report['round'] != round_number or report['candidate_sha256'] != candidate or report['acceptance_sha256'] != acceptance:
        raise Blocked('stale or cross-run review')
    for result in (implementation, review):
        proc = result['process']
        if proc['exit'] != 0 or any(proc[k] for k in ('timeout', 'overflow', 'cancelled')) or not result['session_id']:
            raise Blocked('unsuccessful actual agent process')
    if implementation['session_id'] == review['session_id']:
        raise Blocked('roles must have distinct sessions')
    if implementation['report'].get('status') != 'IMPLEMENTED':
        raise Blocked('implementer did not finish')
    ids = [v['id'] for v in verification]
    expected = expected_verification if expected_verification is not None else required
    specs = {x['id']: x for x in expected if isinstance(x, dict)}
    expected_ids = [x['id'] if isinstance(x, dict) else x for x in expected]
    if len(ids) != len(set(ids)) or set(ids) != set(expected_ids):
        raise Blocked('missing or duplicate verification')
    for v in verification:
        if not v['passed'] or v['run_id'] != run or v['round'] != round_number or v['candidate_sha256'] != candidate or v['acceptance_sha256'] != acceptance:
            raise Blocked('required verification failed or stale')
        c, p = v.get('counts', {}), v.get('process', {})
        spec = specs.get(v['id'], {'min_cases': 1, 'max_skipped': 0})
        if set(c) != {'tests', 'failures', 'errors', 'skipped'} or any(type(x) is not int or x < 0 for x in c.values()):
            raise Blocked('invalid verification counters')
        if c['tests'] < spec['min_cases'] or c['skipped'] > spec['max_skipped'] or c['failures'] or c['errors'] or sum(c[x] for x in ('failures', 'errors', 'skipped')) > c['tests']:
            raise Blocked('verification contradicts PASS flag')
        if p.get('exit') != 0 or any(p.get(k, True) for k in ('timeout', 'overflow', 'cancelled')):
            raise Blocked('actual verifier process did not succeed')
    contracts = report['contracts']
    if len({c['id'] for c in contracts}) != len(contracts):
        raise Blocked('duplicate review contract')
    by_id = {c['id']: c for c in contracts}
    if set(required) - by_id.keys() or any(by_id[x]['status'] != 'PASS' or not by_id[x]['evidence_refs'] for x in required):
        raise Blocked('required contracts not independently passed')
    evidence_ids = set(ids) | {'source-inspection'}
    if any(ref not in evidence_ids for c in contracts for ref in c['evidence_refs']):
        raise Blocked('unknown review evidence reference')
    if report['verdict'] != 'ACCEPT':
        raise Blocked('review verdict: ' + report['verdict'])
    if any(c['status'] in ('FAIL', 'BLOCKED') for c in contracts):
        raise Blocked('contradictory ACCEPT')
    findings = {f['id']: f for f in report['findings']}
    if len(findings) != len(report['findings']):
        raise Blocked('duplicate finding')
    mandatory = lambda f: f['severity'] in ('P0', 'P1') or f['severity'] == 'P2' and bool(set(f['contract_ids']) & set(required))
    if any(mandatory(f) and f['status'] != 'CLOSED' for f in findings.values()):
        raise Blocked('open required finding')
    for old in history:
        for f in old['findings']:
            if mandatory(f) and f['status'] != 'CLOSED' and (f['id'] not in findings or findings[f['id']]['status'] != 'CLOSED' or not findings[f['id']]['evidence_refs']):
                raise Blocked('historical required finding not closed')
    return True
