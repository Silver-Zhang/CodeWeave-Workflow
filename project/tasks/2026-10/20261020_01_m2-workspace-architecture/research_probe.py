"""Read-only production-code research: owned inputs, real public CLI, no M2 code."""
from pathlib import Path
import argparse, hashlib, json, os, shutil, sqlite3, subprocess, sys

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source-root', type=Path, required=True)
parser.add_argument('--work', type=Path, required=True, help='Fresh owned directory; refuses overwrite')
parser.add_argument('--analyzer', type=Path, required=True)
parser.add_argument('--resource-dir', type=Path, required=True)
args = parser.parse_args()
HERE = args.work.absolute()
HERE.mkdir(parents=True, exist_ok=False)
SOURCE = args.source_root.resolve(strict=True)
BUILD = args.analyzer.resolve(strict=True)
RESOURCE = args.resource_dir.resolve(strict=True)
PYTHON = Path(sys.executable)
ROOT = HERE / 'research-input'
ROOT.mkdir()
DB = HERE / 'research.sqlite3'
(HERE/'predefined-expectations.json').write_text(json.dumps([
    'macro/shared headers belong to both consuming TU read-sets',
    'optional-header addition changes target without TU-byte edit',
    'line-only movement keeps external USR/relation multiset, changes stored instance IDs',
    'same source in different physical root changes internal-linkage identity',
    'old explicit index still returns its original source bytes and status'
], indent=2)+'\n')
LOG = []
ENV = {**os.environ, 'PYTHONPATH': str(SOURCE / 'backend')}

def cli(*args):
    argv = [str(PYTHON), '-m', 'codeweave', *map(str, args)]
    result = subprocess.run(argv, env=ENV, capture_output=True, text=True)
    LOG.append(dict(argv=argv, exit_code=result.returncode, stdout=result.stdout, stderr=result.stderr))
    (HERE / 'research-commands.json').write_text(json.dumps(LOG, indent=2))
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)

def commands(root):
    entries = [dict(directory=str(root), file=name, arguments=['c++', '-std=c++17', '-I', str(root), '-c', name]) for name in ['a.cpp', 'b.cpp']]
    (root / 'compile_commands.json').write_text(json.dumps(entries))

def index(root=ROOT):
    return cli('index', '--project-root', root, '--compilation-database', root, '--database', DB, '--analyzer', BUILD, '--resource-dir', RESOURCE)['index_id']

def q(index_id, command, *args):
    return cli('query', command, *args, '--database', DB, '--index-id', index_id)

def symbol(index_id, name):
    matches = [x for x in q(index_id, 'search', name)['items'] if x['name'] == name]
    assert len(matches) == 1, matches
    return matches[0]

(ROOT/'config.hpp').write_text('#define SCALE 3\n')
(ROOT/'shared.hpp').write_text('#pragma once\n#include "config.hpp"\nint one(); int two();\ninline int shared() { return SCALE; }\n')
(ROOT/'a.cpp').write_text('#include "shared.hpp"\n#if __has_include("optional.hpp")\n#include "optional.hpp"\n#else\n#define TARGET one\n#endif\nstatic int hidden() { return 7; }\nint a() { return TARGET() + shared() + hidden(); }\nint one() { return 1; }\n')
(ROOT/'b.cpp').write_text('#include "shared.hpp"\nint b() { return shared(); }\nint two() { return 2; }\n')
commands(ROOT)
original = {p.name:p.read_bytes() for p in ROOT.iterdir()}
first=index()
with sqlite3.connect(DB) as connection:
    deps=connection.execute('SELECT source_file,path FROM unit_files WHERE index_id=? ORDER BY 1,2',(first,)).fetchall()
assert all((str(ROOT/tu),str(ROOT/header)) in deps for tu in ('a.cpp','b.cpp') for header in ('shared.hpp','config.hpp'))
assert not any(p.endswith('optional.hpp') for _,p in deps)
a1=symbol(first,'a'); calls1=q(first,'callees',a1['usr'])['items']
assert 'one' in [c['other_name'] for c in calls1] and 'two' not in [c['other_name'] for c in calls1]
(ROOT/'optional.hpp').write_text('#define TARGET two\n')
second=index()
assert (ROOT/'a.cpp').read_bytes()==original['a.cpp']
a2=symbol(second,'a'); calls2=q(second,'callees',a2['usr'])['items']
assert a1['usr']==a2['usr']
assert 'two' in [c['other_name'] for c in calls2] and 'one' not in [c['other_name'] for c in calls2]
(ROOT/'a.cpp').write_bytes(b'\n'+original['a.cpp'])
third=index()
a3=symbol(third,'a'); calls3=q(third,'callees',a3['usr'])['items']
assert a3['usr']==a2['usr']
assert sorted(c['target_usr'] for c in calls2)==sorted(c['target_usr'] for c in calls3)
assert {c['instance_id'] for c in calls2}.isdisjoint(c['instance_id'] for c in calls3)
copy=HERE/'research-copy'
shutil.copytree(ROOT,copy); commands(copy)
fourth=index(copy)
assert symbol(first,'hidden')['usr'] != symbol(fourth,'hidden')['usr']
assert q(first,'source',ROOT/'a.cpp','--start-line',1,'--end-line',len(original['a.cpp'].splitlines()))['content'].encode()==original['a.cpp']
assert q(first,'status')['index_id']==first
summary={'checks_passed':5,'index_ids':[first,second,third,fourth], 'analyzer_sha256':hashlib.sha256(BUILD.read_bytes()).hexdigest(),'dependency_rows':deps,'external_usr':a1['usr'],'old_call_targets':[c['other_name'] for c in calls1],'new_call_targets':[c['other_name'] for c in calls2],'position_only_instance_ids_disjoint':True,'internal_identity_root_dependent':True,'scope':'current M0/M1 facts, not implemented M2'}
(HERE/'research-results.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
