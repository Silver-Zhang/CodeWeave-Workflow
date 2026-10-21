"""Print four operator-readable DevFlower behavioral assertions; grants no authority."""
import json
from pathlib import Path
import sys

CODE = """import json,sys
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'tools'))
from studio.usable_graph import template,compile_plan
from studio.graph import Invalid
kind=json.load(sys.stdin)
try:
 plan=compile_plan(template(kind));by_id={n['id']:n['type'] for n in plan['document']['nodes']}
 print(json.dumps([by_id[key] for key in plan['order']]))
except Invalid:print(json.dumps({'rejected':True}))
"""

def profiles():
    expected = {
        'A': ['human_gate','developer','verifier','reviewer','delivery'],
        'B': ['human_gate','planner','developer','verifier','reviewer','delivery'],
        'C': ['human_gate','human_gate','human_gate','planner','developer','verifier','reviewer','human_gate','delivery'],
        'blank': {'rejected':True},
    }
    return {'default':[dict(id=kind, argv=[str(Path(sys.executable).resolve()),'-I','-c',CODE],
        stdin=json.dumps(kind), expected_json=value, read_paths=[]) for kind,value in expected.items()]}

if __name__ == '__main__':
    print(json.dumps(profiles(),indent=2))
