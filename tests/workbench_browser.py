"""Ordinary Chromium and real HTTP races; synthetic snapshots, no model acceptance."""
import argparse,json,os,subprocess,sys,threading,time,unittest
from pathlib import Path
sys.path[:0]=[str(Path(__file__).parent),str(Path(__file__).resolve().parents[1]/'tools')]
from test_workbench_runtime import fixture
from studio.workbench_server import create_server
from studio.workbench_examples import examples


def main():
    p=argparse.ArgumentParser();p.add_argument('--chromium',required=True);p.add_argument('--artifacts',required=True);p.add_argument('--node',default='node');p.add_argument('--playwright-module',default='playwright');a=p.parse_args()
    root=Path(__file__).resolve().parents[1];out=Path(a.artifacts).resolve()
    if out.is_relative_to(root) or root.is_relative_to(out):p.error('Artifacts must stay outside source')
    out.mkdir(parents=True,mode=0o700);owner=unittest.TestCase();base,rt=fixture(owner);workspace=base.project['id']
    for label in ('A','B'):
        graph=examples(rt.operator['profiles'])[0];graph['name']='运行 '+label
        graph['budget']={'calls':10 if label=='A' else 12,'seconds':600 if label=='A' else 900}
        graph['nodes'][1]['name']='分析 '+label
        rt.flow.put('run',label,dict(id=label,workspace=workspace,state='COMPLETED',graph=graph,task='任务 '+label,created_at=time.time(),actual_calls=0))
        rt.flow.put('activation',label,dict(id=label,run=label,node='analyze',name='分析 '+label,kind='agent',state='COMPLETED',iteration=1,output={'answer':'结果 '+label}))
    server,token=create_server(rt);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    access=out/'access.json';access.write_text(json.dumps(dict(url='http://127.0.0.1:'+str(server.server_port),token=token,workspace=workspace,path=str(base.source))))
    access.chmod(0o600)
    try:return subprocess.run([a.node,str(Path(__file__).with_suffix('.cjs')),str(out)],timeout=180,env=dict(os.environ,CHROMIUM=a.chromium,PLAYWRIGHT_MODULE=a.playwright_module)).returncode
    finally:server.shutdown();server.server_close();thread.join();owner.doCleanups()


if __name__=='__main__':sys.exit(main())
