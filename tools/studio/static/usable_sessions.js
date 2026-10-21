/* Real HTTP session center. All session actions use workspace-bound handles. */
'use strict';
window.sessionDesk = new class {
  constructor() {
    this.epoch=0;this.historyEpoch=0;this.composeEpoch=0;this.selected=null;this.workspace=null;this.timer=null;this.preview=null;
    const action=(id,fn)=>$(id).addEventListener('click',()=>Promise.resolve().then(fn).catch(e=>notice(e.message)));
    action('session-new',()=>this.compose(null));
    action('session-search',()=>this.history(this.selected));
    action('session-continue',()=>this.compose(this.selected));
    action('session-prepare',()=>this.prepare());
    action('session-register',async()=>{
      const workspace=state.workspace?.id;if(!workspace)throw new Error('先打开工作区');
      await api('/api/session/register',{workspace,provider:$('session-register-provider').value,config_root:$('session-register-root').value});
      if(workspace===state.workspace?.id)await this.refresh();
    });
    $('session-hidden').addEventListener('change',()=>this.refresh().catch(e=>notice(e.message)));
    for(const id of ['session-profile','session-permission','session-prompt'])$(id).addEventListener('input',()=>{
      this.composeEpoch++;this.preview=null;$('session-preview').replaceChildren();
    });
    document.querySelectorAll('[data-go="sessions"]').forEach(b=>b.addEventListener('click',()=>this.refresh().catch(e=>notice(e.message))));
  }
  invalidate() {
    this.epoch++;this.historyEpoch++;this.composeEpoch++;this.preview=null;clearTimeout(this.timer);
    $('session-preview').replaceChildren();
  }
  async refresh() {
    const workspace=state.workspace?.id;if(!workspace)throw new Error('先打开工作区');
    const request=++this.epoch;clearTimeout(this.timer);
    if(this.workspace!==workspace){
      this.workspace=workspace;this.selected=null;this.historyEpoch++;this.preview=null;
      $('session-history').hidden=true;$('session-compose').hidden=true;$('session-messages').replaceChildren();
    }
    const value=await api('/api/sessions?workspace='+workspace+'&hidden='+$('session-hidden').checked);
    if(request!==this.epoch||workspace!==state.workspace?.id)return;
    if(value.workspace_id!==workspace)throw new Error('会话响应的工作区不匹配');
    state.owned=value.owned||[];const rows=value.discovery.sessions||[];$('sessions').replaceChildren();
    if(this.selected){
      this.selected=rows.find(row=>row.handle===this.selected.handle)||null;
      $('session-continue').disabled=!this.selected?.resume||state.workspace.execution_allowed===false;
      if(!this.selected){this.composeEpoch++;this.preview=null;$('session-preview').replaceChildren();$('session-compose').hidden=true;$('session-history').hidden=true;}
    }
    $('session-summary').textContent=`${rows.length} 个已授权可读会话 · 外部会话的进程状态未确认`;
    $('session-new').disabled=state.workspace.execution_allowed===false;
    $('session-coverage').textContent=JSON.stringify({coverage:value.discovery.coverage,nested:value.discovery.nested_coverage,profiles:value.discovery.profile_coverage,capabilities:value.capabilities},null,2);
    for(const row of rows){
      const card=text('article','', 'card session-card');card.dataset.handle=row.handle;
      card.append(text('strong',`${row.provider} · ${row.session_id}${row.hidden?' · DevFlower 已隐藏':''}`),
        text('p',`Profile ${row.profile_id} · ${row.storage_root}`),text('p',`cwd ${row.cwd} · ${row.association}`),
        text('p',`${row.status} · ${row.note}`));
      const read=text('button','查看历史');read.addEventListener('click',()=>this.history(row).catch(e=>notice(e.message)));
      read.disabled=!row.capabilities.read;
      const hide=text('button',row.hidden?'取消隐藏':'在 DevFlower 隐藏');hide.addEventListener('click',async()=>{
        try{await api('/api/session/visibility',{workspace,handle:row.handle,hidden:!row.hidden});if(workspace===state.workspace?.id)await this.refresh();}catch(e){notice(e.message);}
      });
      const archive=text('button','原生归档（不支持）'),remove=text('button','删除原始会话（不支持）');
      archive.disabled=true;remove.disabled=true;remove.title=archive.title='无安全原生 CLI 接口；不会修改文件、子会话、源码或 worktree';
      card.append(read,hide,archive,remove);$('sessions').append(card);
    }
    for(const row of state.owned)if(!rows.some(s=>s.session_id===row.id&&s.provider===row.provider))
      $('sessions').append(text('p',`${row.role} · ${row.provider} · ${row.id} · ${row.state} · 原生记录尚不可读，不能接管`));
    if(!rows.length)$('sessions').append(text('p','未发现匹配的原生记录。可登记受批准的隔离 Profile，或在可执行工作区新建。'));
    this.operations(value.operations||[],workspace);
    if(!$('node-config').contains(document.activeElement))configure();
    if((value.operations||[]).some(x=>!['COMPLETED','FAILED','CANCELLED'].includes(x.state))&&!$('panel-sessions').hidden)
      this.timer=setTimeout(()=>this.refresh().catch(e=>notice(e.message)),1500);
  }
  async history(row) {
    if(!row)return;const workspace=state.workspace?.id,epoch=++this.historyEpoch;
    if(this.selected?.handle!==row.handle){this.composeEpoch++;this.preview=null;$('session-preview').replaceChildren();$('session-compose').hidden=true;}
    this.selected=row;
    $('session-history').hidden=false;$('session-history-title').textContent=`${row.provider} · ${row.session_id}`;
    $('session-messages').replaceChildren(text('p','读取脱敏历史…'));$('session-continue').disabled=!row.resume||state.workspace.execution_allowed===false;
    const value=await api('/api/session/history?'+new URLSearchParams({workspace,handle:row.handle,query:$('session-query').value}));
    if(epoch!==this.historyEpoch||workspace!==state.workspace?.id||this.selected?.handle!==row.handle)return;
    if(value.workspace_id!==workspace||value.handle!==row.handle)throw new Error('历史响应身份不匹配');
    $('session-messages').replaceChildren(...value.messages.map(m=>{const card=text('article','', 'card');card.append(text('strong',m.role),text('pre',m.text));return card;}));
    if(!value.messages.length)$('session-messages').append(text('p','没有符合条件的可见消息；工具输入输出与隐藏推理不展示。'));
  }
  compose(row) {
    if(state.workspace?.execution_allowed===false)throw new Error('工作区只读；打开目录或登记存储不授予执行权限');
    if(row&&!row.resume)throw new Error(row.note||'此原生会话仅可读取');
    this.composeEpoch++;this.selected=row;this.preview=null;$('session-preview').replaceChildren();$('session-compose').hidden=false;
    $('session-compose-title').textContent=row?`继续精确会话 ${row.session_id}`:'新建独立原生会话';
    const profiles=state.profiles.filter(p=>!row||p.provider===row.provider);
    options($('session-profile'),profiles.map(p=>[p.id,`${p.provider} · ${p.model}/${p.effort}`]));
    $('session-prompt').focus();
  }
  async prepare() {
    const workspace=state.workspace?.id,epoch=this.epoch,composeEpoch=++this.composeEpoch,selected=this.selected?.handle||'new';
    this.preview=null;$('session-preview').replaceChildren();
    const input={workspace,handle:selected,profile:$('session-profile').value,prompt:$('session-prompt').value,permission:$('session-permission').value};
    const value=await api('/api/session/prepare',input);
    if(composeEpoch!==this.composeEpoch||epoch!==this.epoch||workspace!==state.workspace?.id||selected!==(this.selected?.handle||'new')||input.prompt!==$('session-prompt').value||input.profile!==$('session-profile').value||input.permission!==$('session-permission').value)return;
    this.preview=value;const parent=$('session-preview');parent.replaceChildren();const b=value.data.binding;
    parent.append(text('p',`${b.provider} · ${b.model}/${b.effort} · UUID ${b.session_id||'由原生 CLI 回执确定'} · HOME ${b.home} · cwd ${value.data.cwd} · ${value.data.permission} · tools ${b.tools.join(', ')}`));
    const answer=document.createElement('input');answer.setAttribute('aria-label','本次原生会话实际确认');answer.placeholder='确认此消息、原环境及本次权限';
    const send=text('button','确认并发送给原生 CLI');send.addEventListener('click',async()=>{
      if(this.preview!==value||composeEpoch!==this.composeEpoch||workspace!==state.workspace?.id)return;send.disabled=true;
      try{
        const result=await api('/api/session/authorize',{permit:value.id,sha256:value.sha256,answer:answer.value});
        if(workspace!==state.workspace?.id)return;this.preview=null;parent.replaceChildren(text('p',`操作 ${result.id} · ${result.state}`));
        await this.refresh();
      }catch(e){notice(e.message+'；授权可能已消费，请先刷新操作记录。');this.preview=null;await this.refresh().catch(()=>{});}
    });parent.append(answer,send);
  }
  operations(rows,workspace) {
    $('session-operations').replaceChildren();
    for(const row of rows){
      const card=text('article','', 'card');card.dataset.operation=row.id;
      card.append(text('strong',`${row.provider} · ${row.state}`),text('p',`操作 ${row.id} · 会话 ${row.session_id||(row.requested_session?'请求 UUID '+row.requested_session+'（待原生回执确认）':'原生 UUID 尚未确认')}`),
        text('p',`${row.model}/${row.effort} · cwd ${row.cwd} · ${row.permission} · PID ${row.process?.pid||'未知'} · ${row.alive?'实际进程存活':'实际进程未运行或未知'}`));
      if(row.reason)card.append(text('p',row.reason));if(row.reply)card.append(text('pre',row.reply));
      if(row.receipt){const details=document.createElement('details');details.append(text('summary','原生执行回执'),text('pre',JSON.stringify(row.receipt,null,2)));card.append(details);}
      if(!['COMPLETED','FAILED','CANCELLED'].includes(row.state)){
        const cancel=text('button','停止此操作');cancel.addEventListener('click',async()=>{
          try{await api('/api/session/cancel',{workspace,id:row.id});if(workspace===state.workspace?.id)await this.refresh();}catch(e){notice(e.message);}
        });card.append(cancel);
      }
      $('session-operations').append(card);
    }
  }
}();
