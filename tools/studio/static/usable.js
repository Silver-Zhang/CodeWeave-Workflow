'use strict';
const $ = id => document.getElementById(id);
const text = (tag, value, cls) => { const e = document.createElement(tag); e.textContent = value; if(cls)e.className=cls; return e; };
const state = {workspace:null, document:null, identity:crypto.randomUUID(), version:0, saved:null, selected:null,
  profiles:[], verificationProfiles:[], owned:[], drafts:[], run:null, runEpoch:0, workspaceEpoch:0, preview:null};
const fragment = new URLSearchParams(location.hash.slice(1));
if(fragment.has('token')) { sessionStorage.setItem('devflower-stable-token',fragment.get('token')); history.replaceState(null,'',location.pathname); }
const token = sessionStorage.getItem('devflower-stable-token') || '';
function notice(message) { $('notice').textContent=message; }
async function api(path,data) {
  const response=await fetch(path,{method:data===undefined?'GET':'POST',headers:{Authorization:'Bearer '+token,...(data===undefined?{}:{'Content-Type':'application/json'})},body:data===undefined?undefined:JSON.stringify(data)});
  const value=await response.json(); if(!response.ok)throw new Error(value.error||'请求失败'); return value;
}
function act(id, fn) { $(id).addEventListener('click',async()=>{try{await fn();}catch(e){notice(e.message);}}); }
function changed() { state.version++; state.preview=null; $('preview').replaceChildren(); $('save-state').textContent='当前改动未保存'; }
function options(select, values, selected) {
  select.replaceChildren(...values.map(([value,label])=>{ const e=text('option',label);e.value=value;return e;}));
  if(selected!==undefined)select.value=selected;
}
function loadDocument(document,saved=null) {
  state.document=structuredClone(document);state.identity=crypto.randomUUID();state.version=0;state.saved=saved;state.selected=null;
  state.preview=null;$('preview').replaceChildren();$('workflow-name').value=document.name;$('max-rounds').value=document.max_rounds;
  $('save-state').textContent=saved?'已加载保存版本':'新草稿未保存';draw();
}
async function newDraft() {
  const requested=$('template').value, identity=state.identity;
  const document=await api('/api/template?kind='+encodeURIComponent(requested));
  if(identity!==state.identity)return; loadDocument(document);
}
async function status() {
  const value=await api('/api/status');state.profiles=value.profiles;state.verificationProfiles=value.verification_profiles||[];state.drafts=value.drafts;
  $('trust').textContent='Stable '+value.stable.slice(0,16);
  options($('recent'),[['','最近工作区'],...value.workspaces.map(w=>[w.id,w.path])],state.workspace?.id);
  options($('drafts'),[['','已保存流程'],...value.drafts.map(d=>[d.id,d.document.name])],state.saved?.id);
  options($('runs'),[['','选择运行'],...value.runs.filter(r=>!state.workspace||r.project===state.workspace.id).map(r=>[r.id,r.id.slice(0,12)+' · '+r.state])],state.run);
  state.workspaces=value.workspaces;
}
function setWorkspace(workspace) {
  state.workspace=workspace;state.workspaceEpoch++;state.owned=[];state.preview=null;state.run=null;state.runEpoch++;
  $('workspace-path').value=workspace.path;$('workspace-info').textContent=`${workspace.path} · ${workspace.branch} · ${workspace.head}`;
  $('sessions').replaceChildren();$('preview').replaceChildren();$('monitor').replaceChildren();$('run-title').textContent='未选择运行';status().catch(e=>notice(e.message));
}
async function saveDraft() {
  const identity=state.identity, version=state.version, document=structuredClone(state.document), saved=state.saved?{...state.saved}:null;
  const result=await api('/api/draft',{document,id:saved?.id||null,expected:saved?.revision||null});
  if(identity===state.identity) {
    // A concurrent response must not replace a newer confirmed revision.
    const stillExpected=state.saved?.revision===(saved?.revision);
    if(stillExpected||!state.saved&&!saved)state.saved={id:result.id,revision:result.revision};
    $('save-state').textContent=version===state.version?'该快照已保存':'请求发出时的快照已保存；当前仍有未保存改动';
  }
  await status();
}
function field(parent,label,key,value,type='text',choices=null) {
  const labelNode=text('label',label); const input=document.createElement(choices?'select':type==='textarea'?'textarea':'input');
  if(choices)options(input,choices,value);else if(type==='checkbox'){input.type='checkbox';input.checked=value;}else{input.type=type;input.value=value;}
  input.dataset.field=key;labelNode.append(input);parent.append(labelNode);
  input.addEventListener('change',()=>{
    const n=state.document.nodes.find(n=>n.id===state.selected);if(!n)return;
    const result=type==='checkbox'?input.checked:type==='number'?Number(input.value):input.value;
    if(key==='label')n.label=result;else n.config[key]=result;changed();draw(false);if(n.type==='verifier'&&key==='profile')configure();
  });return input;
}
function configure() {
  const parent=$('node-config');parent.replaceChildren();
  const n=state.document.nodes.find(n=>n.id===state.selected);if(!n){parent.append(text('p','选择节点以编辑。'));return;}
  parent.append(text('strong',n.type+' · '+n.id));field(parent,'显示名称','label',n.label);
  const c=n.config;
  if(['developer','reviewer','planner'].includes(n.type)) {
    field(parent,'Provider','provider',c.provider,'text',[['codex','Codex'],['claude','Claude Code']]);
    field(parent,'运行配置','profile',c.profile,'text',state.profiles.map(p=>[p.id,`${p.provider} · ${p.model} / ${p.effort}`]));
    const role=n.type==='developer'?'implementer':n.type;
    field(parent,'原生会话','session',c.session,'text',[['new','新建独立原生会话'],...state.owned.filter(s=>s.role===role&&s.provider===c.provider&&s.resume).map(s=>[s.id,s.id])]);
    field(parent,'请求模型（unknown 使用已批准配置）','model',c.model);
    field(parent,'请求 effort（unknown 使用已批准配置）','effort',c.effort);
    field(parent,'系统职责','responsibility',c.responsibility,'textarea');
    field(parent,'项目背景','background',c.background,'textarea');
    field(parent,'步骤预算（秒，30–3600）','timeout_seconds',c.timeout_seconds,'number');
    field(parent,'子 Agent（当前执行器不支持，启用将拒绝运行）','subagents',c.subagents,'checkbox');
    parent.append(text('p','允许工具'));
    for(const tool of c.provider==='codex'?['native']:['Read','Glob','Grep','Bash','Write','Edit']) {
      const label=text('label',tool),input=document.createElement('input');input.type='checkbox';input.checked=c.tools.includes(tool);label.prepend(input);parent.append(label);
      input.addEventListener('change',()=>{c.tools=input.checked?[...new Set([...c.tools,tool])]:c.tools.filter(t=>t!==tool);changed();});
    }
    parent.append(text('p','实际模型和 effort 在运行结果中展示；服务未返回的字段为 unknown。'));
  } else if(n.type==='verifier') {
    field(parent,'固定验证配置','profile',c.profile,'text',['json-assertions','baseline','javascript'].map(x=>[x,x]));
    if(c.profile==='json-assertions')field(parent,'已注册的断言合同','target',c.target,'text',state.verificationProfiles.map(p=>[p.id,`${p.id} · ${p.cases.length} 项断言`]));
    else field(parent,'源码相对路径','target',c.target);
    parent.append(text('p','用例由可信父进程计数；不接受候选自报 unittest 计数。'));
    field(parent,'最低实际测试数','min_cases',c.min_cases,'number');field(parent,'最多 Skip','max_skipped',c.max_skipped,'number');
  } else if(n.type==='human_gate')field(parent,'实际人工确认问题','question',c.question,'textarea');
  else parent.append(text('p','交付权限在当次授权预览中确认；改连线不能绕过测试与独立审核。'));
}
function draw(config=true) {
  if(!state.document)return;
  const svg=$('canvas'), ns='http://www.w3.org/2000/svg';svg.replaceChildren();
  const create=(tag,attrs)=>{const e=document.createElementNS(ns,tag);for(const[k,v]of Object.entries(attrs))e.setAttribute(k,v);return e;};
  const nodes=new Map(state.document.nodes.map(n=>[n.id,n]));
  for(const edge of state.document.edges) {
    const a=nodes.get(edge.source),b=nodes.get(edge.target);if(!a||!b)continue;
    svg.append(create('line',{x1:a.x+100,y1:a.y+35,x2:b.x+100,y2:b.y+35,class:edge.on==='repair'?'repair':''}));
  }
  for(const n of nodes.values()) {
    const group=create('g',{class:'node'+(n.id===state.selected?' selected':''),transform:`translate(${n.x},${n.y})`});
    group.append(create('rect',{width:200,height:70,rx:8}));
    const label=create('text',{x:12,y:29});label.textContent=n.label.slice(0,22);group.append(label);
    const kind=create('text',{x:12,y:51});kind.textContent=n.type;group.append(kind);svg.append(group);
    group.addEventListener('pointerdown',event=>{
      state.selected=n.id;configure();
      const start={x:event.clientX,y:event.clientY,nx:n.x,ny:n.y};group.setPointerCapture(event.pointerId);
      const move=e=>{n.x=Math.round(Math.max(0,Math.min(10000,start.nx+(e.clientX-start.x)*1100/svg.clientWidth)));n.y=Math.round(Math.max(0,Math.min(10000,start.ny+(e.clientY-start.y)*550/svg.clientHeight)));group.setAttribute('transform',`translate(${n.x},${n.y})`);};
      const up=()=>{group.removeEventListener('pointermove',move);group.removeEventListener('pointerup',up);changed();draw(false);};
      group.addEventListener('pointermove',move);group.addEventListener('pointerup',up);
    });
  }
  const choices=state.document.nodes.map(n=>[n.id,n.label+' ('+n.id+')']);
  options($('edge-source'),choices);options($('edge-target'),choices);
  $('edges').replaceChildren(...state.document.edges.map((e,i)=>{const li=text('li',`${e.source} → ${e.target} · ${e.on}`),button=text('button','删除连线');button.addEventListener('click',()=>{state.document.edges.splice(i,1);changed();draw(false);});li.append(button);return li;}));
  if(config)configure();
}
async function sessions() {
  if(!state.workspace)throw new Error('先打开工作区');
  const epoch=state.workspaceEpoch, value=await api('/api/sessions?workspace='+state.workspace.id);
  if(epoch!==state.workspaceEpoch)return;state.owned=value.owned;$('sessions').replaceChildren();
  for(const row of value.owned) {
    const card=text('div','', 'card');card.append(text('strong',`${row.role} · ${row.id}`),text('p',`${row.state} · model ${row.resolved_model} / effort ${row.resolved_effort}`),
      text('p',`HOME ${row.home}`),text('p',`原生记录 ${row.native_records}`),text('p',row.resume?'可在对应角色节点明确选择此会话':'运行中的会话不可重复占用'));
    $('sessions').append(card);
  }
  const discovered=value.discovery.sessions||[];
  for(const row of discovered)$('sessions').append(text('div',`${row.provider||row.tool||'native'} · ${row.session_id||row.id} · 外部发现，运行未确认`,'card'));
  if(!value.owned.length&&!discovered.length)$('sessions').append(text('p','此工作区尚无可显示会话。首次运行将创建持久原生会话。'));
  configure();
}
function taskInput() {
  return {title:$('task-title').value,body:$('task-body').value,scope:$('task-scope').value.split('\n').map(x=>x.trim()).filter(Boolean),
    acceptance:$('task-acceptance').value,issue_url:$('issue-url').value};
}
async function prepare() {
  if(!state.workspace)throw new Error('先打开工作区');
  const identity=state.identity,version=state.version,epoch=state.workspaceEpoch,input=taskInput(),delivery=$('delivery').checked;
  const value=await api('/api/prepare',{workspace:state.workspace.id,workflow:state.document,task:input,delivery:{commit:delivery,push:delivery,pr:delivery}});
  if(identity!==state.identity||version!==state.version||epoch!==state.workspaceEpoch||JSON.stringify(taskInput())!==JSON.stringify(input)||$('delivery').checked!==delivery)return;
  state.preview=value;const parent=$('preview');parent.replaceChildren();
  parent.append(text('h3','确认本次合同与权限'),text('p',`工作区 ${value.data.source.root} · ${value.data.source.branch} · ${value.data.source.head}`),
    text('p',`源码 ${value.data.source_sha256}`),text('p',`合同预览 SHA ${value.sha256}`),
    text('p',`允许路径：${input.scope.join(', ')}；外部模型将接收这些源码。`),
    text('p',delivery?'允许受审候选 commit/push/PR；不允许 merge、force、delete、release。':'仅开发、验证与审核；不允许 Git 交付。'));
  const target=value.data.config.github_delivery;
  if(target)parent.append(text('p',`GitHub ${target.repository} · ${target.branch} → ${target.base}`),
    text('p',`绑定 PR：${target.existing_pr===null?'新建':`#${target.existing_pr}`} · 预期远端 tip：${target.expected_tip||'分支尚不存在'}`));
  parent.append(text('p',`测试隔离：${value.data.config.verification_isolation||'landlock'}`));
  for(const[role,b]of Object.entries(value.data.config.bindings))parent.append(text('p',`${role}: ${b.provider} · ${b.model}/${b.effort} · ${b.session_id||'新会话'} · ${b.timeout_seconds} 秒`));
  const tests=document.createElement('details');tests.append(text('summary','查看绑定的测试断言与执行配置'),text('pre',JSON.stringify(value.data.config.policy.verification,null,2)));parent.append(tests);
  const answers=value.data.human_questions.map(question=>{const label=text('label',question),answer=document.createElement('textarea');answer.rows=2;label.append(answer);parent.append(label);return answer;});
  const button=text('button','人工确认并运行');
  button.addEventListener('click',async()=>{
    if(state.preview!==value)return;button.disabled=true;
    try{
      const result=await api('/api/authorize-run',{permit:value.id,sha256:value.sha256,answers:answers.map(a=>a.value)});
      state.preview=null;parent.replaceChildren(text('p','已使用本次授权，运行 '+result.run_id));selectRun(result.run_id);await status();
    }catch(e){notice(e.message);parent.append(text('p','授权可能已消费，请检查运行列表；不要盲目重试。'));}
  });parent.append(button);
}
function selectRun(run) {
  state.run=run||null;state.runEpoch++;$('monitor').replaceChildren();$('run-title').textContent=run?'读取 '+run+'…':'未选择运行';poll();
}
function renderSnapshot(run,snapshot) {
  $('run-title').textContent=`${run} · ${snapshot.state||'UNKNOWN'} · round ${snapshot.round??'unknown'}`;
  const renderKey=[run,snapshot.state,snapshot.round,snapshot.candidate].join(':');
  if(snapshot.human_gate&&state.renderKey===renderKey&&$('g4-answer'))return;
  state.renderKey=renderKey;
  const parent=$('monitor');parent.replaceChildren();
  if(snapshot.reason)parent.append(text('p',snapshot.reason));
  if(snapshot.current_agent) {
    const a=snapshot.current_agent;
    parent.append(text('p',`${a.role} · ${a.provider} · 会话 ${a.session_id} · 请求 ${a.requested_model}/${a.requested_effort} · PID ${a.process?.pid??'unknown'} · ${a.alive?'实际进程存活':'进程已结束或活性未确认'}`));
  }
  const stages=text('div','','row');
  for(const n of snapshot.graph?.nodes||[]) {
    const c=n.counts;
    stages.append(text('div',`${n.label}: ${n.status}${c?` · ${c.tests} tests / ${c.failures} failures / ${c.errors} errors / ${c.skipped} skipped`:''}`,'card'));
  }
  parent.append(stages);
  if(snapshot.verdict)parent.append(text('p','本轮独立审核：'+snapshot.verdict));
  for(const finding of snapshot.findings||[])parent.append(text('p',`${finding.id} · ${finding.status} · ${finding.title}`));
  if(snapshot.github_receipt?.pr?.url) {
    const link=text('a','打开开发 PR');link.href=snapshot.github_receipt.pr.url;link.target='_blank';link.rel='noopener noreferrer';parent.append(link);
  }
  if(snapshot.human_gate) {
    const label=text('label',snapshot.human_gate.question),answer=document.createElement('textarea'),approve=text('button','确认当前候选的 G4 结果解释');answer.id='g4-answer';
    label.append(answer);parent.append(label,approve);
    approve.addEventListener('click',async()=>{if(state.run!==run)return;approve.disabled=true;try{
      await api('/api/approve-result',{run_id:run,answer:answer.value});await poll();
    }catch(e){notice(e.message);approve.disabled=false;}});
  }
  if(snapshot.candidate) {
    const diffButton=text('button','查看固定候选差异'),diffArea=document.createElement('pre');parent.append(diffButton,diffArea);
    diffButton.addEventListener('click',async()=>{try{
      const value=await api('/api/diff?id='+encodeURIComponent(run));
      if(state.run!==run||value.run_id!==run||value.candidate!==snapshot.candidate||!diffArea.isConnected)return;
      diffArea.textContent=(value.truncated?'差异超过显示上限，以下仅为前 200 KB。\n':'')+value.text;
    }catch(e){if(diffArea.isConnected)diffArea.textContent=e.message;}});
  }
  for(const[role,a]of Object.entries(snapshot.agents||{}))parent.append(text('div',`${role} 最近完成结果（round ${a.result_round??'unknown'}）: ${a.session_id} · ${a.resolved_model??'unknown'} / ${a.resolved_effort??'unknown'} · PID ${a.process?.process?.pid??'unknown'}`,'card'));
  // The whole monitoring panel is replaced from a single identity-checked snapshot.
  for(const[key,value]of Object.entries(snapshot)) {
    if(['agents','run_id','state','round','reason'].includes(key))continue;
    const detail=document.createElement('details');detail.append(text('summary',key),text('pre',JSON.stringify(value,null,2)));parent.append(detail);
  }
}
async function poll() {
  const run=state.run;if(!run)return;const epoch=++state.runEpoch;
  try{const snapshot=await api('/api/run?id='+encodeURIComponent(run));if(state.run!==run||epoch!==state.runEpoch)return;
    if((snapshot.run_id||snapshot.id)!==run)throw new Error('运行快照身份不匹配');renderSnapshot(run,snapshot);
  }catch(e){if(state.run!==run||epoch!==state.runEpoch)return;$('run-title').textContent=run+' · 状态未确认';$('monitor').replaceChildren(text('p',e.message,'error'));}
}
act('open-workspace',async()=>{const epoch=++state.workspaceEpoch;const w=await api('/api/workspace',{path:$('workspace-path').value});if(epoch===state.workspaceEpoch)setWorkspace(w);});
$('recent').addEventListener('change',()=>{const w=state.workspaces.find(w=>w.id===$('recent').value);if(w)setWorkspace(w);});
act('new-draft',newDraft);act('save',saveDraft);
$('drafts').addEventListener('change',()=>{const d=state.drafts.find(d=>d.id===$('drafts').value);if(d)loadDocument(d.document,{id:d.id,revision:d.revision});});
$('workflow-name').addEventListener('input',()=>{state.document.name=$('workflow-name').value;changed();});
$('max-rounds').addEventListener('change',()=>{state.document.max_rounds=Number($('max-rounds').value);changed();});
act('add-node',async()=>{const identity=state.identity,n=await api('/api/node?kind='+$('add-kind').value);if(identity!==state.identity)return;n.id=n.type+'-'+crypto.randomUUID().slice(0,8);n.x=100;n.y=200;state.document.nodes.push(n);state.selected=n.id;changed();draw();});
act('delete-node',()=>{state.document.nodes=state.document.nodes.filter(n=>n.id!==state.selected);state.document.edges=state.document.edges.filter(e=>e.source!==state.selected&&e.target!==state.selected);state.selected=null;changed();draw();});
act('connect',()=>{state.document.edges.push({source:$('edge-source').value,target:$('edge-target').value,on:$('edge-on').value});changed();draw(false);});
act('compile',async()=>{const identity=state.identity,version=state.version,p=await api('/api/compile',{document:state.document});if(identity===state.identity&&version===state.version)notice('可执行顺序：'+p.order.join(' → '));});
act('refresh-sessions',sessions);act('refresh-runs',status);
act('import-issue',async()=>{const epoch=state.workspaceEpoch,url=$('issue-url').value,v=await api('/api/issue',{url});if(epoch!==state.workspaceEpoch||url!==$('issue-url').value)return;$('task-title').value=v.title;$('task-body').value=v.body;$('task-acceptance').value=v.body;state.preview=null;$('preview').replaceChildren();notice('已导入真实 Issue，请核对允许路径与验收文本。');});
for(const id of ['task-title','task-body','task-scope','task-acceptance','issue-url','delivery'])$(id).addEventListener('input',()=>{state.preview=null;$('preview').replaceChildren();});
act('prepare',prepare);$('runs').addEventListener('change',()=>selectRun($('runs').value));
act('resume',async()=>{if(!state.run)throw new Error('选择运行');await api('/api/resume',{run_id:state.run});await poll();});
act('cancel',async()=>{if(!state.run)throw new Error('选择运行');await api('/api/cancel',{run_id:state.run});await poll();});
setInterval(poll,2000);
(async()=>{try{await status();await newDraft();notice('Stable 身份已核验。打开工作区开始。');}catch(e){notice(e.message);}})();
