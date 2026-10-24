"""Deployment pins and mechanical receipts for privileged external steps."""
from pathlib import Path
from orchestration.common import Blocked,digest,tree_hash,manifest
from .session_sources import clean_path,opened
import os
import hashlib
import re


def validate_profile(profile,check_bytes=True):
    fields={'kind','name','argv','executable_sha256','dependencies','dependency_trees','read_paths','write_paths','timeout','isolation'}
    if not isinstance(profile,dict) or set(profile)-fields or profile.get('kind') not in ('verify','delivery'):
        raise Blocked('外部执行配置需要明确类型')
    argv=profile.get('argv')
    if not isinstance(argv,list) or not argv or not all(isinstance(a,str) and '\0' not in a for a in argv):raise Blocked('固定外部参数数组无效')
    executable=clean_path(argv[0]);deps=profile.get('dependencies',{});trees=profile.get('dependency_trees',{})
    if not isinstance(deps,dict) or not isinstance(trees,dict) or deps.get(executable)!=profile.get('executable_sha256') or not deps.get(executable):
        raise Blocked('外部执行器需要固定程序及依赖哈希')
    # This is a deliberately small argv protocol, not a filename heuristic.
    # env, renamed interpreters and wrappers can all interpret extensionless
    # operands as files relative to the writable project cwd. Therefore EVERY
    # operand must be an absolute pinned input, regardless of executable name.
    # Only known interpreter startup switches before the pinned entrypoint are
    # accepted. Adapter configuration/literal options belong in its pinned
    # launcher, not in untyped argv operands.
    interpreter = Path(executable).name.lower()
    if re.fullmatch(r'python(?:\d+(?:\.\d+)*)?', interpreter):
        options = {'-I','-B','-u','-s','-S','-E','-O','-OO','-q','--'}
    elif interpreter in ('node','nodejs'):
        options = {'--no-warnings','--'}
    elif interpreter in ('bash','sh','dash'):
        options = {'--'}
    else:
        options = set()
    entrypoint = False
    options_closed = False
    for arg in argv[1:]:
        if not entrypoint and not options_closed and arg in options:
            if arg == '--':options_closed = True
            continue
        if not Path(arg).is_absolute():
            raise Blocked('外部参数仅支持固定哈希的绝对输入路径；字面配置须放入固定启动器')
        clean_path(arg)
        if Path(arg).is_dir():
            if arg not in trees:raise Blocked('外部目录参数没有固定树哈希')
        elif arg not in deps:raise Blocked('外部脚本/配置没有固定哈希')
        if options and not entrypoint and arg not in deps:
            raise Blocked('解释器入口必须是固定哈希的绝对脚本文件')
        entrypoint = True
    if options and not entrypoint:
        raise Blocked('解释器入口必须是固定哈希的绝对脚本文件')
    for field in ('read_paths','write_paths'):
        if not isinstance(profile.get(field,[]),list):raise Blocked('外部挂载需要路径数组')
        for path in profile.get(field,[]):
            clean_path(path)
            if path in ('/','/home','/tmp','/var','/var/tmp'):raise Blocked('外部挂载范围过大')
            if field=='read_paths' and Path(path).is_dir() and path not in trees:raise Blocked('外部导入目录需要完整树哈希')
    if type(profile.get('timeout',600)) is not int or not 1<=profile.get('timeout',600)<=3600:raise Blocked('外部超时无效')
    if profile.get('isolation','bwrap') not in ('bwrap','landlock'):raise Blocked('外部步骤必须强制隔离')
    if check_bytes:
        for path,sha in deps.items():
            with opened(clean_path(path)) as fd:
                content=hashlib.sha256()
                while chunk:=os.read(fd,65536):content.update(chunk)
                if content.hexdigest()!=sha:raise Blocked('固定外部程序或配置已变化')
        for path,sha in trees.items():
            clean_path(path)
            if tree_hash(path)!=sha or any(e['mode']=='120000' for e in manifest(path)):raise Blocked('固定外部依赖目录已变化或包含未固定目标的符号链接')


def validate_receipt(receipt,payload,kind):
    fields=('run','activation','candidate_sha256','graph_sha256','authorization_sha256','acceptance_sha256')
    if not isinstance(receipt,dict) or any(k not in payload or k not in receipt or receipt[k]!=payload[k] for k in fields):
        raise Blocked('外部回执不属于当前源码/运行/节点/合同')
    if kind=='verify':
        keys=('tests','failures','errors','skipped')
        if any(type(receipt.get(k)) is not int or receipt[k]<0 for k in keys) or receipt['tests']<1 or any(receipt[k] for k in keys[1:]):
            raise Blocked('验证未通过，不能以退出 0 或 Agent ACCEPT 代替测试计数')
        if receipt.get('verified') is not True:raise Blocked('缺少固定验证执行证据')
    elif receipt.get('verdict')!='ACCEPT' or receipt.get('remote_verified') is not True or receipt.get('delivery_state')!='COMPLETED':
        raise Blocked('交付尚未完整确认：'+str(receipt.get('delivery_state','unknown'))+'；已成功远端不回滚')
