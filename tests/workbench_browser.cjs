/* Real HTTP/Chromium with delayed real responses. Snapshots are synthetic fixtures. */
const fs=require('fs'),assert=require('assert/strict');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const out=process.argv[2],access=JSON.parse(fs.readFileSync(out+'/access.json'));
const results=[];let browser;
const delay=ms=>new Promise(r=>setTimeout(r,ms));
async function until(fn){for(let i=0;i<100;i++){if(await fn())return;await delay(40)}throw Error('Condition did not become true');}
async function test(name,fn){const context=await browser.newContext({viewport:{width:952,height:756}}),page=await context.newPage();page.setDefaultTimeout(8000);const errors=[];page.on('pageerror',e=>errors.push(String(e)));try{await page.goto(access.url+'/#'+access.token);await page.getByRole('button',{name:'打开文件夹',exact:true}).waitFor();await fn(page);assert.deepEqual(errors,[]);results.push({name,passed:true});}catch(e){results.push({name,passed:false,error:String(e)});await page.screenshot({path:out+'/'+name+'-failure.png'});}finally{await page.unrouteAll({behavior:'ignoreErrors'});await context.close();fs.writeFileSync(out+'/workbench-results.json',JSON.stringify({evidence_type:'synthetic native data, ordinary Chromium/real HTTP',tests:results.length,failures:results.filter(r=>!r.passed).length,skipped:0,results},null,2));}}
async function openWorkspace(p){await p.getByRole('button',{name:'打开文件夹',exact:true}).click();await p.getByRole('heading',{name:'打开文件夹',exact:true}).waitFor();await p.getByRole('button',{name:'选择此文件夹',exact:true}).click();await p.getByRole('heading',{name:'打开文件夹',exact:true}).waitFor({state:'hidden'});await until(async()=>!(await p.getByRole('button',{name:'开始运行',exact:true}).isDisabled()));}
async function example(p,index){await p.getByRole('button',{name:'示例',exact:true}).click();await p.locator('.example-library>button').nth(index).click();}
async function nativeSessions(p){
 await openWorkspace(p);await p.getByLabel('会话分组方式',{exact:true}).selectOption('workflow');
 await p.locator('.session-group-title').first().waitFor();
 for(const label of ['dialog-B','dialog-A'])await p.locator('.session-main').filter({hasText:'Synthetic '+label}).click();
 await p.getByRole('button',{name:'原生终端',exact:true}).click();
 await until(async()=>await p.getByRole('button',{name:'打开同一原生会话',exact:true}).isEnabled());
 const mutations=[];
 // These races need real prepare replies, never a native fixture launched as a model.
 await p.route(/\/api\/terminal\/(start|input|resize|close)$/,route=>{mutations.push(route.request().url());return route.abort()});
 return {mutations,tab:label=>p.locator('.editor-tabs').getByRole('button',{name:'Synthetic '+label,exact:true})};
}
async function heldPrepare(p,handle,invalid=false){
 let release,reply,delivered=false;const held=new Promise(r=>release=r);
 const handler=async route=>{
  const data=route.request().postDataJSON();if(data.handle!==handle)return route.fallback();
  // For the error case, ask the real server to reject an unknown identity.
  const response=await route.fetch(invalid?{postData:JSON.stringify({...data,handle:'unknown-native-terminal-handle'})}:{});
  reply={status:response.status(),body:await response.json(),request:data};await held;
  await route.fulfill({response});delivered=true;
 };
 await p.route('**/api/terminal/prepare',handler);
 return {release,seen:async()=>{await until(()=>reply!==undefined);return reply},finish:async()=>{release();await until(()=>delivered)}};
}
(async()=>{browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM,args:['--no-sandbox']});
await test('directory-cancel-and-origin-auth',async p=>{assert(!p.url().includes('#'));assert(await p.locator('.brand').getByText('DEVELOPMENT',{exact:true}).isVisible(),'Development identity must remain visible at ordinary viewport widths');const denied=await p.request.get(access.url+'/api/status');assert.equal(denied.status(),403);await p.getByRole('button',{name:'打开文件夹',exact:true}).click();await p.getByRole('heading',{name:'打开文件夹',exact:true}).waitFor();await p.getByRole('button',{name:'取消',exact:true}).click();assert(await p.getByText('尚未打开工作区',{exact:false}).isVisible());await openWorkspace(p);assert((await p.locator('.workspace-name').innerText()).includes(access.path));await p.reload();await until(async()=>(await p.locator('.workspace-name').innerText()).includes(access.path));assert.equal((await p.context().cookies()).filter(c=>c.name==='devflower_workbench').length,0);});
await test('node-panel-prompts-drag-and-save-reopen',async p=>{await openWorkspace(p);await p.locator('.react-flow__node[data-id="analyze"]').click();await p.getByLabel('模块名称',{exact:true}).fill('浏览器配置节点');await p.getByLabel('工作方式',{exact:true}).selectOption('Plan');await p.getByRole('button',{name:'提示词',exact:true}).click();await p.getByLabel('本次运行初始化提示词',{exact:true}).fill('INIT-UI');await p.getByLabel('每轮提示词',{exact:true}).fill('ROUND-UI');await p.getByLabel('输出与交接要求',{exact:true}).fill('OUTPUT-UI');await p.getByRole('button',{name:'关闭节点配置',exact:true}).click();const node=p.locator('.react-flow__node[data-id="analyze"]'),before=await node.boundingBox();await p.mouse.move(before.x+40,before.y+20);await p.mouse.down();await p.mouse.move(before.x+90,before.y+60,{steps:8});await p.mouse.up();assert.equal(await p.locator('.inspector').count(),0);await p.getByRole('button',{name:'保存',exact:true}).click();await until(async()=>(await p.locator('.notice').innerText()).includes('当前改动已保存'));await p.reload();await p.locator('.react-flow__node[data-id="analyze"]').click();await p.getByRole('button',{name:'提示词',exact:true}).click();assert.equal(await p.getByLabel('本次运行初始化提示词',{exact:true}).inputValue(),'INIT-UI');assert.equal(await p.getByLabel('每轮提示词',{exact:true}).inputValue(),'ROUND-UI');await p.screenshot({path:out+'/configured-canvas.png'});});
await test('delayed-save-cannot-adopt-new-document',async p=>{await openWorkspace(p);await p.getByLabel('工作流名称',{exact:true}).fill('文档 A');let release,arrived;const held=new Promise(r=>release=r),seen=new Promise(r=>arrived=r);let first=true;const sent=[];p.on('request',r=>{if(r.url().endsWith('/api/draft'))sent.push(r.postDataJSON());});await p.route('**/api/draft',async route=>{const response=await route.fetch();if(first){first=false;arrived();await held;}await route.fulfill({response});});await p.getByRole('button',{name:'保存',exact:true}).click();await seen;await example(p,1);await p.getByLabel('工作流名称',{exact:true}).fill('文档 B');release();await until(async()=>await p.getByRole('button',{name:'保存',exact:true}).isEnabled());await p.getByRole('button',{name:'保存',exact:true}).click();await until(()=>Promise.resolve(sent.length===2));await until(async()=>(await p.locator('.notice').innerText()).includes('当前改动已保存'));assert(sent[1].id==null,'New document must omit the old save identity');assert.equal(sent[1].graph.name,'文档 B');assert.equal(await p.getByLabel('工作流名称',{exact:true}).inputValue(),'文档 B');});
await test('reordered-run-and-network-failure-are-honest',async p=>{await openWorkspace(p);let release,arrived;const hold=new Promise(r=>release=r),seen=new Promise(r=>arrived=r);let first=true;await p.route('**/api/run?**',async route=>{const response=await route.fetch();if(first&&route.request().url().includes('run=A')){first=false;arrived();await hold;}await route.fulfill({response});});await p.getByLabel('历史运行',{exact:true}).selectOption('A');await seen;await p.getByLabel('历史运行',{exact:true}).selectOption('B');await until(async()=>await p.locator('.react-flow__node[data-id="analyze"]').getByText('分析 B',{exact:true}).count()===1);release();await delay(180);assert.equal(await p.getByLabel('工作流名称',{exact:true}).inputValue(),'运行 B');assert.equal(await p.getByLabel('本次任务',{exact:true}).inputValue(),'任务 B');await p.unroute('**/api/run?**');await p.route('**/api/run?**',route=>route.abort());await until(async()=>(await p.locator('.activity-tabs').innerText()).includes('状态未确认'));assert(!(await p.locator('.activity-tabs').innerText()).includes('已完成'));});
await test('loop-permission-preview-includes-nested-agents',async p=>{await openWorkspace(p);await example(p,2);await p.getByLabel('本次任务',{exact:true}).fill('Preview only; never starts a native model');await p.getByRole('button',{name:'开始运行',exact:true}).click();await p.getByRole('heading',{name:'确认这次工作流',exact:true}).waitFor();const text=await p.locator('.authorization').innerText();assert(text.includes('提出或修订方案：Ask / read'));assert(text.includes('独立检查方案：Ask / read'));assert(text.includes('high'));await p.getByRole('button',{name:'取消运行预览',exact:true}).click();});
await test('frozen-budget-does-not-display-or-edit-draft',async p=>{await openWorkspace(p);await p.locator('.react-flow__node[data-id="analyze"]').click();await p.getByRole('button',{name:'高级',exact:true}).click();await p.getByLabel('运行调用预算',{exact:true}).fill('24');await p.getByLabel('运行时间预算（秒）',{exact:true}).fill('1200');await p.getByLabel('历史运行',{exact:true}).selectOption('A');await until(async()=>await p.getByLabel('工作流名称',{exact:true}).inputValue()==='运行 A');await p.locator('.react-flow__node[data-id="analyze"]').click();await p.getByRole('button',{name:'高级',exact:true}).click();assert.equal(await p.getByLabel('运行调用预算',{exact:true}).inputValue(),'10');assert.equal(await p.getByLabel('运行时间预算（秒）',{exact:true}).inputValue(),'600');assert(await p.getByLabel('运行调用预算',{exact:true}).isDisabled());assert(await p.getByLabel('运行时间预算（秒）',{exact:true}).isDisabled());await p.getByLabel('历史运行',{exact:true}).selectOption('B');await until(async()=>await p.getByLabel('工作流名称',{exact:true}).inputValue()==='运行 B');await p.locator('.react-flow__node[data-id="analyze"]').click();await p.getByRole('button',{name:'高级',exact:true}).click();assert.equal(await p.getByLabel('运行调用预算',{exact:true}).inputValue(),'12');await p.getByRole('button',{name:'编辑草稿',exact:true}).click();await p.locator('.react-flow__node[data-id="analyze"]').click();await p.getByRole('button',{name:'高级',exact:true}).click();assert.equal(await p.getByLabel('运行调用预算',{exact:true}).inputValue(),'24');assert.equal(await p.getByLabel('运行时间预算（秒）',{exact:true}).inputValue(),'1200');assert(await p.getByLabel('运行调用预算',{exact:true}).isEnabled());});
await test('slow-poll-eventually-displays-real-snapshot',async p=>{await openWorkspace(p);let responses=0;await p.route('**/api/run?**',async route=>{const response=await route.fetch();await delay(1400);responses++;await route.fulfill({response});});await p.getByLabel('历史运行',{exact:true}).selectOption('A');await delay(4600);const title=await p.getByLabel('工作流名称',{exact:true}).inputValue();assert(responses>=2,'Actual HTTP replies must have returned');assert.equal(title,'运行 A','Slow valid responses must eventually update the selected run');});
await test('hung-snapshot-becomes-unknown-without-restarting-run',async p=>{await openWorkspace(p);let release;const hold=new Promise(r=>release=r);let held=0;await p.route('**/api/run?**',async route=>{const response=await route.fetch();held++;await hold;await route.fulfill({response});});try{await p.getByLabel('历史运行',{exact:true}).selectOption('A');await until(async()=>held===1);await delay(3000);assert.equal(held,1,'An outstanding snapshot must not overlap before its deadline');await delay(2600);assert((await p.locator('.activity-tabs').innerText()).includes('状态未确认'));assert(held<=2,'Only a timed-out read may be retried');}finally{release();}});
await test('canvas-nodes-stay-visible-during-unrelated-edits',async p=>{
 await openWorkspace(p);
 const nodes=p.locator('.react-flow__node');await until(async()=>await nodes.count()>0&&(await nodes.evaluateAll(es=>es.every(e=>getComputedStyle(e).visibility==='visible'))));
 await p.evaluate(()=>{const visible=[...document.querySelectorAll('.react-flow__node')];window.canvasVisibilityLoss=[];window.canvasVisibilityObserver=new MutationObserver(records=>{for(const m of records){if(m.attributeName==='style'&&(m.oldValue?.includes('visibility: hidden')||m.target.style.visibility==='hidden'))window.canvasVisibilityLoss.push(m.target.dataset.id);}});for(const e of visible)window.canvasVisibilityObserver.observe(e,{attributes:true,attributeFilter:['style'],attributeOldValue:true});});
 for(let i=0;i<5;i++){await p.getByLabel('本次任务',{exact:true}).fill('Ordinary task edit '+i);await delay(90);}
 assert.deepEqual(await p.evaluate(()=>window.canvasVisibilityLoss),[],'Visible canvas modules must retain their measured size during unrelated task editing');
 assert(await nodes.evaluateAll(es=>es.every(e=>getComputedStyle(e).visibility==='visible')),'Every module must remain available to click and drag');
 await p.locator('.react-flow__node[data-id="analyze"]').click();await p.getByLabel('模块名称',{exact:true}).waitFor();
 await p.getByRole('button',{name:'关闭节点配置',exact:true}).click();
 const node=p.locator('.react-flow__node[data-id="analyze"]'),before=await node.boundingBox();
 await p.mouse.move(before.x+40,before.y+20);await p.mouse.down();await p.mouse.move(before.x+90,before.y+60,{steps:8});await p.mouse.up();
 await until(async()=>{const after=await node.boundingBox();return after&&Math.hypot(after.x-before.x,after.y-before.y)>10});
 assert.deepEqual(await p.evaluate(()=>window.canvasVisibilityLoss),[],'Clicking and dragging must also preserve measured dimensions');
 await p.evaluate(()=>window.canvasVisibilityObserver.disconnect());
});
await test('canvas-measurements-stay-out-of-drafts-and-isolate-views',async p=>{
 await openWorkspace(p);
 const visible=async()=>until(async()=>await p.locator('.react-flow__node').count()>0&&await p.locator('.react-flow__node').evaluateAll(es=>es.every(e=>getComputedStyle(e).visibility==='visible')));
 const graphOnly=async()=>p.evaluate(()=>JSON.parse(localStorage.getItem('devflower-workbench-view')).graph);
 const cleanGraph=g=>{for(const n of g.nodes){for(const key of ['measured','width','height','dimensions'])assert(!(key in n),'UI measurement leaked into canonical node: '+key);if(n.body)cleanGraph(n.body)}};
 await visible();let savedRequest;
 p.on('request',r=>{if(r.url().endsWith('/api/draft'))savedRequest=r.postDataJSON()});
 await p.getByRole('button',{name:'保存',exact:true}).click();await until(async()=>(await p.locator('.notice').innerText()).includes('当前改动已保存'));await visible();
 const initial=await graphOnly();cleanGraph(initial);cleanGraph(savedRequest.graph);
 assert.equal(await p.locator('.dirty').innerText(),'已保存');
 for(const id of ['A','B']){
  await p.getByLabel('历史运行',{exact:true}).selectOption(id);await until(async()=>await p.getByLabel('工作流名称',{exact:true}).inputValue()==='运行 '+id);await visible();
  await p.getByRole('checkbox',{name:'减少动态效果'}).check();await p.getByRole('checkbox',{name:'减少动态效果'}).uncheck();await visible();
  assert.equal(await p.locator('.dirty').innerText(),'已保存');assert.deepEqual(await graphOnly(),initial);
  assert((await p.locator('.activity-tabs').innerText()).includes('已完成'),'UI measurement must not change runtime status');
 }
 await p.getByRole('button',{name:'编辑草稿',exact:true}).click();await visible();assert.deepEqual(await graphOnly(),initial);
 await example(p,2);await visible();const loop=p.locator('.react-flow__node').filter({has:p.getByRole('button',{name:'编辑循环内流程',exact:true})});
 await loop.getByRole('button',{name:'编辑循环内流程',exact:true}).click();await visible();
 const nested=await graphOnly();cleanGraph(nested);
 await p.getByLabel('本次任务',{exact:true}).fill('Nested canvas measurement check');await visible();assert.deepEqual(await graphOnly(),nested);
 await p.getByRole('button',{name:'返回外层',exact:true}).click();await visible();
 // A new document reuses the example IDs but must mount a fresh canvas.
 await example(p,0);await visible();await p.getByLabel('本次任务',{exact:true}).fill('Replacement document measurement check');await visible();cleanGraph(await graphOnly());
});
await test('structured-dialog-visible-reload-switch-and-no-duplicates',async p=>{
 await openWorkspace(p);
 const open=async label=>{await p.locator('.session-main').filter({hasText:'Synthetic '+label}).click();await until(async()=>await p.locator('.conversation-toolbar>strong').innerText()==='Synthetic '+label);};
 const answers=p.locator('.execution-result');
 const check=async label=>{await until(async()=>await answers.count()===2&&(await answers.first().innerText()).includes('SYNTHETIC '+label+' final answer 1'));const text=await answers.allTextContents();assert(text[0].includes('结构化执行结果'));assert(text[0].includes('loop/analyze'));assert(text[0].includes('1 / 1'));assert(text[1].includes('1 / 2'));assert(text[0].includes(label+'-run'));assert(!text.join('').includes('HIDDEN_RESULT_REASONING'));assert.equal(await p.locator('.message.assistant').filter({hasText:'final answer'}).count(),0);};
 await open('dialog-A');await check('dialog-A');
 assert.equal(await p.locator('.request-group[open]').count(),0,'Advanced payloads stay folded');
 await p.getByRole('button',{name:'刷新历史',exact:true}).click();await check('dialog-A');
 await p.reload();await check('dialog-A');assert.equal(await p.locator('.conversation-toolbar>strong').innerText(),'Synthetic dialog-A');
 await open('dialog-B');await check('dialog-B');await open('dialog-A');await check('dialog-A');
 await p.getByRole('button',{name:'刷新历史',exact:true}).click();await check('dialog-A');
 await p.screenshot({path:out+'/structured-dialog.png'});
 await open('dialog-native');await until(async()=>await p.locator('.message.assistant').filter({hasText:'SYNTHETIC dialog-native final answer'}).count()===2);assert.equal(await answers.count(),0);
 await open('dialog-failed');await until(async()=>await p.locator('.message.assistant').filter({hasText:'No response requested.'}).count()===2);assert.equal(await answers.count(),0);
});
await test('delayed-session-history-isolated-and-http-search-truthful',async p=>{
 await openWorkspace(p);let release,arrived;const hold=new Promise(r=>release=r),seen=new Promise(r=>arrived=r);let first=true;
 await p.route('**/api/history?**',async route=>{const response=await route.fetch();if(first&&route.request().url().includes(access.sessions['dialog-A'].handle)){first=false;arrived();await hold;}await route.fulfill({response});});
 await p.locator('.session-main').filter({hasText:'Synthetic dialog-A'}).click();await seen;
 await p.locator('.session-main').filter({hasText:'Synthetic dialog-B'}).click();await until(async()=>(await p.locator('.execution-result').allTextContents()).join('').includes('SYNTHETIC dialog-B final answer 2'));release();await delay(150);
 const text=await p.locator('.execution-result').allTextContents();assert.equal(text.length,2);assert(!text.join('').includes('dialog-A'));
 const response=await p.request.get(access.url+'/api/history?'+new URLSearchParams({workspace:access.workspace,handle:access.sessions['dialog-B'].handle,query:'final answer 2'}),{headers:{Authorization:'Bearer '+access.token}});assert.equal(response.status(),200);const history=await response.json();assert.deepEqual(history.execution_results.map(r=>r.text),['SYNTHETIC dialog-B final answer 2']);assert.equal(history.messages.length,0);
});
await test('non-loop-results-use-first-human-round',async p=>{
 await openWorkspace(p);
 await p.locator('.session-main').filter({hasText:'Synthetic dialog-plain'}).click();
 const rows=p.locator('.execution-result');await until(async()=>await rows.count()===1);
 const text=await rows.first().innerText();
 assert(/轮次\s+1\s+·/.test(text),'Non-loop completed results must show human round 1, matching the actual-input group');
 assert(!/轮次\s+0\s+·/.test(text),'Internal zero must not be shown as a human round');
 assert((await p.locator('.request-group').first().innerText()).includes('第 1 轮'));
 await p.locator('.session-main').filter({hasText:'Synthetic dialog-A'}).click();
 await until(async()=>await rows.count()===2);
 assert(/轮次\s+1\s*\/\s*1/.test(await rows.first().innerText()),'Nested loop path must retain its actual 1 / 1 round');
});
await test('product-editor-copy-delete-undo-and-multiselect',async p=>{
 await openWorkspace(p);const graph=()=>p.evaluate(()=>JSON.parse(localStorage.getItem('devflower-workbench-view')).graph);
 const initial=await graph();await p.locator('.react-flow__pane').click({position:{x:25,y:300}});
 await p.keyboard.press('Control+a');await until(async()=>!(await p.getByRole('button',{name:'复制选中节点',exact:true}).isDisabled()));
 await p.getByRole('button',{name:'复制选中节点',exact:true}).click();await p.getByRole('button',{name:'粘贴节点',exact:true}).click();
 await until(async()=>(await graph()).nodes.length===initial.nodes.length*2-1);
 const pasted=await graph();assert.equal(pasted.nodes.filter(n=>n.kind==='start').length,1);
 for(const n of pasted.nodes.filter(n=>!initial.nodes.some(x=>x.id===n.id)&&n.kind==='agent'))assert.equal(n.session,'new');
 await p.getByRole('button',{name:'删除选中节点',exact:true}).click();await until(async()=>(await graph()).nodes.length===initial.nodes.length);
 await p.getByRole('button',{name:'撤销',exact:true}).click();await until(async()=>(await graph()).nodes.length===pasted.nodes.length);
 await p.getByRole('button',{name:'重做',exact:true}).click();await until(async()=>(await graph()).nodes.length===initial.nodes.length);
 await p.getByRole('button',{name:'撤销',exact:true}).click();await p.keyboard.press('Control+a');await p.getByRole('button',{name:'对齐与分布',exact:true}).click();await p.getByRole('menuitem',{name:'顶部对齐',exact:true}).click();
 assert.equal(new Set((await graph()).nodes.map(n=>n.position.y)).size,1);
 await p.getByRole('button',{name:'缩略导航',exact:true}).click();assert.equal(await p.locator('.react-flow__minimap').count(),0);
 await p.getByRole('button',{name:'缩略导航',exact:true}).click();assert.equal(await p.locator('.react-flow__minimap').count(),1);
 await p.screenshot({path:out+'/product-editor.png'});
});
await test('product-edge-label-insertion-and-frozen-configuration',async p=>{
 await openWorkspace(p);const graph=()=>p.evaluate(()=>JSON.parse(localStorage.getItem('devflower-workbench-view')).graph);const initial=await graph();
 await p.locator('.react-flow__edge-interaction').first().click({force:true});await p.getByLabel('连线标签',{exact:true}).fill('显式交接');
 await p.getByLabel('传递内容',{exact:true}).selectOption('field');await p.getByLabel('字段',{exact:true}).fill('result.score');
 await p.getByLabel('条件',{exact:true}).selectOption('true');await p.getByLabel('上下文字符预算',{exact:true}).fill('2048');
 await until(async()=>{const e=(await graph()).edges[0];return e.label==='显式交接'&&e.transfer==='field'&&e.field==='result.score'&&e.when==='true'&&e.max_chars===2048});
 const beforeInsert=await graph(),original=beforeInsert.edges[0];
 await p.getByRole('button',{name:'在连线上插入 Agent',exact:true}).click();await until(async()=>(await graph()).nodes.length===initial.nodes.length+1);
 const inserted=await graph();assert.equal(inserted.edges.length,beforeInsert.edges.length+1);
 const addedNodes=inserted.nodes.filter(n=>!beforeInsert.nodes.some(old=>old.id===n.id));assert.equal(addedNodes.length,1);
 const agent=addedNodes[0];assert.equal(agent.kind,'agent');assert.equal(agent.session,'new');assert(!agent.context_from);assert(!agent.session_id);
 const addedEdges=inserted.edges.filter(e=>!beforeInsert.edges.some(old=>old.id===e.id));assert.equal(addedEdges.length,1);
 assert.deepEqual(addedEdges[0],{id:addedEdges[0].id,source:agent.id,target:original.target,transfer:'result',when:'always'});
 const expected=JSON.parse(JSON.stringify(beforeInsert));expected.nodes.push(agent);expected.edges.find(e=>e.id===original.id).target=agent.id;expected.edges.push(addedEdges[0]);
 assert.deepEqual(inserted,expected,'Insertion must preserve the rest of the graph, including the original edge label and handoff configuration');
 await p.getByRole('button',{name:'撤销',exact:true}).click();await until(async()=>(await graph()).nodes.length===beforeInsert.nodes.length);
 assert.deepEqual(await graph(),beforeInsert,'One Undo must restore the complete original graph without an isolated Agent');
 assert.equal(await p.locator(`.react-flow__node[data-id="${agent.id}"]`).count(),0);
 await p.getByRole('button',{name:'重做',exact:true}).click();await until(async()=>(await graph()).nodes.length===inserted.nodes.length);
 assert.deepEqual(await graph(),inserted,'One Redo must restore the same Agent identity, topology and handoff configuration');
 await p.locator(`.react-flow__node[data-id="${agent.id}"]`).waitFor();
 const saved=p.waitForResponse(r=>r.url()===access.url+'/api/draft'&&r.request().method()==='POST');
 await p.getByRole('button',{name:'保存',exact:true}).click();const response=await saved;assert(response.ok());
 assert.deepEqual(response.request().postDataJSON().graph,inserted,'The real HTTP save must contain the complete redone graph');
 await p.getByLabel('历史运行',{exact:true}).selectOption('A');await until(async()=>await p.getByLabel('工作流名称',{exact:true}).inputValue()==='运行 A');
 await p.locator('.react-flow__node[data-id="analyze"]').click();assert(await p.getByLabel('模块名称',{exact:true}).isDisabled());
 await p.getByRole('button',{name:'提示词',exact:true}).click();assert(await p.getByLabel('每轮提示词',{exact:true}).isDisabled());
});
await test('product-workflow-grouping-and-readable-public-dialog',async p=>{
 await openWorkspace(p);await p.getByLabel('会话分组方式',{exact:true}).selectOption('workflow');
 await until(async()=>(await p.locator('.session-group-title').allTextContents()).length>0);
 await p.locator('.session-main').filter({hasText:'Synthetic dialog-A'}).click();await until(async()=>await p.locator('.execution-result').count()===2);
 assert.equal(await p.locator('.request-group[open]').count(),0);
 await p.getByRole('button',{name:'原生终端',exact:true}).click();await p.getByRole('button',{name:'打开同一原生会话',exact:true}).waitFor();
 let starts=0;p.on('request',r=>{if(r.url().endsWith('/api/terminal/start'))starts++});await p.reload();await p.getByRole('button',{name:'原生终端',exact:true}).click();await p.getByRole('button',{name:'打开同一原生会话',exact:true}).waitFor();assert.equal(starts,0,'Reload must never implicitly start a native writer');
});
for(const invalid of [false,true])await test('native-delayed-prepare-'+(invalid?'error':'success')+'-cannot-cross-session',async p=>{
 const {mutations,tab}=await nativeSessions(p),a=await heldPrepare(p,access.sessions['dialog-A'].handle,invalid),b=await heldPrepare(p,access.sessions['dialog-B'].handle);
 const open=p.getByRole('button',{name:'打开同一原生会话',exact:true});const prepares=[];
 p.on('request',r=>{if(r.url().endsWith('/api/terminal/prepare'))prepares.push(r.postDataJSON())});
 try{
  await open.click();const old=await a.seen();assert.equal(old.status,invalid?400:200);if(!invalid)assert.equal(old.body.data.handle,access.sessions['dialog-A'].handle);
  await tab('dialog-B').click();await until(async()=>await open.isEnabled());
  assert.equal(await p.locator('.native-terminal>header b').innerText(),'Synthetic dialog-B');
  await open.click();const fresh=await b.seen();assert.equal(fresh.status,200);assert.equal(fresh.body.data.handle,access.sessions['dialog-B'].handle);
  await a.finish();await delay(120);
  assert.equal(await p.locator('.terminal-confirm').count(),0,'A must never offer its authorization under B');
  assert.equal(await p.locator('.native-terminal [role=alert]').count(),0,'A must not publish its error under B');
  assert(await open.isDisabled(),'A must not clear B pending request state');
  assert.equal(await p.getByLabel('原生CLI终端',{exact:true}).getAttribute('data-connected'),'false');
  await b.finish();await p.locator('.terminal-confirm').waitFor();
  await until(async()=>await p.getByRole('button',{name:'确认打开原生终端',exact:true}).isEnabled());
  await tab('dialog-A').click();await until(async()=>await open.isEnabled());assert.equal(await p.locator('.terminal-confirm').count(),0,'Switching must discard a visible preview');
  await tab('dialog-B').click();await until(async()=>await open.isEnabled());assert.equal(await p.locator('.terminal-confirm').count(),0,'Returning to B must not revive its preview');
  await open.click();await p.locator('.terminal-confirm').waitFor();await until(async()=>await p.getByRole('button',{name:'确认打开原生终端',exact:true}).isEnabled());
  await p.getByRole('button',{name:'重新连接终端',exact:true}).click();await until(async()=>await open.isEnabled());
  assert.equal(await p.locator('.terminal-confirm').count(),0,'Reconnect must discard the prior authorization even for the same session');
  await tab('dialog-A').click();await until(async()=>await open.isEnabled());assert.equal(await p.locator('.terminal-confirm').count(),0);
  assert.deepEqual(prepares.map(r=>r.handle),[access.sessions['dialog-A'].handle,access.sessions['dialog-B'].handle,access.sessions['dialog-B'].handle],'Only explicit opens may prepare; switching/reconnecting must not replay');
  assert.deepEqual(mutations,[],'Switching/reconnecting must never start, write, resize or close a different PTY');
 }finally{a.release();b.release()}
});
await test('native-unmount-discards-delayed-prepare-for-same-session',async p=>{
 const {mutations,tab}=await nativeSessions(p),a=await heldPrepare(p,access.sessions['dialog-A'].handle);
 const open=p.getByRole('button',{name:'打开同一原生会话',exact:true});let prepares=0;
 p.on('request',r=>{if(r.url().endsWith('/api/terminal/prepare'))prepares++});
 try{
  await open.click();assert.equal((await a.seen()).status,200);
  await p.getByRole('button',{name:'对话视图',exact:true}).click();assert.equal(await p.locator('.native-terminal').count(),0);
  await p.getByRole('button',{name:'原生终端',exact:true}).click();await until(async()=>await open.isEnabled());
  await a.finish();await delay(120);assert.equal(await p.locator('.terminal-confirm').count(),0);
  await tab('dialog-B').click();await until(async()=>await open.isEnabled());await tab('dialog-A').click();await until(async()=>await open.isEnabled());
  assert.equal(await p.locator('.terminal-confirm').count(),0);assert.equal(prepares,1);assert.deepEqual(mutations,[]);
 }finally{a.release()}
});
await test('recovery-entry-refuses-missing-completion-without-replay',async p=>{
 await openWorkspace(p);let starts=0;p.on('request',r=>{if(r.url().endsWith('/api/start'))starts++});
 await p.getByLabel('历史运行',{exact:true}).selectOption(access.lost_run);
 await p.getByRole('button',{name:'核验并恢复',exact:true}).waitFor();await p.getByRole('button',{name:'核验并恢复',exact:true}).click();
 await until(async()=>(await p.locator('.alert').innerText()).includes('缺少可靠原生完成回执'));
 assert.equal(starts,0);assert((await p.locator('.activity-tabs').innerText()).includes('状态未确认'));
});
await test('existing-chat-keeps-native-profile-and-terminal-hides-second-composer',async p=>{
 await openWorkspace(p);await p.locator('.session-main').filter({hasText:'Synthetic dialog-native'}).click();
 await p.getByLabel('此会话执行配置',{exact:true}).waitFor();assert((await p.getByLabel('此会话执行配置',{exact:true}).innerText()).includes('codex'));
 assert.equal(await p.getByLabel('对话执行配置',{exact:true}).count(),0);
 await p.getByRole('button',{name:'原生终端',exact:true}).click();await p.getByRole('button',{name:'打开同一原生会话',exact:true}).waitFor();assert.equal(await p.locator('.chat-composer').count(),0);
});
await browser.close();console.log(JSON.stringify({tests:results.length,failures:results.filter(r=>!r.passed).length,skipped:0}));process.exitCode=results.some(r=>!r.passed)?1:0;
})().catch(e=>{console.error(String(e));process.exitCode=1;browser?.close();});
