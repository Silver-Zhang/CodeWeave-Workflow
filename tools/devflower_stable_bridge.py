"""Pinned adapter to an existing, independently authorized Stable run.

Deploy a copy outside Development. This adapter cannot mint approvals, import
Development's Controller, turn Agent output into verification, or create a run.
All authority comes from the externally bound Stable run and its original gate.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import re
import sys
import time


def canonical(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read_json(path, expected=None):
    path=Path(path)
    if not path.is_absolute() or path.is_symlink() or not path.is_file() or path.stat().st_nlink!=1 or path.stat().st_size>2_000_000:
        raise ValueError('Invalid private bridge input')
    raw=path.read_bytes()
    if expected is not None and sha(raw)!=expected:raise ValueError('Bridge input changed')
    return json.loads(raw)


def stable_modules(binding):
    """Validate all frozen bytes before the first Stable Python import."""
    record=read_json(binding['record'],binding['sha256']);root=Path(record['root'])
    if root.is_symlink() or not root.is_absolute():raise ValueError('Invalid Stable root')
    entries=[]
    for folder,dirs,files in os.walk(root,followlinks=False):
        dirs[:]=sorted(d for d in dirs if d!='.git')
        if any((Path(folder)/n).is_symlink() for n in dirs+files):raise ValueError('Stable symlink refused')
        for name in files:
            if name=='.git':continue
            p=Path(folder)/name
            entries.append(dict(path=p.relative_to(root).as_posix(),mode='100755' if p.stat().st_mode&0o111 else '100644',size=p.stat().st_size,sha256=sha(p.read_bytes())))
    entries.sort(key=lambda x:x['path'])
    if entries!=record['files'] or sha(canonical(entries))!=record['candidate_sha256']:raise ValueError('Stable bytes changed')
    # -I plus this sole explicit product path prevents importing the target's code.
    sys.path.insert(0,str(root/'tools'))
    from orchestration.trust import TrustedRelease
    return TrustedRelease.bound(binding)


class Bridge:
    def __init__(self,config):
        self.config=config
        if set(config)!={'version','stable','grants'} or config['version']!=1:
            raise ValueError('Unsupported bridge configuration')
        self.trust=stable_modules(config['stable'])
        self.grants=Path(config['grants'])
        if not self.grants.is_absolute() or self.grants.is_symlink() or not self.grants.is_dir():raise ValueError('Invalid external grants directory')
        self.store=None

    def bind(self,payload):
        run=payload.get('run','')
        if not isinstance(run,str) or not re.fullmatch('[0-9a-f]{32}',run):raise ValueError('Invalid run identity')
        self.grant_path=self.grants/(run+'.json');grant_sha=sha(self.grant_path.read_bytes());grant=read_json(self.grant_path,grant_sha)
        if set(grant)!={'control','stable_run','binding','github'}:raise ValueError('Invalid external per-run grant')
        from orchestration.controller import overlaps
        if overlaps(payload['source'],self.grants):raise ValueError('Source cannot contain external grants')
        self.grant_sha256=grant_sha;self.grant=grant
        from orchestration.store import Store
        if self.store is not None:self.store.db.close()
        self.store=Store(grant['control'])

    def execute(self,kind,payload):
        from orchestration.common import Blocked,tree_hash,digest
        from orchestration.controller import binding_check,overlaps
        from orchestration.store import lease
        from orchestration.gate import gate
        self.bind(payload)
        c=dict(self.grant,stable=self.config['stable']);run=c['stable_run'];row=self.store.get(run);d=row['data'];expected=c['binding']
        fields={'run','source','candidate_sha256','graph_sha256','authorization_sha256','acceptance_sha256'}
        if set(expected)!=fields or any(payload.get(k)!=v for k,v in expected.items()):raise Blocked('External grant belongs to another run/source/contract')
        if not payload.get('activation') or kind not in ('verify','delivery'):raise Blocked('Invalid bridge operation')
        source=Path(payload['source'])
        self.trust.permits(source,c['control'])
        if d.get('stable')!=c['stable'] or overlaps(source,Path(__file__).resolve()):raise Blocked('Bridge requires independently bound Stable authority outside source')
        with lease(Path(c['control'])/(run+'.lock')):
            row=self.store.get(run);d=row['data']
            cfg=binding_check(self.store,d)
            if payload['acceptance_sha256']!=d['acceptance_sha256']:
                raise Blocked('Task acceptance differs from the original Stable run')
            candidate=d['candidate']['sha256']
            if candidate!=payload['candidate_sha256'] or tree_hash(source)!=candidate or tree_hash(d['candidate_path'])!=candidate:
                raise Blocked('Frozen/source candidate differs from the external grant')
            # A prior PASS flag or result.json is insufficient: validate the original
            # Controller-owned reports, exact expected suite set and all raw receipts.
            reports=d.get('verification',[]);specs={s['id']:s for s in cfg['policy']['verification']}
            if len(reports)!=len(specs) or {v['id'] for v in reports}!=set(specs):raise Blocked('Missing verification suites')
            totals=dict(tests=0,failures=0,errors=0,skipped=0)
            for v in reports:
                counts=v['counts'];proc=v['process'];spec=specs[v['id']]
                if set(counts)!=set(totals) or any(type(x) is not int or x<0 for x in counts.values()):raise Blocked('Invalid counters')
                if not v['passed'] or v['run_id']!=run or v['round']!=d['round'] or v['candidate_sha256']!=candidate or v['acceptance_sha256']!=d['acceptance_sha256']:
                    raise Blocked('Failed or stale verification')
                if counts['tests']<max(1,spec['min_cases']) or any(counts[k] for k in ('failures','errors','skipped')) or proc.get('exit')!=0 or any(proc.get(k,True) for k in ('timeout','overflow','cancelled')):
                    raise Blocked('Actual verification failed or skipped')
                result=Path(v['result_path'])
                if result.is_symlink() or not result.is_file() or digest(result.read_bytes())!=v['result_sha256']:raise Blocked('Verification receipt changed')
                for k in totals:totals[k]+=counts[k]
            receipt={k:payload[k] for k in fields|{'activation'}}
            receipt.update(stable_run=run,stable_candidate=self.trust.data['candidate_sha256'],grant_sha256=self.grant_sha256,executor='independently pinned Stable',**totals)
            if kind=='verify':
                receipt.update(summary='固定 Stable 的完整候选验证及原始回执已核验',verified=True)
                return receipt
            gate(run,d['round'],candidate,d['acceptance_sha256'],cfg['policy']['required_contracts'],reports,d['implementation'],d['review'],d['history'],cfg['policy']['verification'])
        # deliver_run acquires its own run/source leases and repeats every gate.
        from orchestration.controller import deliver_run
        from orchestration.github_delivery import GitHub
        if sha(self.grant_path.read_bytes())!=self.grant_sha256:raise Blocked('External grant changed before delivery')
        if row['state']!='COMPLETED':
            try:deliver_run(self.store,run,github=GitHub(**c['github']) if c['github'] else None)
            except Blocked:
                current=self.store.get(run)
                receipt.update(delivery_state=current['state'],remote_verified=False,verdict='BLOCKED',partial=current['state']=='PARTIAL_DELIVERY',receipts=current['data'].get('receipts',[]),summary='交付尚未完整确认；已成功远端不回滚')
                return receipt
        current=self.store.get(run);d=current['data']
        if current['state']!='COMPLETED':
            receipt.update(delivery_state=current['state'],remote_verified=False,verdict='BLOCKED',partial=False,receipts=d.get('receipts',[]),summary='本地交付状态已保留；远端尚未完整确认')
            return receipt
        if c['github']:
            client=GitHub(**c['github']);r=d['github_receipt'];target=cfg['github_delivery']
            if client.tip(target['branch'])!=r['commit']:raise Blocked('GitHub readback changed')
            item=client.api(f"repos/{client.repository}/pulls/{r['pr']['number']}")
            if item['head']['sha']!=r['commit'] or item['head']['ref']!=target['branch'] or item['base']['ref']!=target['base']:raise Blocked('PR readback mismatch')
            receipts=[r]
        else:
            from orchestration.delivery import remote_tip
            receipts=d['receipts'];targets=cfg['delivery_targets']
            if len(receipts)!=len(targets) or any(not r.get('pushed') or remote_tip(t['remote'],t['branch'])!=r['commit'] for t,r in zip(targets,receipts)):
                raise Blocked('Remote delivery incomplete or changed')
        receipt.update(summary='固定 Stable 已提交、推送并读回所有授权交付目标',verdict='ACCEPT',remote_verified=True,delivery_state='COMPLETED',receipts=receipts)
        return receipt


def main():
    p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--config-sha256',required=True);p.add_argument('--kind',choices=['verify','delivery'],required=True);a=p.parse_args()
    bridge=Bridge(read_json(a.config,a.config_sha256))
    try:
        raw=sys.stdin.buffer.read(200001)
        if len(raw)>200000:raise ValueError('Bridge request exceeds limit')
        payload=json.loads(raw);run=payload.get('run','')
        if not isinstance(run,str) or not re.fullmatch('[0-9a-f]{32}',run):raise ValueError('Invalid run identity')
        # A fixed external supervisor may issue the grant after observing the real
        # launch identity. This process only waits/reads; it never creates grants.
        deadline=time.monotonic()+8
        while not (bridge.grants/(run+'.json')).exists() and time.monotonic()<deadline:time.sleep(.1)
        result=bridge.execute(a.kind,payload);print(canonical(result).decode())
    finally:
        if bridge.store is not None:bridge.store.db.close()


if __name__=='__main__':main()
