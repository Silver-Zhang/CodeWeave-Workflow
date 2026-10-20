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
    svg.addEventListener('wheel',e=>{e.preventDefault();this.zoom(e.deltaY<0?1.15:1/1.15,e);},{passive:false});
    svg.addEventListener('keydown',e=>{
      if(e.key==='Escape'){this.cancel();this.edgeSelection=null;this.render(this.document,this.selection);}
      if(['Delete','Backspace'].includes(e.key)){e.preventDefault();this.callbacks.remove(this.edgeSelection);}
    });
    this.updateView();
  }
  create(tag,attrs={}) {
    const e=document.createElementNS('http://www.w3.org/2000/svg',tag);
    for(const[k,v]of Object.entries(attrs))e.setAttribute(k,v);
    return e;
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
      const w=Math.max(...ns.map(n=>n.x+210))-x+75,h=Math.max(...ns.map(n=>n.y+82))-y+110;
      this.view={x,y,w:Math.max(w,h*1100/620,350),h:Math.max(h,w*620/1100,197)};
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
    this.document=doc;this.selection=selection;this.svg.replaceChildren();
    const defs=this.create('defs');
    for(const name of ['next','repair']){
      const marker=this.create('marker',{id:'arrow-'+name,viewBox:'0 0 10 10',refX:9,refY:5,markerWidth:7,markerHeight:7,orient:'auto-start-reverse'});
      marker.append(this.create('path',{d:'M 0 0 L 10 5 L 0 10 z',class:name}));defs.append(marker);
    }
    this.svg.append(defs);this.edges=this.create('g',{class:'connections'});this.svg.append(this.edges);
    this.redrawEdges();
    for(const n of doc.nodes) {
      const g=this.create('g',{'data-node':n.id,class:'node '+n.type+(n.id===selection?' selected':''),transform:`translate(${n.x},${n.y})`});
      g.append(this.create('rect',{width:210,height:82,rx:12}));
      const title=this.create('text',{x:18,y:32});title.textContent=n.label.slice(0,24);
      const subtitle=this.create('text',{x:18,y:57,class:'node-subtitle'});subtitle.textContent=n.type;
      g.append(title,subtitle);
      for(const[port,x,y]of [['in',0,41],['out',210,41],...(n.type==='reviewer'?[['repair',105,82]]:[])]) {
        const handle=this.create('circle',{cx:x,cy:y,r:7,class:'port '+port,'data-port':port});
        const label=this.create('title');label.textContent=port==='in'?'输入':port==='repair'?'修复回到 Developer':'拖动连接到下一个节点';handle.append(label);g.append(handle);
      }
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
      const path=this.create('path',{d,class:'edge '+e.on+(this.edgeSelection===i?' selected':''),'data-edge':i,'marker-end':'url(#arrow-'+e.on+')'});
      const title=this.create('title');title.textContent=`${e.source} → ${e.target} · ${e.on}`;path.append(title);
      this.edges.append(hit,path);
    });
  }
  down(e) {
    if(e.button!==0&&e.button!==1||this.gesture)return;
    this.svg.focus();const p=this.point(e),node=e.target.closest('[data-node]'),port=e.target.getAttribute('data-port');
    if(node&&e.button===0) {
      const n=this.document.nodes.find(n=>n.id===node.dataset.node);this.selection=n.id;this.edgeSelection=null;
      this.svg.querySelectorAll('.node').forEach(g=>g.classList.toggle('selected',g.dataset.node===n.id));
      this.callbacks.select(n.id);
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
      const id=target?.dataset.node;this.release();
      if(id&&id!==g.node.id)this.callbacks.connect(g.node.id,id,g.port==='repair'?'repair':'next');
      else this.callbacks.message('将输出端口拖到另一个节点。修复端口仅连接 Developer。');
    } else {
      this.release();
      if(g.type==='node'&&(g.node.x!==g.x||g.node.y!==g.y))this.callbacks.change();
    }
  }
  cancel() {
    const g=this.release();if(!g)return;
    if(g.type==='node'){
      g.node.x=g.x;g.node.y=g.y;g.element.setAttribute('transform',`translate(${g.x},${g.y})`);this.redrawEdges();
    }else if(g.type==='pan'){this.view=g.view;this.updateView();}
  }
}
