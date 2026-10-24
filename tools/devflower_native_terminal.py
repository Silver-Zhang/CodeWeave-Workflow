#!/usr/bin/env python3
"""Advanced read-only native resume in the original managed environment."""
import argparse
from contextlib import nullcontext
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import signal
sys.dont_write_bytecode=True
from orchestration.common import Blocked,clean_env,digest
from orchestration.store import lease
from orchestration.sandbox import runtime_paths
from orchestration.provider_transport import claude_transport
from studio.workbench_runtime import WorkbenchRuntime
from studio.workbench_sessions import WorkbenchSessions
from studio.workbench_scheduler import source_lease


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('operator','operator-sha256','candidate-sha256','policy','policy-sha256','workspace','handle'):p.add_argument('--'+key,required=True)
    a=p.parse_args();rt=WorkbenchRuntime(a.operator,a.operator_sha256,a.candidate_sha256,a.policy,a.policy_sha256)
    parent=os.environ.get('DEVFLOWER_TERMINAL_PARENT_PID')
    if parent:
        # Popen created a new session with this PTY on stdin. Do this in the
        # child main thread, not an unsafe preexec hook in the HTTP server.
        import fcntl,termios
        from orchestration.sandbox import LIBC
        fcntl.ioctl(sys.stdin.fileno(),termios.TIOCSCTTY,0)
        if LIBC.prctl(1,signal.SIGTERM,0,0,0) or os.getppid()!=int(parent):
            raise Blocked('原生终端监督器已退出，未启动CLI')
    if not sys.stdin.isatty() or not sys.stdout.isatty():raise Blocked('请在本机交互终端打开；浏览器不会启动第二个会话写入者')
    rt.check_operator();project,row=rt.session_center.resolve(a.workspace,a.handle)
    binding,reason=rt.session_center._binding(row,project)
    if not binding or WorkbenchSessions(rt).busy(binding,row['native']['session_id']):raise Blocked(reason or '会话占用状态未确认')
    cwd=row['native']['cwd'];home=Path(binding['home']);sid=row['native']['session_id']
    selected=rt.node_binding(a.workspace,dict(profile=binding['runtime_profile'],model=binding['model'],
        effort=binding['effort'],mode='Ask',permission='read'))
    if binding['provider']=='codex':
        argv=[binding['executable'],'resume',sid,'--model',binding['model'],'--no-alt-screen','--sandbox','read-only','--ask-for-approval','never','-c','features.multi_agent=false','-c','model_reasoning_effort='+json.dumps(binding['effort'])]
        transport=nullcontext(([],{}))
    else:
        argv=[binding['executable'],'--resume',sid,'--model',binding['model'],'--effort',binding['effort'],'--permission-mode','plan','--tools','Read,Glob,Grep','--setting-sources','user','--strict-mcp-config','--mcp-config','{"mcpServers":{}}']
        transport=claude_transport(binding,timeout=3600)
    with source_lease(rt.source_lock(cwd),False),lease(home.parent/(digest(str(home.resolve()).encode())+'.session.lock')),tempfile.TemporaryDirectory(prefix='df-terminal-') as scratch,transport as (extra,_):
        # All runtime/source mounts are readonly; only this native HOME and the
        # private temporary directory are writable. No PTY is attached in HTTP.
        rt.check_operator();rt.session_center.resolve(a.workspace,a.handle)
        from studio.model_admission import ModelAdmission
        ModelAdmission(rt).require(selected['binding'],cwd)
        wrapped=['/usr/bin/bwrap','--die-with-parent','--unshare-user','--unshare-pid','--unshare-ipc','--unshare-uts','--cap-drop','ALL','--proc','/proc','--dev','/dev','--tmpfs','/tmp']
        paths=sorted(set([cwd,*binding['read_paths'],*[x for x in runtime_paths() if not x.startswith(('/proc/','/dev/'))]]),key=lambda x:(len(Path(x).parts),x))
        for path in paths:
            if Path(path).exists():wrapped+=['--ro-bind',str(Path(path).resolve()),path]
        wrapped+=['--bind',str(home),str(home),'--bind',scratch,scratch]
        for source,relative in binding.get('readonly_files',[]):
            dest=home/relative
            if dest.is_symlink() or not dest.resolve().is_relative_to(home.resolve()):raise Blocked('凭据挂载路径不安全')
            dest.parent.mkdir(parents=True,exist_ok=True);wrapped+=['--ro-bind',source,str(dest)]
        wrapped+=['--remount-ro','/','--remount-ro','/tmp','--chdir',cwd,'--',*argv,*extra]
        env=clean_env(home);env['TMPDIR']=scratch;env['TERM']=os.environ.get('TERM','xterm-256color')
        code=subprocess.call(wrapped,cwd=cwd,env=env)
        if code:
            ModelAdmission(rt).invalidate(selected['binding'],cwd)
        return code


if __name__=='__main__':
    try:sys.exit(main())
    except (Blocked,OSError,ValueError) as exc:print(str(exc),file=sys.stderr);sys.exit(1)
