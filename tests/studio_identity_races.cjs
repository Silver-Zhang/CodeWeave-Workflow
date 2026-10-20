const fs = require('fs'), assert = require('assert/strict');
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const dir = process.argv[2], baseline = process.argv.includes('--baseline');
const access = JSON.parse(fs.readFileSync(dir + '/access.json'));
const doc = JSON.parse(fs.readFileSync(dir + '/document.json'));
const results = []; let browser, sequence = 0;
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
async function until(fn, message, timeout = 3500) {
  const end = Date.now() + timeout;
  while (Date.now() < end) { if (await fn()) return; await delay(15); }
  throw new Error(message);
}
async function test(name, fn) {
  const context = await browser.newContext({viewport: {width: 1700, height: 1000}});
  const p = await context.newPage(); p.setDefaultTimeout(4000);
  const errors = []; p.on('pageerror', e => errors.push(String(e)));
  const queues = [];
  async function hold(pattern, predicate = () => true) {
    const queue = []; queues.push(queue);
    await p.route(pattern, async route => {
      if (!predicate(route.request())) return route.continue();
      const response = await route.fetch();
      let release, done;
      const ready = new Promise(r => release = r), finished = new Promise(r => done = r);
      const item = {body: route.request().postDataJSON(), response: await response.json(),
                    release, finished, status: response.status()}; queue.push(item);
      try {
        await ready;
        if (item.fail) await route.abort('failed');
        else if (item.override) await route.fulfill({status: 200, json: item.override});
        else await route.fulfill({response});
      } catch {} finally { done(); }
    });
    return queue;
  }
  const api = async (path, data) => {
    const options = {headers: {Authorization: 'Bearer ' + access.token}};
    if (data !== undefined) options.data = data;
    const r = await context.request[data === undefined ? 'get' : 'post'](access.url + path, options);
    return {status: r.status(), value: await r.json()};
  };
  const seed = async name => (await api('api/workflows', {document: {...structuredClone(doc), name}})).value;
  const open = async () => {
    await p.goto(access.url + '#token=' + access.token);
    await p.locator('#runs button').nth(1).waitFor();
    await p.locator('.node').nth(6).waitFor();
  };
  const rename = async name => { await p.getByLabel('流程名称', {exact: true}).fill(name); await p.getByLabel('流程名称', {exact: true}).press('Tab'); };
  const release = async q => { q.release(); await q.finished; await delay(60); };
  const save = async (q, n) => { await p.locator('#save').click(); await until(() => q.length > n, 'save request absent'); return q[n]; };
  const select = async id => { await p.locator(`#runs button[title="${id}"]`).click(); };
  const view = async () => ({title: await p.locator('#title').innerText(), revision: await p.locator('#revision').innerText(),
    round: await p.locator('#round-label').innerText(), nodes: await p.locator('#nodes').innerText(),
    rounds: await p.locator('#rounds').innerText(), notice: await p.locator('#notice').innerText(),
    connection: await p.locator('#connection').innerText()});
  try {
    const detail = await fn({p, context, hold, api, seed, open, rename, release, save, select, view});
    assert.deepEqual(errors, []); results.push({name, status: 'PASS', detail});
  } catch (e) { results.push({name, status: 'FAIL', error: String(e)}); }
  finally {
    for (const q of queues) for (const item of q) item.release();
    await delay(60);
    await p.screenshot({path: `${dir}/case-${++sequence}.png`}).catch(() => {});
    await context.close();
  }
  console.log(JSON.stringify(results.at(-1)));
}
async function main() {
  browser = await chromium.launch({executablePath: process.env.CHROMIUM, headless: true, args: ['--no-sandbox']});
  await test('ST-R04 delayed save A cannot adopt new B identity', async ({p, hold, open, rename, save, release}) => {
    await open(); await rename('NEW_A'); const q = await hold('**/api/workflows', r => r.method() === 'POST');
    const a = await save(q, 0); await p.locator('#new').click(); await rename('NEW_B'); await release(a);
    const b = await save(q, 1); await release(b);
    assert.notEqual(b.body.id, a.response.id, 'B adopted A id: ' + JSON.stringify({a: a.response, b: b.body.id}));
    assert.notEqual(b.response.id, a.response.id); return {a: a.response, b: b.response};
  });
  await test('ST-R05 late A snapshot cannot populate selected B', async ({p, hold, open, select, release, view}) => {
    await open(); const q = await hold('**/api/runs/' + access.a);
    await select(access.a); await until(() => q.length === 1, 'A snapshot absent');
    await select(access.b); await release(q[0]); const v = await view();
    assert.notEqual(v.title, 'RUN_A', 'selected B with A content: ' + JSON.stringify(v));
    await until(async () => (await view()).title === 'RUN_B', 'B snapshot absent');
    const b = await view(); assert(b.revision.includes(access.b)); assert(b.nodes.includes('9 tests')); assert(!b.nodes.includes('6 tests'));
    assert.equal(b.round, '当前第 3 轮'); assert(!b.rounds.includes('ACCEPT')); return b;
  });
  // Additional identity cases are exercised on every fixed candidate.
  if (!baseline) await additional();
}
async function additional() {
  await test('ST-R04 save A then load B preserves B id and CAS base', async ({p, seed, open, hold, rename, save, release, api}) => {
    const a = await seed('LOAD_A'), b = await seed('LOAD_B'); await open();
    await p.locator('#workflows button').filter({hasText: 'LOAD_A'}).click(); await p.getByLabel('流程名称', {exact: true}).filter({}).waitFor();
    await until(async () => (await p.locator('#title').innerText()) === 'LOAD_A', 'A load');
    await rename('LOAD_A_EDIT'); const q = await hold('**/api/workflows', r => r.method() === 'POST'); const first = await save(q, 0);
    await p.locator('#workflows button').filter({hasText: 'LOAD_B'}).click(); await until(async () => (await p.locator('#title').innerText()) === 'LOAD_B', 'B load');
    await release(first); await rename('LOAD_B_EDIT'); const second = await save(q, 1); await release(second);
    assert.equal(second.body.id, b.id); assert.equal(second.body.expected, b.revision);
    assert.equal((await api('api/workflows/' + a.id)).value.document.name, 'LOAD_A_EDIT');
    assert.equal((await api('api/workflows/' + b.id)).value.document.name, 'LOAD_B_EDIT');
  });
  await test('ST-R04 different draft saves complete in reverse order', async ({p, open, hold, rename, save, release}) => {
    await open(); await rename('REVERSE_A'); const q = await hold('**/api/workflows', r => r.method() === 'POST'); const a = await save(q, 0);
    await p.locator('#new').click(); await rename('REVERSE_B'); const b = await save(q, 1);
    await release(b); await release(a); await rename('REVERSE_B_2'); const b2 = await save(q, 2); await release(b2);
    assert.equal(b2.body.id, b.response.id); assert.equal(b2.body.expected, b.response.revision);
    assert.notEqual(b.response.id, a.response.id);
  });
  await test('ST-R04 edit during save stays dirty and next save uses returned revision', async ({p, open, hold, rename, save, release}) => {
    await open(); await rename('EDIT_A'); const q = await hold('**/api/workflows', r => r.method() === 'POST'); const a = await save(q, 0);
    await rename('EDIT_A_2'); await release(a);
    assert((await p.locator('#revision').innerText()).includes('未保存')); assert((await p.locator('#notice').innerText()).includes('未保存'));
    const next = await save(q, 1); await release(next); assert.equal(next.body.id, a.response.id); assert.equal(next.body.expected, a.response.revision);
    assert.equal(next.body.document.name, 'EDIT_A_2'); assert((await p.locator('#revision').innerText()).startsWith('已保存版本'));
  });
  await test('ST-R04 uncommitted input during save is never called fully saved', async ({p, open, hold, rename, save, release}) => {
    await open(); await rename('INPUT_A'); const q = await hold('**/api/workflows', r => r.method() === 'POST'); const a = await save(q, 0);
    await p.getByLabel('流程名称', {exact: true}).fill('INPUT_B_UNCOMMITTED'); await release(a);
    assert((await p.locator('#revision').innerText()).includes('未保存')); assert((await p.locator('#notice').innerText()).includes('未保存'));
  });
  await test('ST-R04 concurrent same-draft clicks serialize one POST', async ({p, open, hold, rename, save, release}) => {
    await open(); await rename('DOUBLE_A'); const q = await hold('**/api/workflows', r => r.method() === 'POST'); const a = await save(q, 0);
    assert(await p.locator('#save').isDisabled()); await p.locator('#save').evaluate(e => {e.disabled = false; e.click(); e.click();});
    await delay(120); assert.equal(q.length, 1); await release(a); assert(!(await p.locator('#save').isDisabled()));
  });
  await test('ST-R04 concurrent external save still enforces backend CAS', async ({p, seed, api, open, hold, rename, save, release}) => {
    const a = await seed('CAS_A'); await open(); await p.locator('#workflows button').filter({hasText: 'CAS_A'}).click();
    await until(async () => (await p.locator('#title').innerText()) === 'CAS_A', 'CAS load');
    const original = (await api('api/workflows/' + a.id)).value.document;
    const winner = await api('api/workflows', {id: a.id, expected: a.revision, document: {...original, name: 'CAS_WINNER'}}); assert.equal(winner.status, 200);
    await rename('CAS_LOSER'); const q = await hold('**/api/workflows', r => r.method() === 'POST'); const loser = await save(q, 0); await release(loser);
    assert.equal(loser.status, 409); assert((await p.locator('#notice').innerText()).includes('another tab'));
    assert.equal((await api('api/workflows/' + a.id)).value.revision, winner.value.revision);
  });
  await test('ST-R04 old save failure cannot overwrite new draft notice', async ({p, open, hold, rename, save, release}) => {
    await open(); await rename('ERROR_A'); const q = await hold('**/api/workflows', r => r.method() === 'POST'); const a = await save(q, 0);
    await p.locator('#new').click(); await rename('ERROR_B'); const before = await p.locator('#notice').innerText(); a.fail = true; await release(a);
    assert.equal(await p.locator('#notice').innerText(), before); assert.equal(await p.locator('#title').innerText(), 'ERROR_B');
  });
  await test('ST-R04 save completion in monitor cannot overwrite run header', async ({p, open, hold, rename, save, release, select, view}) => {
    await open(); await rename('MONITOR_SAVE'); const q = await hold('**/api/workflows', r => r.method() === 'POST'); const a = await save(q, 0);
    await select(access.b); await until(async () => (await view()).title === 'RUN_B', 'B snapshot'); await release(a);
    const b = await view(); assert(b.revision.includes(access.b)); assert.equal(b.title, 'RUN_B');
    await p.locator('#design-tab').click(); assert.equal(await p.locator('#title').innerText(), 'MONITOR_SAVE'); assert((await p.locator('#revision').innerText()).startsWith('已保存版本'));
  });
  await test('ST-R05 reverse responses cannot replace B with A', async ({open, hold, select, release, view}) => {
    await open(); const qa = await hold('**/api/runs/' + access.a), qb = await hold('**/api/runs/' + access.b);
    await select(access.a); await until(() => qa.length === 1, 'A snapshot'); await select(access.b); await until(() => qb.length === 1, 'B snapshot');
    await release(qb[0]); const before = await view(); await release(qa[0]); const after = await view();
    assert.equal(after.title, 'RUN_B'); for (const field of ['title','revision','round','nodes','rounds','notice']) assert.equal(after[field], before[field]);
  });
  await test('ST-R05 obsolete network failure cannot clear successful B', async ({open, hold, select, release, view}) => {
    await open(); const qa = await hold('**/api/runs/' + access.a); await select(access.a); await until(() => qa.length === 1, 'A snapshot');
    await select(access.b); await until(async () => (await view()).title === 'RUN_B', 'B snapshot'); qa[0].fail = true; await release(qa[0]);
    const b = await view(); assert.equal(b.title, 'RUN_B'); assert(b.connection.includes('已连接')); assert(b.nodes.includes('9 tests'));
  });
  await test('ST-R05 current network failure clears stale nodes and verdicts', async ({p, open, select, view}) => {
    await open(); await select(access.a); await until(async () => (await view()).title === 'RUN_A', 'A snapshot');
    await p.route('**/api/runs/' + access.a, route => route.abort('failed')); await p.locator('#refresh-runs').click();
    await until(async () => (await view()).connection.includes('数据不可用'), 'failure indicator');
    const v = await view(); assert.equal(v.nodes, ''); assert.equal(v.rounds, ''); assert(!v.notice.includes('通过门禁')); assert.equal(await p.locator('#inspector').innerText(), '');
    await p.unroute('**/api/runs/' + access.a); await p.locator('#refresh-runs').click(); await until(async () => (await view()).title === 'RUN_A', 'network recovery');
  });
  await test('ST-R05 response id mismatch rejected without READY or ACCEPT', async ({open, hold, select, release, view, api}) => {
    await open(); const q = await hold('**/api/runs/' + access.a); await select(access.a); await until(() => q.length === 1, 'A snapshot');
    q[0].override = (await api('api/runs/' + access.b)).value; await release(q[0]); const v = await view();
    assert(v.connection.includes('数据不可用')); assert.equal(v.nodes, ''); assert.equal(v.rounds, '');
  });
  await test('ST-R05 leaving monitor discards pending response and preserves draft', async ({p, open, rename, hold, select, release, view}) => {
    await open(); await rename('DESIGN_SURVIVES'); const q = await hold('**/api/runs/' + access.a); await select(access.a); await until(() => q.length === 1, 'A snapshot');
    await p.locator('#design-tab').click(); await release(q[0]); const v = await view();
    assert.equal(v.title, 'DESIGN_SURVIVES'); assert(!v.revision.includes('Controller')); assert.equal(v.rounds, ''); assert.equal(await p.locator('.node.running').count(), 0);
  });
  await test('ST-R05 obsolete run-list response cannot start old selection query', async ({p, open, hold, select, release, view}) => {
    await open(); const q = await hold('**/api/runs'); await select(access.a); await until(() => q.length === 1, 'A list');
    await select(access.b); await until(() => q.length === 2, 'B list'); await release(q[1]);
    await until(async () => (await view()).title === 'RUN_B', 'B snapshot'); await release(q[0]); assert.equal((await view()).title, 'RUN_B');
  });
  await test('ST-R05 A-B-A ignores first A even when run id matches again', async ({open, hold, select, release, view}) => {
    await open(); const qa = await hold('**/api/runs/' + access.a), qb = await hold('**/api/runs/' + access.b);
    await select(access.a); await until(() => qa.length === 1, 'first A'); await select(access.b); await until(() => qb.length === 1, 'B');
    require('child_process').execFileSync('python3', ['-c',
      'import sqlite3,json,sys; d=sqlite3.connect(sys.argv[1]); r=json.loads(d.execute("select data from runs where id=?",(sys.argv[2],)).fetchone()[0]); r["round"]=r["candidate_round"]=4; r["verification"][0]["round"]=4; r["verification"][0]["counts"]["tests"]=12; r["review"]["report"]["round"]=4; r["reviews"][0]["round"]=4; d.execute("update runs set data=? where id=?",(json.dumps(r),sys.argv[2])); d.commit(); d.close()',
      dir + '/control/state.sqlite', access.a]);
    await select(access.a); await until(() => qa.length === 2, 'second A'); await release(qa[1]); await release(qb[0]); await release(qa[0]);
    const a = await view(); assert.equal(a.title, 'RUN_A'); assert.equal(a.round, '当前第 4 轮'); assert(a.nodes.includes('12 tests')); assert(!a.nodes.includes('6 tests'));
  });
}
main().catch(e => { results.push({name: 'harness', status: 'FAIL', error: String(e)}); }).finally(async () => {
  fs.writeFileSync(dir + '/identity-results.json', JSON.stringify({real_http: true, offline_bridge: false,
    fixtures: 'real local HTTP and SQLite/WAL, no model calls, no authority issued', baseline_reproduction: baseline,
    tests: results.length, failures: results.filter(r => r.status === 'FAIL').length, skipped: 0, results}, null, 2));
  if (browser) await browser.close(); process.exitCode = results.some(r => r.status === 'FAIL') ? 1 : 0;
});
