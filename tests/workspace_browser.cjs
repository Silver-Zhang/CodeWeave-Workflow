const fs=require('fs'),path=require('path'),assert=require('assert');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const out=process.argv[2], config=JSON.parse(fs.readFileSync(path.join(out,'access.json'),'utf8'));
const tests=[];
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM,headless:true,args:['--no-sandbox']});
 async function page(){
  const p=await browser.newPage({viewport:{width:1440,height:1000}});
  await p.goto(config.url+'/#token='+config.token);
  await p.waitForFunction(()=>document.querySelector('#project-workspace').options.length===2);
  await p.click('#open-sessions');
  await p.waitForFunction(()=>document.querySelectorAll('.session-row').length===3);
  return p;
 }
 async function test(name,fn){
  let p;
  try{p=await page();await fn(p);tests.push({name,passed:true});}
  catch(e){tests.push({name,passed:false,error:String(e)});fs.writeFileSync(path.join(out,'browser-results.json'),JSON.stringify(tests,null,2));}
  finally{if(p){await p.screenshot({path:path.join(out,`case-${tests.length}.png`)});await p.close();}}
  fs.writeFileSync(path.join(out,'browser-results.json'),JSON.stringify(tests,null,2));
 }
 async function hold(p,id){
  let arrived,release,finish,routeError;
  const finished=new Promise(r=>finish=r);
  const seen=new Promise(r=>arrived=r),gate=new Promise(r=>release=r);
  const url=`**/api/workspaces/${id}/sessions`;
  let used=false;
  const callback=async route=>{
   if(used){await route.continue();return;}
   used=true;
   const response=await route.fetch();const body=await response.body();
   arrived(JSON.parse(body.toString()));
   await gate;
   try { await route.fulfill({response,body}); }
   catch(error) { routeError=String(error); }
   finally { finish(); }
  };
  await p.route(url,callback);
  return {seen,release,remove:async()=>{await finished;await p.unroute(url,callback);if(routeError)throw new Error(routeError);}};
 }
 await test('Three real HTTP source profiles; duplicate native IDs remain distinct and no content leaks',async p=>{
  const ids=await p.locator('.session-row').evaluateAll(rows=>rows.map(x=>x.dataset.identity));
  assert.equal(new Set(ids).size,3);
  const text=await p.locator('#session-panel').innerText();
  assert(text.includes('codex')&&text.includes('claude')&&text.includes('恢复未验证'));
  assert(!text.includes('PRIVATE_PROMPT')&&!text.includes('SYNTHETIC_AUTH'));
  await p.locator('.session-row summary').first().click();
  assert((await p.locator('.session-row textarea').first().inputValue()).includes('HOME='));
  assert(!(await p.locator('.session-row textarea').first().inputValue()).includes('--last'));
 });
 await test('Delayed A response cannot replace selected B',async p=>{
  const h=await hold(p,config.a);await p.click('#refresh-sessions');await h.seen;
  await p.selectOption('#session-workspace',config.b);
  await p.waitForFunction(()=>document.querySelectorAll('.session-row').length===1);
  h.release();await h.remove();await p.waitForTimeout(150);
  assert.equal(await p.locator('.session-row').count(),1);
  assert.equal(await p.locator('#session-heading').innerText(),config.b_path);
 });
 await test('A-B-A keeps the second A request when the first A returns last',async p=>{
  const h=await hold(p,config.a);await p.click('#refresh-sessions');const old=await h.seen;
  await p.selectOption('#session-workspace',config.b);
  await p.waitForFunction(()=>document.querySelectorAll('.session-row').length===1);
  await p.selectOption('#session-workspace',config.a);
  await p.waitForFunction(()=>document.querySelectorAll('.session-row').length===3);
  const newest=await p.locator('#session-status').getAttribute('data-scanned-at');
  assert(Number(newest)>old.scanned_at);
  h.release();await h.remove();await p.waitForTimeout(150);
  assert.equal(await p.locator('#session-status').getAttribute('data-scanned-at'),newest);
 });
 await test('Concurrent refresh responses cannot overwrite the newest snapshot',async p=>{
  const h=await hold(p,config.a);await p.click('#refresh-sessions');await h.seen;
  await p.click('#refresh-sessions');
  await p.waitForFunction(()=>document.querySelectorAll('.session-row').length===3);
  const newest=await p.locator('#session-status').getAttribute('data-scanned-at');
  h.release();await h.remove();await p.waitForTimeout(150);
  assert.equal(await p.locator('#session-status').getAttribute('data-scanned-at'),newest);
 });
 await test('Current network failure clears metadata, then real HTTP recovery works',async p=>{
  const url=`**/api/workspaces/${config.a}/sessions`;
  await p.route(url,route=>route.abort());await p.click('#refresh-sessions');
  await p.waitForFunction(()=>document.querySelector('#session-status').textContent.includes('不可用'));
  assert.equal(await p.locator('.session-row').count(),0);
  await p.unroute(url);await p.click('#refresh-sessions');
  await p.waitForFunction(()=>document.querySelectorAll('.session-row').length===3);
 });
 await test('Closed panel ignores pending snapshot and fresh reopen succeeds',async p=>{
  const h=await hold(p,config.a);await p.click('#refresh-sessions');await h.seen;
  await p.click('#close-sessions');h.release();await h.remove();await p.waitForTimeout(150);
  assert.equal(await p.locator('.session-row').count(),0);
  await p.click('#open-sessions');
  await p.waitForFunction(()=>document.querySelectorAll('.session-row').length===3);
 });
 await test('Mismatched workspace identity fails closed',async p=>{
  const url=`**/api/workspaces/${config.a}/sessions`;
  await p.route(url,async route=>{
   const response=await route.fetch(),data=await response.json();data.workspace_id=config.b;
   await route.fulfill({response,json:data});
  });
  await p.click('#refresh-sessions');
  await p.waitForFunction(()=>document.querySelector('#session-status').textContent.includes('不匹配'));
  assert.equal(await p.locator('.session-row').count(),0);
 });
 await browser.close();
 const failures=tests.filter(x=>!x.passed).length;
 console.log(JSON.stringify({tests:tests.length,failures,errors:0,skipped:0}));
 process.exitCode=failures?1:0;
})().catch(e=>{console.error(String(e));process.exitCode=1;});
