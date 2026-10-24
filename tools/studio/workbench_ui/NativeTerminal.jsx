import React,{useEffect,useLayoutEffect,useRef,useState} from 'react';
import {Terminal as XTerm} from '@xterm/xterm';
import {FitAddon} from '@xterm/addon-fit';
import {Terminal,Play,Square,RefreshCw} from 'lucide-react';
import '@xterm/xterm/css/xterm.css';
import {statusInfo} from './runtime_projection.mjs';

// A native process is started only by the explicit confirm button. Mount/reload
// attaches a known PTY and reads output; it never retries a native input/start.
export function NativeTerminal({api,workspace,session,onChanged}) {
  const host=useRef(null),terminal=useRef(null),fit=useRef(null),current=useRef(null),version=useRef(0);
  const request=useRef(0);
  const sequence=useRef(0),pending=useRef(Promise.resolve()),uncertain=useRef(false),cursor=useRef(0);
  const [row,setRow]=useState(null),[preview,setPreview]=useState(null),[error,setError]=useState(''),[connected,setConnected]=useState(false);
  const [loading,setLoading]=useState(false);
  const [revision,setRevision]=useState(0);
  const scope=workspace.id+':'+session.handle;
  useLayoutEffect(()=>{
    const term=new XTerm({cursorBlink:true,convertEol:false,fontSize:12,fontFamily:'ui-monospace,monospace',
      scrollback:2000,allowProposedApi:false,disableStdin:true,theme:{background:'#111923',foreground:'#dae7fa'}});
    const addon=new FitAddon();term.loadAddon(addon);term.open(host.current);terminal.current=term;fit.current=addon;
    const observer=new ResizeObserver(()=>{if(terminal.current!==term)return;addon.fit();const active=current.current;if(active?.state==='RUNNING'&&!uncertain.current)api('/api/terminal/resize',{workspace:workspace.id,id:active.id,cols:Math.max(20,Math.min(300,term.cols)),rows:Math.max(5,Math.min(100,term.rows))}).catch(()=>{})});observer.observe(host.current);
    const input=term.onData(data=>{
      const active=current.current;if(!active||uncertain.current)return;
      // Serialize small writes; an ambiguous response disables input and is never retried.
      const epoch=version.current;
      const characters=Array.from(data);
      for(let start=0;start<characters.length;start+=512){const text=characters.slice(start,start+512).join('');pending.current=pending.current.then(async()=>{
        if(uncertain.current||epoch!==version.current||current.current?.id!==active.id)return;const next=sequence.current+1;
        try{await api('/api/terminal/input',{workspace:workspace.id,id:active.id,sequence:next,text});if(epoch===version.current)sequence.current=next;}
        catch(e){if(epoch!==version.current)return;uncertain.current=true;term.options.disableStdin=true;setConnected(false);setError('输入结果未确认，未重发。请重新连接核验后继续：'+e.message)}
      });}
    });
    return()=>{version.current++;request.current++;current.current=null;observer.disconnect();input.dispose();term.dispose();terminal.current=null;fit.current=null;};
  },[scope]);
  const attach=async()=>{
    const token=++version.current,reply=++request.current;setLoading(true);setError('');setPreview(null);setRow(null);setConnected(false);
    current.current=null;cursor.current=0;sequence.current=0;uncertain.current=false;pending.current=Promise.resolve();
    if(terminal.current){terminal.current.options.disableStdin=true;terminal.current.reset();}
    try{
      const list=await api('/api/terminals?workspace='+workspace.id);if(token!==version.current||reply!==request.current)return;
      const active=list.terminals.find(t=>t.handle===session.handle&&['STARTING','RUNNING','RECOVERY_REQUIRED'].includes(t.state));
      current.current=active||null;cursor.current=0;terminal.current?.reset();setRow(active||null);sequence.current=active?.input_sequence||0;
      uncertain.current=Boolean(active&&active.state==='RECOVERY_REQUIRED');setConnected(Boolean(active&&!uncertain.current));
      if(terminal.current)terminal.current.options.disableStdin=!active||uncertain.current;
      pending.current=Promise.resolve();setRevision(v=>v+1);
    }catch(e){if(reply===request.current)setError(e.message)}finally{if(reply===request.current)setLoading(false)}
  };
  // Clear the prior scope before paint, including on a same-session reconnect.
  useLayoutEffect(()=>{attach()},[scope]);
  useEffect(()=>{
    if(!row||current.current?.id!==row.id)return;const id=row.id,epoch=version.current;let live=true,busy=false,timer;
    const tick=async()=>{
      if(busy||!live||epoch!==version.current||current.current?.id!==id)return;busy=true;
      try{
        const value=await api(`/api/terminal/output?workspace=${workspace.id}&id=${id}&after=${cursor.current}`);
        if(!live||epoch!==version.current||current.current?.id!==id)return;
        if(value.reset)terminal.current?.reset();if(value.output)terminal.current?.write(value.output);cursor.current=value.next;
        current.current=value;setRow(value);
        const running=value.state==='RUNNING'&&value.process_alive;
        // Output stays live without rescanning every native history. The sidebar
        // refreshes on explicit actions and actual lifecycle transitions.
        if(!uncertain.current){setConnected(running);if(terminal.current)terminal.current.options.disableStdin=!running;}
        if(!running&&['COMPLETED','FAILED','CANCELLED','RECOVERY_REQUIRED'].includes(value.state)){clearInterval(timer);onChanged?.();}
      }catch(e){if(live&&epoch===version.current){setConnected(false);uncertain.current=true;if(terminal.current)terminal.current.options.disableStdin=true;setError('终端连接未确认，未自动重发输入：'+e.message)}}
      finally{busy=false;}
    };
    tick();timer=setInterval(tick,250);return()=>{live=false;clearInterval(timer)};
  },[row?.id,scope,revision]);
  // Replies own UI state only until the next action, reconnect or scope cleanup.
  // A stale start/close may have executed on the server; never cancel or replay it.
  async function prepare(){const reply=++request.current;setError('');setPreview(null);setLoading(true);try{
    const value=await api('/api/terminal/prepare',{workspace:workspace.id,handle:session.handle});
    if(reply===request.current)setPreview({...value,request:reply});
  }catch(e){if(reply===request.current)setError(e.message)}finally{if(reply===request.current)setLoading(false)}}
  async function start(){if(!preview||preview.request!==request.current||!terminal.current)return;const reply=++request.current;setPreview(null);setLoading(true);setError('');try{
    const value=await api('/api/terminal/start',{id:preview.id,sha256:preview.sha256,
      answer:'本地工作台操作者确认打开此既有只读原生会话；仅本次操作，保持原环境和历史。',cols:Math.max(20,Math.min(300,terminal.current.cols)),rows:Math.max(5,Math.min(100,terminal.current.rows))});
    if(reply!==request.current)return;
    version.current++;current.current=value;cursor.current=0;sequence.current=value.input_sequence||0;uncertain.current=false;
    pending.current=Promise.resolve();terminal.current.reset();terminal.current.options.disableStdin=value.state!=='RUNNING';setRow(value);setRevision(v=>v+1);setPreview(null);setConnected(value.state==='RUNNING'&&value.process_alive);fit.current.fit();terminal.current.focus();onChanged?.();
  }catch(e){if(reply===request.current)setError(e.message)}finally{if(reply===request.current)setLoading(false)}}
  async function close(){const active=current.current;if(!active||active.id!==row?.id)return;const reply=++request.current;setLoading(true);setError('');setPreview(null);try{
    await api('/api/terminal/close',{workspace:workspace.id,id:active.id});if(reply!==request.current)return;
    terminal.current.options.disableStdin=true;setConnected(false);onChanged?.();
  }catch(e){if(reply===request.current)setError(e.message)}finally{if(reply===request.current)setLoading(false)}}
  return <div className="native-terminal"><header><div><Terminal size={17}/><b>{session.title}</b><span>{row?statusInfo(row.state)[0]:'尚未打开'} · {row?.process_alive?'会话由此终端独占':'接管前核验占用'} · 原生只读</span></div><div>
    <button onClick={attach} disabled={loading} aria-label="重新连接终端"><RefreshCw size={14}/>重新连接</button>
    {row?.process_alive?<button onClick={close} disabled={loading}><Square size={14}/>关闭此终端</button>:<button onClick={prepare} disabled={loading||session.choices?.resume===false}><Play size={14}/>打开同一原生会话</button>}
  </div></header><p className="hint">原CLI、目录与会话身份；与工作流共用写入锁。关闭标签只断开显示，关闭终端才停止进程；原生历史保留。输出只保留在本次服务内存中。</p>
    {error&&<p role="alert" className="terminal-error">{error}</p>}
    {preview&&<div className="terminal-confirm"><h3>打开原生只读会话</h3><p>{preview.data.provider} · {preview.data.model} / {preview.data.effort}</p><p>{preview.data.cwd}</p><p>将占用同一会话的原生写入锁；不复制历史、不启动shell、不允许修改工作区。</p><button onClick={()=>setPreview(null)}>取消</button><button onClick={start} disabled={loading}>确认打开原生终端</button></div>}
    <div className="terminal-host" ref={host} aria-label="原生CLI终端" data-connected={connected}/>
    <footer>{connected?'原生进程已连接；键盘输入发送到此唯一PTY':'输入已关闭或连接未确认，不会自动重放'}{row?.reason&&' · '+row.reason}</footer>
  </div>;
}
