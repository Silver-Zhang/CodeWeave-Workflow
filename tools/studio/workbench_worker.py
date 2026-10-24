"""Independent process lifecycle for a v3 Development run, not a Stable authority."""
import argparse
from pathlib import Path
import sys
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from orchestration.store import lease
from orchestration.store import process_identity
import os
from studio.workbench_runtime import WorkbenchRuntime
from studio.workbench_scheduler import Scheduler

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for key in ('operator','operator-sha256','candidate-sha256','policy','policy-sha256','run'):p.add_argument('--'+key,required=True)
    a=p.parse_args();rt=WorkbenchRuntime(a.operator,a.operator_sha256,a.candidate_sha256,a.policy,a.policy_sha256)
    with lease(rt.storage/(a.run+'.worker.lock')):
        rt.flow.change('run',a.run,{'worker':process_identity(os.getpid())})
        try:
            Scheduler(rt,a.run).run_graph()
        except BaseException as exc:
            from studio.workbench_failures import abort_unexpected
            try:abort_unexpected(rt,a.run,exc)
            except BaseException:sys.stderr.write('Worker failure: '+type(exc).__name__+'; authority update unavailable\n')
            sys.exit(1)
        if rt.flow.get('run',a.run).get('unexpected_error'):sys.exit(1)
