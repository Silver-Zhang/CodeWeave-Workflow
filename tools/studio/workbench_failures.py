"""Fail closed on unexpected worker errors without replaying native effects."""
from pathlib import Path
import sqlite3
import traceback
from orchestration.process import group_alive, stop
from orchestration.store import process_identity

TERMINAL={'COMPLETED','FAILED','CANCELLED','SKIPPED','RECOVERY_REQUIRED'}


def abort_unexpected(runtime,run,error):
    """Only this run's verified process groups may be stopped.

    Persist public error class/frames, never an exception's arbitrary payload,
    Provider output, credentials, or hidden reasoning. Completed receipts stay.
    """
    if runtime.flow.get('run',run).get('unexpected_error'):
        return  # First failure already persisted and owned groups were checked.
    name=type(error).__name__
    reason='运行器异常（'+name+'）；本次已停止调度，需核验原生回执，未自动重发。'
    frames=[dict(file=Path(f.filename).name,line=f.lineno,function=f.name)
            for f in traceback.extract_tb(error.__traceback__)][-12:]
    import time
    diagnostic={}
    code=getattr(error,'sqlite_errorcode',None)
    if isinstance(error,sqlite3.Error) and type(code) is int and 0<=code<2**31:
        diagnostic['sqlite_errorcode']=code
        diagnostic['sqlite_errorname']={5:'SQLITE_BUSY',6:'SQLITE_LOCKED',8:'SQLITE_READONLY',
            10:'SQLITE_IOERR',11:'SQLITE_CORRUPT',13:'SQLITE_FULL',14:'SQLITE_CANTOPEN',
            19:'SQLITE_CONSTRAINT'}.get(code&255,'SQLITE_ERROR_OTHER')
    runtime.flow.change('run',run,dict(state='RECOVERY_REQUIRED',reason=reason,unexpected_error=name,
                        error_frames=frames,finished_at=time.time(),**diagnostic),event={'kind':'worker-error','error_class':name})
    me=process_identity(__import__('os').getpid())
    for row in runtime.flow.list('activation'):
        if row['run']!=run:continue
        process=row.get('process');owned=process and me and all(process.get(k)==me[k] for k in ('host','boot_id'))
        if owned:
            try:
                if group_alive(process):stop(process)
            except (OSError,KeyError,ValueError):pass  # State remains unconfirmed, never success.
        if row['state'] not in TERMINAL:
            runtime.flow.change('activation',row['id'],dict(state='RECOVERY_REQUIRED' if row['state'] in ('STARTING','RUNNING') else 'SKIPPED',
                reason=reason,error_class=name,finished_at=time.time()),event={'kind':'node-failed','error_class':name})
