import json
import sys
import time
import unittest
from pathlib import Path

root = Path('/home/workspace/DevFlower/archives/devflower-pr15-pr17-final-20261024/reviews/r5-pr17-recovery2/candidate')
sys.path[:0] = [str(root / 'tools'), str(root / 'tests')]

from orchestration.common import digest
from studio.model_catalog import ModelCatalog
from studio.workbench_examples import examples
from studio.workbench_sessions import WorkbenchSessions
from test_workbench_runtime import fixture


class Owner(unittest.TestCase):
    def runTest(self):
        pass


owner = Owner()
base, runtime = fixture(owner)
profile_name = 'default-codex'
profile = runtime.operator['profiles'][profile_name]
identity = digest(json.dumps(profile, sort_keys=True).encode())
# Simulate a fresh, successful native model/list whose authoritative rows omit
# the configured default. It is neither stale nor an error response.
runtime.flow.put('model-discovery', profile_name, {
    'id': profile_name,
    'profile_sha256': identity,
    'models': [{'id': 'some-other-model', 'name': 'Other', 'efforts': ['high']}],
    'at': time.time(),
    'attempted_at': time.time(),
    'source': 'Codex app-server model/list',
    'error': None,
})
catalog = ModelCatalog(WorkbenchSessions(runtime)).get(profile_name, profile)
agent = next(node for node in examples(runtime.operator['profiles'])[0]['nodes'] if node['kind'] == 'agent')
print('catalog_discovery_complete=', catalog['discovery_complete'])
print('fresh_native_rows_omitted_default=True')
print('catalog_exposes_default=', any(row['id'] == profile['model'] for row in catalog['models']))
try:
    binding = runtime.node_binding(base.project['id'], agent)
    print('RESULT=ADMITTED', binding['binding']['model'], binding['binding']['effort'])
except Exception as exc:
    print('RESULT=REJECTED', type(exc).__name__, str(exc))
owner.doCleanups()
