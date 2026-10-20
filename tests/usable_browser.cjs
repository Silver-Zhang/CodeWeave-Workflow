const fs=require('fs'), path=require('path');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const output=process.argv[2], access=JSON.parse(fs.readFileSync(path.join(output,'access.json')));
let browser, page;
const results=[];
const wait=ms=>new Promise(r=>setTimeout(r,ms));
async function check(name,fn){try{await fn();results.push({name,passed:true});console.log('PASS '+name);}catch(error){results.push({name,passed:false,error:String(error)});console.log('FAIL '+name+': '+error);}}
function assert(value,message){if(!value)throw Error(message);}
async function load(){await page.goto(access.url+'#token='+access.token);await page.waitForFunction(()=>document.querySelector('#workflow-name').value.length>0);}
async function fresh(name){const response=page.waitForResponse(r=>r.url().includes('/api/template?'));await page.click('#new-draft');await response;await page.waitForFunction(()=>document.querySelector('#save-state').textContent==='新草稿未保存');await page.fill('#workflow-name',name);}
async function interceptOnce(pattern){
  let release, seen, used=false;
  const reached=new Promise(r=>seen=r), hold=new Promise(r=>release=r);
  const route=async r=>{if(used)return r.continue();used=true;const response=await r.fetch();seen(r.request());await hold;await r.fulfill({response});await page.unroute(pattern,route);};
  await page.route(pattern,route);return {reached,release};
}
(async()=>{
 browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM,args:['--no-sandbox']});
 page=await browser.newPage({viewport:{width:1440,height:1000}});
 await load();
 await check('static response never embeds browser capability',async()=>{
   const response=await page.request.get(access.url);assert(!(await response.text()).includes(access.token),'token exposed');
   assert((await page.request.get(access.url+'api/status')).status()===403,'unauthenticated API accepted');
 });
 await check('open explicit workspace through HTTP',async()=>{
   await page.fill('#workspace-path',access.source);await page.click('#open-workspace');
   await page.waitForFunction(p=>document.querySelector('#workspace-info').textContent.includes(p),access.source);
 });
 await check('A C blank templates editable and blank execution refused',async()=>{
   for(const mode of ['A','C','blank']){
     await page.selectOption('#template',mode);await fresh('edited '+mode);
     await page.click('#save');await page.waitForFunction(()=>document.querySelector('#save-state').textContent==='该快照已保存');
   }
   await page.click('#compile');await page.waitForFunction(()=>document.querySelector('#notice').textContent.includes('sequential'));
   await page.selectOption('#template','B');
 });
 await check('authorization preview displays bound PR tip repository and fixed assertion contract',async()=>{
   await page.selectOption('#template','A');await fresh('preview boundary');
   await page.fill('#task-title','Preview fixture');await page.fill('#task-body','Change README');
   await page.fill('#task-scope','README.md');await page.fill('#task-acceptance','README is correct');await page.check('#delivery');
   await page.click('#prepare');await page.locator('#preview h3').waitFor();
   const preview=await page.textContent('#preview');
   for(const expected of ['fixture/project','flow/usable-test','main','#42','f'.repeat(40),'landlock','json-assertion','expected_json'])assert(preview.includes(expected),'preview hides '+expected);
   assert(await page.locator('#preview textarea').count()===1,'human response missing');
   // No authorization is sent; this is a display regression only.
   await page.uncheck('#delivery');assert(await page.locator('#preview button').count()===0,'stale authorization remained');
   await page.selectOption('#template','B');
 });
 await check('late save A cannot assign identity to new B',async()=>{
   await fresh('race A');const delay=await interceptOnce('**/api/draft');await page.click('#save');await delay.reached;
   await fresh('race B');delay.release();await wait(180);
   const next=page.waitForRequest(r=>r.url().endsWith('/api/draft'));await page.click('#save');
   assert((await next).postDataJSON().id===null,'new B inherited A id');
   await page.waitForFunction(()=>document.querySelector('#save-state').textContent==='该快照已保存');
 });
 await check('edits during save stay dirty',async()=>{
   await fresh('edit before');const delay=await interceptOnce('**/api/draft');await page.click('#save');await delay.reached;
   await page.fill('#workflow-name','edit after');delay.release();
   await page.waitForFunction(()=>document.querySelector('#save-state').textContent.includes('仍有未保存'));
 });
 await check('concurrent new saves reversed preserve active draft',async()=>{
   await fresh('concurrent initial');const delay=await interceptOnce('**/api/draft');await page.click('#save');await delay.reached;
   await page.fill('#workflow-name','concurrent newer');await page.click('#save');
   await page.waitForFunction(()=>document.querySelector('#save-state').textContent==='该快照已保存');
   delay.release();await wait(200);
   assert(await page.inputValue('#workflow-name')==='concurrent newer','old response rewrote editor');
 });
 await check('node add connect delete use actual graph',async()=>{
   await page.selectOption('#add-kind','verifier');await page.click('#add-node');
   await page.waitForFunction(()=>document.querySelector('#node-config strong')?.textContent.startsWith('verifier · verifier-'));
   const id=(await page.textContent('#node-config strong')).split(' · ')[1],edges=await page.locator('#edges li').count();
   await page.selectOption('#edge-source','verifier');await page.selectOption('#edge-target',id);await page.click('#connect');
   assert(await page.locator('#edges li').count()===edges+1,'edge did not connect');
   const count=await page.locator('#canvas .node').count();await page.click('#delete-node');
   assert(await page.locator('#canvas .node').count()===count-1,'node did not delete');
 });
 await check('run A response cannot overwrite B',async()=>{
   await page.click('#refresh-runs');
   await page.waitForFunction(id=>[...document.querySelector('#runs').options].some(o=>o.value===id),access.a);
   const delay=await interceptOnce('**/api/run?id='+access.a);await page.selectOption('#runs',access.a);await delay.reached;
   await page.selectOption('#runs',access.b);await page.waitForFunction(id=>document.querySelector('#run-title').textContent.includes(id+' · BLOCKED'),access.b);
   delay.release();await wait(200);
   assert((await page.textContent('#run-title')).includes(access.b+' · BLOCKED'),'A contaminated B');
   assert(!(await page.textContent('#monitor')).includes('"verdict": "ACCEPT"'),'A verdict contaminated B');
 });
 await check('A B A handles reordered snapshots',async()=>{
   const delay=await interceptOnce('**/api/run?id='+access.a);await page.selectOption('#runs',access.a);await delay.reached;
   await page.selectOption('#runs',access.b);await page.selectOption('#runs',access.a);
   await page.waitForFunction(id=>document.querySelector('#run-title').textContent.includes(id+' · READY'),access.a);
   delay.release();await wait(150);
   assert((await page.textContent('#run-title')).includes(access.a+' · READY'),'selected A lost identity');
 });
 await check('network failure clears prior accepted result',async()=>{
   await page.route('**/api/run?id='+access.a,r=>r.abort('failed'));
   await page.selectOption('#runs',access.b);await page.selectOption('#runs',access.a);
   await page.waitForFunction(()=>document.querySelector('#run-title').textContent.includes('状态未确认'));
   assert(!(await page.textContent('#monitor')).includes('ACCEPT'),'network error retained ACCEPT');
   await page.unroute('**/api/run?id='+access.a);
 });
 await check('page reopen reads same persistent run',async()=>{
   await page.reload();await page.waitForFunction(()=>document.querySelector('#workflow-name').value.length>0);
   await page.selectOption('#runs',access.b);
   await page.waitForFunction(id=>document.querySelector('#run-title').textContent.includes(id+' · BLOCKED'),access.b);
 });
 await page.screenshot({path:path.join(output,'studio.png'),fullPage:true});
})().catch(e=>{results.push({name:'harness',passed:false,error:String(e)});console.error(e);}).finally(async()=>{
 fs.writeFileSync(path.join(output,'results.json'),JSON.stringify({tests:results.length,failures:results.filter(r=>!r.passed).length,skipped:0,results},null,2));
 if(browser)await browser.close();process.exitCode=results.every(r=>r.passed)?0:1;
});
