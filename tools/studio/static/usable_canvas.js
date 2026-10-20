'use strict';
// Geometry and pointer ownership belong to the editor, never to the runtime.
class WorkflowCanvas {
  constructor(svg, callbacks) {
    this.svg=svg;this.callbacks=callbacks;this.view={x:0,y:0,w:1100,h:620};
    this.selection=null;this.edgeSelection=null;this.gesture=null;
    svg.addEventListener('pointerdown',e=>this.down(e));
    svg.addEventListener('pointermove',e=>this.move(e));
    svg.addEventListener('pointerup',e=>this.finish(e));
    svg.addEventListener('pointercancel',()=>this.cancel());
    svg.addEventListener('lostpointercapture',()=>this.cancel());
    svg.addEventListener('dblclick',e=>{
      if(e.target.closest('[data-canvas-action],[data-port]'))return;
      const node=e.target.closest('[data-node]'),id=node?.dataset.node||this.clickNode;
      if(id)this.callbacks.select(id);
      else if(!this.readonly)this.callbacks.addAfter?.(null,null,this.point(e));
    });
    svg.addEventListener('contextmenu',e=>{
      if(this.readonly)return;
      e.preventDefault();const node=e.target.closest('[data-node]');
      if(node){this.callbacks.select(node.dataset.node,true);this.callbacks.menu?.(node.dataset.node,e.clientX,e.clientY);}
      else this.callbacks.addAfter?.(null,null,this.point(e));
    });
    svg.addEventListener('dragover',e=>{
      if(!this.readonly&&e.dataTransfer.types.includes('application/x-devflower-node')){e.preventDefault();e.dataTransfer.dropEffect='copy';}
    });
    svg.addEventListener('drop',e=>{
      if(this.readonly)return;
      const kind=e.dataTransfer.getData('application/x-devflower-node');if(!kind)return;
      e.preventDefault();this.callbacks.drop?.(kind,this.point(e));
    });
    svg.addEventListener('wheel',e=>{e.preventDefault();this.zoom(e.deltaY<0?1.15:1/1.15,e);},{passive:false});
    svg.addEventListener('keydown',e=>{
      const action=e.target.closest('[data-canvas-action]');
      if(action&&['Enter',' '].includes(e.key)){e.preventDefault();this.action(action);return;}
      if(e.key==='Escape'){this.cancel();this.edgeSelection=null;if(this.document)this.render(this.document,this.selection);}
      if(!this.readonly&&['Delete','Backspace'].includes(e.key)){e.preventDefault();this.callbacks.remove(this.edgeSelection);}
      if((e.key==='Enter'||e.key===' ')&&e.target.dataset.node){e.preventDefault();this.callbacks.select(e.target.dataset.node);}
    });
    this.updateView();
  }
  create(tag,attrs={}) {
    const e=document.createElementNS('http://www.w3.org/2000/svg',tag);
    for(const[k,v]of Object.entries(attrs))e.setAttribute(k,v);
    return e;
  }
  action(element) {
    if(this.readonly)return;
    const kind=element.dataset.canvasAction;
    if(kind==='add')this.callbacks.addAfter?.(element.dataset.source);
    if(kind==='insert')this.callbacks.addAfter?.(element.dataset.source,Number(element.dataset.edgeIndex));
    if(kind==='remove')this.callbacks.remove(Number(element.dataset.edgeIndex));
  }
  button(label,attrs,x,y,symbol) {
    const g=this.create('g',{...attrs,transform:`translate(${x},${y})`,role:'button',tabindex:0,'aria-label':label});
    if(attrs.class==='node-add')g.append(this.create('rect',{x:-16,y:-16,width:32,height:42,class:'action-hit'}));
    g.append(this.create('circle',{r:12}));
    const t=this.create('text',{'text-anchor':'middle',dy:4});t.textContent=symbol;
    const title=this.create('title');title.textContent=label;g.append(t,title);return g;
  }
  label(value) {
    let width=0,result='';
    for(const char of value){width+=char.codePointAt(0)>255?2:1;if(width>22)return result+'…';result+=char;}
    return result;
  }
  point(event) {
    // inverse CTM includes preserveAspectRatio, CSS size, and viewport pan/zoom.
    const p=this.svg.createSVGPoint();p.x=event.clientX;p.y=event.clientY;
    return p.matrixTransform(this.svg.getScreenCTM().inverse());
  }
  updateView() {
    const v=this.view;this.svg.setAttribute('viewBox',`${v.x} ${v.y} ${v.w} ${v.h}`);
    this.callbacks.viewport?.(Math.round(1100/v.w*100));
  }
  zoom(factor,event=null) {
    if(this.gesture)return;
    const p=event?this.point(event):{x:this.view.x+this.view.w/2,y:this.view.y+this.view.h/2};
    const scale=Math.max(350,Math.min(4400,this.view.w/factor))/this.view.w;
    this.view={x:p.x+(this.view.x-p.x)*scale,y:p.y+(this.view.y-p.y)*scale,w:this.view.w*scale,h:this.view.h*scale};
    this.updateView();
  }
  fit() {
    if(this.gesture)this.cancel();
    const ns=this.document?.nodes||[];
    if(!ns.length)this.view={x:0,y:0,w:1100,h:620};
    else {
      const x=Math.min(...ns.map(n=>n.x))-75,y=Math.min(...ns.map(n=>n.y))-100;
      const w=Math.max(...ns.map(n=>n.x+245))-x+75,h=Math.max(...ns.map(n=>n.y+82))-y+110;
      // Fitting should reveal the whole graph without inflating a small graph.
      this.view={x,y,w:Math.max(w,h*1100/620,1100),h:Math.max(h,w*620/1100,620)};
    }
    this.updateView();
  }
  path(a,b,repair=false) {
    if(repair){
      const x=a.x+105,y=a.y+82,tx=b.x+105,ty=b.y+82,via=Math.max(y,ty)+95;
      return `M ${x} ${y} C ${x} ${via}, ${tx} ${via}, ${tx} ${ty}`;
    }
    const x=a.x+210,y=a.y+41,tx=b.x,ty=b.y+41,d=Math.max(65,Math.abs(tx-x)*.5);
    if(tx<x&&Math.abs(ty-y)>100){const mid=(y+ty)/2;return `M ${x} ${y} C ${x+55} ${y}, ${x+55} ${mid}, ${x} ${mid} L ${tx} ${mid} C ${tx-55} ${mid}, ${tx-55} ${ty}, ${tx} ${ty}`;}
    return `M ${x} ${y} C ${x+d} ${y}, ${tx-d} ${ty}, ${tx} ${ty}`;
  }
  render(doc,selection=null) {
    if(this.gesture)this.cancel();
    if(this.document!==doc)this.edgeSelection=null;
    this.document=doc;this.selection=selection;this.svg.replaceChildren();
    const defs=this.create('defs');
    for(const name of ['next','repair']){
      const marker=this.create('marker',{id:'arrow-'+name,viewBox:'0 0 10 10',refX:9,refY:5,markerWidth:7,markerHeight:7,orient:'auto-start-reverse'});
      marker.append(this.create('path',{d:'M 0 0 L 10 5 L 0 10 z',class:name}));defs.append(marker);
    }
    this.svg.append(defs);this.edges=this.create('g',{class:'connections'});this.svg.append(this.edges);
    this.redrawEdges();
    for(const n of doc.nodes) {
      const g=this.create('g',{'data-node':n.id,tabindex:0,role:'button','aria-label':`${n.label} · ${n.id}${this.readonly?' · '+n.status:''}`,class:'node '+n.type+(this.readonly?' status-'+n.status:'')+(n.id===selection?' selected':''),transform:`translate(${n.x},${n.y})`});
      g.append(this.create('rect',{width:210,height:82,rx:9,class:'node-body'}));
      const full=this.create('title');full.textContent=n.label;g.append(full);
      const icon=this.create('g',{class:'node-icon',transform:'translate(16,20)'});
      icon.append(this.create('rect',{width:30,height:30,rx:7}));
      const glyph=this.create('text',{x:15,y:21,'text-anchor':'middle'});
      glyph.textContent=({human_gate:'◎',authorization:'◎',planner:'◇',developer:'⌘',implementer:'⌘',verifier:'✓',verification:'✓',reviewer:'◈',delivery:'↗'})[n.type]||'◷';
      icon.append(glyph);g.append(icon);
      const title=this.create('text',{x:57,y:30,class:'node-label'});title.textContent=this.label(n.label);
      const roles={human_gate:'任务与授权',authorization:'任务授权',planner:'规划',developer:'Codex · 实施',implementer:'Codex · 实施',verifier:'测试验证',verification:'测试验证',reviewer:'Claude Code · 审核',delivery:'提交与开发 PR'};
      const subtitle=this.create('text',{x:57,y:49,class:'node-subtitle'});subtitle.textContent=roles[n.type]||n.type;
      const detail=this.create('text',{x:16,y:70,class:'node-detail'});
      const statuses={pending:'等待执行',running:'正在执行',passed:'已通过',completed:'已完成',failed:'失败',blocked:'已阻断',unknown:'未确认',cancelled:'已停止'};
      detail.textContent=this.readonly?`${statuses[n.status]||n.status} · ${n.counts?n.counts.tests+'项 / 失败'+n.counts.failures+' / Skip'+n.counts.skipped:'轮次 '+(n.round??'历史')}`:'双击配置 · 拖动排列';
      g.append(title,subtitle,detail);
      for(const[port,x,y]of this.readonly?[]:[['in',0,41],['out',210,41],...(n.type==='reviewer'?[['repair',105,82]]:[])]) {
        const handle=this.create('circle',{cx:x,cy:y,r:7,class:'port '+port,'data-port':port});
        const label=this.create('title');label.textContent=port==='in'?'输入':port==='repair'?'修复回到 Developer':'拖动连接到下一个节点';handle.append(label);g.append(handle);
      }
      if(!this.readonly&&n.type!=='delivery')g.append(this.button('在 '+n.label+' 后添加节点',
        {class:'node-add','data-canvas-action':'add','data-source':n.id},194,-12,'+'));
      this.svg.append(g);
    }
    this.updateView();
  }
  redrawEdges() {
    if(!this.edges)return;this.edges.replaceChildren();
    const ns=new Map(this.document.nodes.map(n=>[n.id,n]));
    this.document.edges.forEach((e,i)=>{
      const a=ns.get(e.source),b=ns.get(e.target);if(!a||!b)return;
      const d=this.path(a,b,e.on==='repair');
      const hit=this.create('path',{d,class:'edge-hit','data-edge':i});
      const path=this.create('path',{d,class:'edge '+e.on+(this.readonly?' status-'+(this.document.edge_states?.[i]||'pending'):'')+(this.edgeSelection===i?' selected':''),'data-edge':i,'marker-end':'url(#arrow-'+e.on+')'});
      const title=this.create('title');title.textContent=`${e.source} → ${e.target} · ${e.on}`;path.append(title);
      const group=this.create('g',{class:'connection'+(this.edgeSelection===i?' selected':'')});
      group.append(hit,path);this.edges.append(group);
      if(!this.readonly){
        const point=path.getPointAtLength(path.getTotalLength()/2),actions=this.create('g',{class:'edge-actions'});
        // Short legacy edges have no room between ports for a two-button menu.
        if(Math.abs(b.x-a.x-210)<80&&Math.abs(b.y-a.y)<82)point.y=Math.min(a.y,b.y)-32;
        actions.append(this.button('删除 '+e.source+' 到 '+e.target+' 的连线',
          {'data-canvas-action':'remove','data-edge-index':i},point.x+15,point.y,'×'));
        if(e.on==='next')actions.append(this.button('在连线中插入节点',
          {'data-canvas-action':'insert','data-source':e.source,'data-edge-index':i},point.x-15,point.y,'+'));
        group.append(actions);
      }
    });
    const selected=this.edges.querySelector('.connection.selected');
    if(selected)this.edges.append(selected); // Keep selected controls above crossing connections.
  }
  down(e) {
    if(e.button!==0&&e.button!==1||this.gesture)return;
    const action=e.target.closest('[data-canvas-action]');
    if(action&&e.button===0){e.preventDefault();this.action(action);return;}
    this.clickNode=null;this.svg.focus();const p=this.point(e),node=e.target.closest('[data-node]'),port=e.target.getAttribute('data-port');
    if(node&&e.button===0) {
      const n=this.document.nodes.find(n=>n.id===node.dataset.node);this.selection=n.id;this.edgeSelection=null;
      this.svg.querySelectorAll('.node').forEach(g=>g.classList.toggle('selected',g.dataset.node===n.id));
      if(this.readonly){this.callbacks.select(n.id);return;}
      // Pointer-down selects; double-click opens the inspector, never a drag.
      this.callbacks.select(n.id,true);
      if(port==='in')return;
      this.gesture=port?{type:'connect',node:n,port,start:p,pointer:e.pointerId}:
        {type:'node',node:n,element:node,start:p,x:n.x,y:n.y,pointer:e.pointerId};
    } else if(e.target.hasAttribute('data-edge')&&e.button===0) {
      this.edgeSelection=Number(e.target.getAttribute('data-edge'));this.redrawEdges();return;
    } else {
      this.edgeSelection=null;this.gesture={type:'pan',start:p,view:{...this.view},pointer:e.pointerId};
    }
    e.preventDefault();this.svg.setPointerCapture(e.pointerId);
  }
  move(e) {
    const g=this.gesture;if(!g||g.pointer!==e.pointerId)return;
    const p=this.point(e);
    if(g.type==='node') {
      g.node.x=Math.round(Math.max(0,Math.min(10000,g.x+p.x-g.start.x)));
      g.node.y=Math.round(Math.max(0,Math.min(10000,g.y+p.y-g.start.y)));
      g.element.setAttribute('transform',`translate(${g.node.x},${g.node.y})`);this.redrawEdges();
    } else if(g.type==='pan'){
      this.view.x+=g.start.x-p.x;this.view.y+=g.start.y-p.y;this.updateView();
    } else {
      this.preview?.remove();this.preview=this.create('path',{class:'connection-preview',d:this.path(g.node,{x:p.x,y:p.y-41},g.port==='repair')});
      this.svg.append(this.preview);
    }
  }
  release() {
    const g=this.gesture;this.gesture=null;this.preview?.remove();this.preview=null;
    if(g&&this.svg.hasPointerCapture(g.pointer))this.svg.releasePointerCapture(g.pointer);
    return g;
  }
  finish(e) {
    const g=this.gesture;if(!g||e.pointerId!==g.pointer)return;
    if(g.type==='connect') {
      const target=document.elementFromPoint(e.clientX,e.clientY)?.closest('[data-node]');
      const id=target?.dataset.node,point=this.point(e);this.release();
      if(id&&id!==g.node.id)this.callbacks.connect(g.node.id,id,g.port==='repair'?'repair':'next');
      else if(!id&&g.port!=='repair')this.callbacks.addAfter?.(g.node.id,null,{x:point.x+105,y:point.y});
      else this.callbacks.message('修复端口需要连接已有的 Developer 节点。');
    } else {
      this.release();
      if(g.type==='node'){
        if(g.node.x!==g.x||g.node.y!==g.y)this.callbacks.change();
        else {this.clickNode=g.node.id;this.callbacks.select(g.node.id,true);}
      }
    }
  }
  cancel() {
    const g=this.release();if(!g)return;
    if(g.type==='node'){
      g.node.x=g.x;g.node.y=g.y;g.element.setAttribute('transform',`translate(${g.x},${g.y})`);this.redrawEdges();
    }else if(g.type==='pan'){this.view=g.view;this.updateView();}
  }
}
