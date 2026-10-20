"""Safe canvas identity and current-evidence projection; never an execution gate."""
from orchestration.contracts import studio_workflow_check
from orchestration.controller import human_result_bound
from .projection import counts, liveness, sha, token


def _verification_result(info, *, final_report=False):
    counter = counts(info.get('counts'))
    if counter is not None and set(info['counts']) != set(counter):
        counter = None
    passed = (info.get('passed') is True and counter is not None and counter['tests'] > 0
              and not any(counter[k] for k in ('failures', 'errors', 'skipped')))
    if final_report:
        # VALIDATED operations already attest Controller validation. A retained
        # final report must also contain the actual successful process receipt.
        process = info.get('process')
        passed = (passed and isinstance(process, dict) and process.get('exit') == 0
                  and not any(process.get(k, True) for k in ('timeout', 'overflow', 'cancelled')))
    return counter, 'passed' if passed else 'failed'


def workflow_graph(run, snapshot, data, operations):
    config = data['config']
    plan = studio_workflow_check(config)
    workflow = config['studio_workflow']
    number = data.get('round', 0)
    state = snapshot['state']
    worker_live = any(w['alive'] for w in snapshot.get('workers', []))
    candidate = snapshot.get('candidate')
    acceptance = data.get('acceptance_sha256')
    nodes = {n['id']: n for n in plan['document']['nodes']}
    stopped = state in ('BLOCKED', 'CANCELLED', 'RECOVERY_REQUIRED', 'RECOVERING', 'PARTIAL_DELIVERY', 'UNKNOWN')

    def bound(info):
        return bool(candidate and info.get('run_id') == run and info.get('round') == number
                    and info.get('candidate_sha256') == candidate and info.get('acceptance_sha256') == acceptance)

    # Operation intents inherit the actual Controller phase/round, not the most
    # recent process with a similar role. Missing/truncated history is unconfirmed.
    operation_rounds = {}
    # Reader's public events omit operation IDs, so detailed association is
    # supplied separately by Runtime from the same read transaction.
    for operation in operations:
        if '_round' in operation:
            operation_rounds[operation['id']] = operation['_round']

    output = []
    for key in plan['order']:
        source = nodes[key]; kind = source['type']
        n = {k: source[k] for k in ('id', 'type', 'label', 'x', 'y')}
        n.update(status='pending', round=number)
        if kind == 'verifier':
            ids = workflow['verification_ids'][key]
            n.update(verification_ids=ids[:], counts=None, results=[])
            for identity in ids:
                op = next((o for o in operations if o['kind'] == 'VERIFICATION'
                           and o['data'].get('verification_id') == identity and bound(o['data'])), None)
                report = next((r for r in data.get('verification', []) if r.get('id') == identity and bound(r)), None)
                item = dict(id=identity, status='pending', counts=None, round=number)
                if op:
                    info = op['data']
                    item['operation_id'] = op['id']
                    if op['status'] == 'VALIDATED':
                        item['counts'], item['status'] = _verification_result(info)
                    elif op['status'] == 'VERIFICATION_BLOCKED':
                        item['status'] = 'blocked'
                    else:
                        proc = next((p for p in operations if p['kind'] == 'PROCESS'
                                     and p['data'].get('context', {}).get('verification_operation_id') == op['id']), None)
                        if proc and proc['status'] == 'RUNNING' and liveness(proc['data'].get('process')) == 'alive' and worker_live and state == 'VERIFYING':
                            item['status'] = 'running'
                        elif stopped or proc or op['status'] == 'EXECUTED':
                            item['status'] = 'blocked'
                elif report:
                    item['counts'], item['status'] = _verification_result(report, final_report=True)
                n['results'].append(item)
            statuses = [v['status'] for v in n['results']]
            n['status'] = next((s for s in ('failed', 'blocked', 'running', 'pending') if s in statuses), 'passed')
            counters = [r['counts'] for r in n['results'] if r['counts'] is not None]
            if counters:
                n['counts'] = {k: sum(c[k] for c in counters) for k in ('tests', 'failures', 'errors', 'skipped')}
        elif kind in ('planner', 'developer', 'reviewer'):
            role = 'implementer' if kind == 'developer' else kind
            phase = {'planner': 'PLANNING', 'developer': 'IMPLEMENTING', 'reviewer': 'REVIEWING'}[kind]
            result_key = {'planner': 'plan', 'developer': 'implementation', 'reviewer': 'review'}[kind]
            value = data.get(result_key, {})
            report = value.get('report', {})
            current = bool(value) and (bound(report) if kind == 'reviewer' else
                                       kind == 'planner' or data.get('implementation_round') == number)
            n['agent'] = dict(role=role, session_id=token(data.get('sessions', {}).get(role)),
                              requested_model=token(config['bindings'][role].get('model')),
                              requested_effort=token(config['bindings'][role].get('effort')),
                              resolved_model='unknown', resolved_effort='unknown', alive=False)
            process = next((o for o in operations if o['kind'] == 'PROCESS'
                            and o['data'].get('context', {}).get('agent_role') == role
                            and operation_rounds.get(o['id']) == (0 if kind == 'planner' else number)), None)
            if process:
                p = process['data'].get('process')
                n['agent'].update(pid=p.get('pid') if isinstance(p, dict) else None,
                    alive=process['status'] == 'RUNNING' and liveness(p) == 'alive' and worker_live and state == phase)
                request = next((o['data'] for o in operations if o['kind'] == 'AGENT_REQUEST'
                                and o['data'].get('role') == role and operation_rounds.get(o['id']) == (0 if kind == 'planner' else number)), {})
                n['agent']['session_id'] = token(request.get('actual_session') or request.get('requested_session'))
            if current:
                n['agent'].update({k: token(value.get(k)) for k in ('session_id', 'requested_model', 'requested_effort', 'resolved_model', 'resolved_effort')})
                if kind == 'reviewer':
                    verdict = report.get('verdict')
                    n['verdict'] = verdict if verdict in ('ACCEPT', 'ACCEPT_WITH_LIMITATIONS', 'NEEDS_CORRECTION', 'BLOCKED') else None
                    n['findings'] = [{k: f.get(k) for k in ('id', 'status', 'severity', 'title')} for f in report.get('findings', [])]
                    n['open_findings'] = sum(f['status'] != 'CLOSED' for f in n['findings'])
                    required = set(config['policy']['required_contracts'])
                    open_required = any(f.get('status') != 'CLOSED' and
                        (f.get('severity') in ('P0', 'P1') or f.get('severity') == 'P2' and
                         bool(set(f.get('contract_ids', [])) & required)) for f in report.get('findings', []))
                    n['status'] = 'failed' if verdict == 'NEEDS_CORRECTION' else 'passed' if verdict == 'ACCEPT' and not open_required else 'blocked'
                else:
                    n['status'] = 'passed' if report.get('status') == 'IMPLEMENTED' else 'blocked'
            elif state == phase or snapshot.get('recorded_state') == phase:
                n['status'] = 'running' if n['agent']['alive'] else 'blocked'
        elif kind == 'human_gate':
            final = plan['document']['template'] == 'C' and key == plan['order'][-2]
            if final:
                n['status'] = 'passed' if human_result_bound(data) and candidate else 'blocked' if state == 'AWAITING_HUMAN' else 'pending'
                n['confirmation'] = '当前候选需填写结果解释并确认' if state == 'AWAITING_HUMAN' else '结果确认绑定当前候选和轮次'
            else:
                n['status'] = 'passed' if sha(data.get('authorization_sha256')) else 'pending'
                n['confirmation'] = '本次授权回执已绑定' if n['status'] == 'passed' else '授权证据未确认'
        elif kind == 'delivery':
            receipt = data.get('github_receipt') or {}
            allowed = config['policy']['delivery']['commit']
            n['delivery'] = dict(authorized=allowed, commit=sha(receipt.get('commit')),
                                 pushed=receipt.get('pushed') is True, pr=None, phase=state)
            pr = receipt.get('pr')
            target = config.get('github_delivery', {})
            if isinstance(pr, dict) and pr.get('head') == receipt.get('commit') and isinstance(pr.get('url'), str) and pr['url'].startswith('https://github.com/' + target.get('repository', '') + '/pull/'):
                n['delivery']['pr'] = {k: pr.get(k) for k in ('number', 'url', 'head')}
            if allowed:
                n['status'] = 'passed' if state == 'COMPLETED' and n['delivery']['commit'] and n['delivery']['pushed'] and n['delivery']['pr'] else 'blocked' if stopped else 'running' if state in ('COMMITTING', 'PUSHING') and worker_live else 'pending'
            else:
                n['status'] = 'blocked'
                n['delivery']['phase'] = '未授权 Git 交付'
        output.append(n)
    # Edge evidence is separate so the original edge objects remain intact.
    edge_states = []
    by_id = {n['id']: n for n in output}
    for edge in plan['document']['edges']:
        a, b = by_id[edge['source']], by_id[edge['target']]
        status = 'pending'
        if edge['on'] == 'repair':
            feedback = data.get('feedback', {}).get('review', {})
            if b['status'] == 'running' and feedback.get('verdict') == 'NEEDS_CORRECTION' and feedback.get('run_id') == run and feedback.get('round') == number - 1:
                status = 'running'
        elif a['status'] == 'passed':
            status = b['status'] if b['status'] in ('running', 'failed', 'blocked') else 'passed' if b['status'] == 'passed' else 'pending'
        edge_states.append(status)
    return dict(nodes=output, edges=plan['document']['edges'], sha256=plan['sha256'],
                round=number, run_id=run, edge_states=edge_states)
