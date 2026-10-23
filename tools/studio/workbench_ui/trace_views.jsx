import React from 'react';
import Markdown from 'react-markdown';

const names = {answer:'最终回答', summary:'摘要', result:'结构化结果', artifacts:'产物引用', evidence:'验证与审核证据',
  issues:'未解决问题', next:'下一步', sources:'来源', accepted:'满足条件', reference:'文件引用', accessible:'可访问',
  source:'来源节点', content:'实际内容', sha256:'内容身份', node:'节点', iteration:'轮次', iteration_path:'完整轮次路径'};

export function DataValue({value, depth=0}) {
  if (value === null || value === undefined) return <span className="hint">无</span>;
  if (typeof value === 'string') return <Markdown skipHtml>{value}</Markdown>;
  if (typeof value === 'boolean') return <span>{value?'是':'否'}</span>;
  if (typeof value !== 'object') return <span>{String(value)}</span>;
  if (value.truncated) return <div className="hint">交接预算已截断：原 {value.original_chars} 字符，预算 {value.budget}<pre>{value.text}</pre></div>;
  const body = Array.isArray(value) ? <ol className="data-array">{value.map((v,i)=><li key={i}><DataValue value={v} depth={depth+1}/></li>)}</ol> :
    <dl className="data-object">{Object.entries(value).filter(([key])=>!['receipt','authorization','credentials'].includes(key)).map(([key,v])=><React.Fragment key={key}><dt>{names[key]||key}</dt><dd><DataValue value={v} depth={depth+1}/></dd></React.Fragment>)}</dl>;
  return depth>2 ? <details><summary>展开{Array.isArray(value)?value.length+'项数据':'字段内容'}</summary>{body}</details> : body;
}

export function VisibleRequest({activation}) {
  if (!activation) return null;
  const receipt=activation.receipt;
  return <details className="actual-request" data-testid="actual-provider-request"><summary>本次实际 Provider 请求 · {activation.input_sent_sha256?'已完整发送':'尚无完整发送回执'}</summary>
    <p className="hint">以下来自该运行的持久记录，不是草稿模板。可见内容已脱敏；初始化{activation.initialization_included?'本次已包含':'本次未重复发送'}。</p>
    {(activation.request_sections||[]).map((part,i)=>{let data;try{if(part.title.startsWith('上游输入'))data=JSON.parse(part.text)}catch{}return <section key={i}><h4>{part.title}</h4>{data?<DataValue value={data}/>:<Markdown skipHtml>{part.text}</Markdown>}</section>})}
    <details><summary>完整可见请求与身份</summary><pre>{activation.actual_request||'尚未产生真实请求'}</pre><dl className="handoff-facts"><dt>运行</dt><dd>{activation.run}</dd><dt>Activation</dt><dd>{activation.id}</dd><dt>完整轮次</dt><dd>{(activation.iteration_path?.length?activation.iteration_path:[activation.iteration||1]).join(' / ')}</dd><dt>实际发送SHA</dt><dd>{activation.input_sent_sha256||'尚无回执'}</dd><dt>请求模型</dt><dd>{receipt?.requested_model||activation.model} / {receipt?.requested_effort||activation.effort}</dd><dt>回报模型</dt><dd>{receipt?.resolved_model||'unknown'} / {receipt?.resolved_effort||'unknown'}</dd><dt>原生会话</dt><dd>{receipt?.session_id||'尚未核验'}</dd></dl></details>
  </details>;
}

export function HandoffTrace({edge, prefix, events, snapshot}) {
  const matches = events.filter(e=>e.edge===edge.id && e.source===prefix+edge.source && e.node===prefix+edge.target &&
    e.run===snapshot?.run.id && ['handoff-ready','handoff-sent','handoff-received'].includes(e.kind));
  const groups = new Map();
  for(const event of matches) groups.set(JSON.stringify([event.edge,event.activation,event.node,event.iteration_path]),event);
  if(!groups.size)return <p className="hint">尚无本运行、本连线的实际交接记录。配置预览不代表已经发送。</p>;
  return <div data-testid="handoff-trace">{[...groups.values()].map(event=>{
    const source=snapshot.nodes.find(a=>a.id===event.activation);
    const target=snapshot.nodes.find(a=>a.node===event.node && JSON.stringify(a.iteration_path||[])===JSON.stringify(event.iteration_path||[]));
    const state=event.kind==='handoff-sent'?'已完整发送到原生工具输入':event.kind==='handoff-received'?'确定性节点已接收':'内容已固定，等待发送';
    return <details key={event.seq} open><summary>第 {(event.iteration_path?.length?event.iteration_path:[event.iteration||1]).join(' / ')} 轮 · {state}</summary>
      <dl className="handoff-facts"><dt>来源</dt><dd>{source?.name||event.source}</dd><dt>目标</dt><dd>{target?.name||event.node}</dd><dt>传递字段</dt><dd>{edge.transfer==='field'?edge.field:names[edge.transfer||'result']||edge.transfer}</dd><dt>接收状态</dt><dd>{state}</dd></dl>
      <DataValue value={event.content}/><details><summary>运行与产物身份</summary><dl className="handoff-facts"><dt>运行</dt><dd>{event.run}</dd><dt>来源Activation</dt><dd>{event.activation}</dd><dt>目标Activation</dt><dd>{target?.id||'尚无对应激活'}</dd><dt>调用前源码</dt><dd>{source?.source_at_request?.sha256||'此确定性来源没有模型源码回执'}</dd><dt>工作台候选</dt><dd>{snapshot.run.candidate_sha256||'历史记录未提供'}</dd></dl></details>
    </details>;
  })}</div>;
}
