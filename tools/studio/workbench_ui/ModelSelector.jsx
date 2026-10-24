import React,{useEffect,useRef,useState} from 'react';

// The server selects approved endpoints and credentials. No browser-supplied URL.
export function ModelSelector({api,profile,model,effort,onChange,onCatalog,disabled=false}){
 const [catalog,setCatalog]=useState(profile),[pending,setPending]=useState(false),[error,setError]=useState('');
 const version=useRef(0);
 async function load(refresh=false){const v=++version.current;setPending(true);setError('');try{
  let result=await api('/api/models',{profile:profile.id,refresh});
  if(v===version.current&&!refresh&&!result.attempted_at)result=await api('/api/models',{profile:profile.id,refresh:true});
  if(v!==version.current)return;setCatalog(result);onCatalog?.(result);
 }catch(e){if(v===version.current)setError(e.message)}finally{if(v===version.current)setPending(false)}}
 useEffect(()=>{setCatalog(profile);load(false);return()=>{version.current++}},[profile?.id]);
 const current=catalog?.id===profile?.id?catalog:profile;
 const models=current?.models||[],selected=models.find(m=>m.id===model);
 return <section className="model-picker" aria-label="模型发现">
  <label className="field"><span>模型</span><select aria-label="模型" disabled={disabled||pending} value={model||''} onChange={e=>{const m=models.find(x=>x.id===e.target.value);onChange({model:m.id,effort:m.efforts.includes(effort)?effort:m.efforts[0]||''})}}>
   {!selected&&<option value={model||''}>{model||'请选择模型'}（目录尚未确认）</option>}
   {models.map(m=><option key={m.id} value={m.id} disabled={!m.execution_allowed}>{m.name||m.id}{!m.execution_allowed?'（发现但未登记执行）':''}</option>)}
  </select></label>
  <label className="field"><span>推理强度</span><select aria-label="推理强度" disabled={disabled||pending} value={effort||''} onChange={e=>onChange({model,effort:e.target.value})}>{!selected?.efforts.includes(effort)&&<option value={effort||''}>{effort||'unknown'}</option>}{(selected?.efforts||[]).map(x=><option key={x}>{x}</option>)}</select></label>
  <div className="catalog-meta"><button type="button" disabled={pending||disabled} onClick={()=>load(true)}>{pending?'正在读取…':'刷新模型'}</button><span role="status">{current?.refresh_pending?'另一个刷新正在进行，请稍后再读':current?.stale?'旧数据／未发现实时目录':'目录已获取'} · {current?.source||'尚未查询'}</span><small>更新：{current?.updated_at?new Date(current.updated_at*1000).toLocaleString('zh-CN'):'尚无成功查询'}</small>
  {(error||current?.error)&&<p role="alert">{error||current.error}</p>}<small>目录不是调用成功证明。实际物理后端与生效 effort：unknown；以原生回合回执分别核对。</small></div>
 </section>
}
