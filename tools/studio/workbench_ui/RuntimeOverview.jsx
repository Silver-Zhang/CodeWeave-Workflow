import React from 'react';
import {Activity,ArrowRight,Check,Clock3,AlertCircle} from 'lucide-react';
import {statusInfo,roundText,duration} from './runtime_projection.mjs';

export function StatusBadge({state}){
 const [label,tone,symbol]=statusInfo(state||'DRAFT');
 return <span className={'badge '+(state||'draft').toLowerCase()+' tone-'+tone}><span aria-hidden="true">{symbol}</span>{label}</span>;
}
export function RuntimeOverview({projection:p,snapshot,viewMode,onSelect,onRun,onReconnect}){
 if(viewMode!=='run')return <div className="design-banner"><span><i/>设计画布</span><p>编辑下一次运行的流程 · 当前执行快照不受影响</p><button onClick={onRun}>填写任务并开始 <ArrowRight size={13}/></button></div>;
 return <section className={'runtime-overview tone-'+statusInfo(p.state)[1]} aria-label="运行总览" aria-live="polite" data-testid="runtime-overview">
  <div className="overview-head"><div className="overview-title"><Activity size={18}/><strong>本次运行</strong><StatusBadge state={p.state}/><span className="frozen-label">冻结快照 · 只读</span></div><span className="elapsed"><Clock3 size={13}/>{p.trusted?duration(snapshot.run.started_at||snapshot.run.created_at,snapshot.run.finished_at):'耗时待确认'}</span></div>
  <div className="overview-content"><div className="overview-current"><small>当前执行</small><strong>{!p.trusted?'正在重新核验状态':p.active.length?p.active.map(x=>x.node.name).join('、'):p.state==='COMPLETED'?'流程已结束':p.state==='PAUSED'?'等待继续调度':p.state==='FAILED'?'执行已停止，请查看原因':p.waiting.length?'等待输入或确认':p.state==='CANCELLED'?'本次任务已取消':'正在等待调度'}</strong><span>{p.active.map(x=>`第 ${roundText(x.activation)} 轮 · ${duration(x.activation.started_at)}`).join('；')}</span></div><div className="overview-progress"><small>完成节点</small><strong>{p.trusted?`${p.done} / ${p.total}`:'— / —'}</strong><span>{p.trusted?<><Check size={12}/>基于真实运行记录</>:'旧状态已隐藏'}</span></div></div>
  {(p.reason||p.waiting.length>0)&&<div className="overview-attention">{p.reason&&<p><AlertCircle size={14}/>{p.reason}{!p.trusted&&<button onClick={onReconnect}>重新读取</button>}</p>}{p.waiting.map(({node,activation:a})=><button key={node.path} onClick={()=>onSelect(node.path)}>{node.name} · {a.state==='WAITING_CONFIRMATION'?'等待人工确认':`已收到 ${a.received||0}/${a.expected||0} 个输入；等待 ${(a.waiting||[]).map(id=>p.latest.find(x=>x.node.path===id)?.node.name||id).join('、')}`}</button>)}</div>}
 </section>;
}
