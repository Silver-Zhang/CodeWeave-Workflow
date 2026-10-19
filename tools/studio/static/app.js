/* Local, dependency-free canvas. Runtime data never becomes editable run state. */
const $ = (id) => document.getElementById(id);
const clone = (value) => structuredClone(value);
const fragment = new URLSearchParams(location.hash.slice(1));
if (fragment.has('token')) {
  sessionStorage.setItem('devflower-token', fragment.get('token'));
  history.replaceState(null, '', location.pathname);
}
const token = sessionStorage.getItem('devflower-token') || '';
let graph, saved = {}, importedTask = null, compiled = null, meta;
let editVersion = 0, compileRequest = 0, loadRequest = 0, starting = false;
function invalidate() { editVersion++; compiled = null; $('start').disabled = true; }
function snapshotKey() { return JSON.stringify({document: graph, task: importedTask}); }
function canStart() {
  return mode === 'design' && !starting && !invalidFields() && compiled && compiled.editVersion === editVersion &&
    compiled.snapshot === snapshotKey() && meta?.launcher.enabled && !meta.launcher.used &&
    meta.launcher.config_sha256 === compiled.config_sha256;
}
function invalidFields() { return $('inspector').querySelector('input:invalid,textarea:invalid'); }
function checkFields() { if (invalidFields()) throw new Error('请先修正并提交当前参数，再编译或启动。'); }
function refreshStart() { $('start').disabled = !canStart(); }
let mode = 'design', selection = null, selectedEdge = null, runId = null, runData = null;
let zoom = 0.8, undoStack = [], redoStack = [], connecting = null, fileKind = '', busy = false;
const states = {pending: '未开始', completed: '已完成', passed: '通过', running: '进程运行中',
  executed: '已执行 · 等待结果验证', unconfirmed: '阶段已开始 · 进程未证实', failed: '验证失败', needs_correction: '需要修复',
  blocked: '已阻断', cancelled: '已取消', disabled: '未授权交付', partial: '部分交付'};
const icons = {authorization: 'H', implementer: 'Cx', freeze: '#', verification: '✓', reviewer: 'Cr', gate: 'G', delivery: '↗'};
const typeNames = {authorization: 'HUMAN AUTHORIZATION', implementer: 'IMPLEMENTER', freeze: 'CANDIDATE SNAPSHOT',
  verification: 'VERIFICATION', reviewer: 'INDEPENDENT REVIEW', gate: 'DETERMINISTIC GATE', delivery: 'DELIVERY'};
function el(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}
function notify(message, error = false) {
  $('toast').textContent = message; $('toast').hidden = false;
  $('notice').textContent = message; $('notice').classList.toggle('error', error);
  clearTimeout(notify.timer); notify.timer = setTimeout(() => $('toast').hidden = true, 4500);
}
async function api(path, body) {
  const options = {headers: {Authorization: `Bearer ${token}`}, cache: 'no-store', signal: AbortSignal.timeout(7000)};
  if (body !== undefined) { options.method = 'POST'; options.headers['Content-Type'] = 'application/json'; options.body = JSON.stringify(body); }
  const response = await fetch(path, options);
  const value = await response.json();
  if (!response.ok) throw new Error(value.error || `HTTP ${response.status}`);
  return value;
}
function documentNow() { return mode === 'run' ? runData?.graph : graph; }
function remember() {
  if (mode !== 'design') return;
  undoStack.push(clone(graph)); if (undoStack.length > 40) undoStack.shift(); redoStack = [];
  invalidate();
}
function changed() { invalidate(); $('revision').textContent = '草稿已修改 · 保存创建不可变版本'; }
function draw() {
  const doc = documentNow(); $('nodes').replaceChildren(); $('paths').replaceChildren();
  if (!doc) { $('title').textContent = '选择真实运行'; return; }
  $('title').textContent = doc.name;
  for (const node of doc.nodes) {
    const status = mode === 'run' ? node.status || 'pending' : 'pending';
    const card = el('article', undefined, `node ${status}${selection === node.id ? ' selected' : ''}${mode === 'run' ? ' locked' : ''}`);
    card.dataset.id = node.id; card.tabIndex = 0; card.style.left = `${node.x}px`; card.style.top = `${node.y}px`;
    card.setAttribute('aria-label', `${node.label}，${states[status]}`);
    const head = el('div', undefined, 'node-header'); head.append(el('span', icons[node.type], `node-icon ${node.type}`));
    const name = el('div'); name.append(el('div', node.label, 'node-title'), el('div', typeNames[node.type], 'node-type'));
    head.append(name); card.append(head);
    let detail = node.type === 'verification' ? node.config.id : node.config.model || '由 Controller 验证';
    if (node.counts) detail = `${node.counts.tests} tests · ${node.counts.failures + node.counts.errors} failed · ${node.counts.skipped} skip`;
    card.append(el('div', detail, 'node-body'));
    const footer = el('div', undefined, 'node-footer'); footer.append(el('i', undefined, `dot ${status}`), el('span', mode === 'run' ? states[status] : '待授权 · 设计节点'));
    card.append(footer);
    for (const direction of ['in', 'out']) {
      const port = el('button', undefined, `port ${direction}`); port.dataset.node = node.id;
      port.title = `${node.label} · ${direction === 'in' ? '入口' : '出口'}`; port.setAttribute('aria-label', port.title);
      port.disabled = mode === 'run'; card.append(port);
      port.addEventListener('pointerdown', (event) => {
        event.stopPropagation(); if (mode !== 'design') return;
        if (direction === 'out') { connecting = node.id; $('ghost').setAttribute('d', ''); }
      });
      port.addEventListener('click', (event) => {
        event.stopPropagation();
        if (direction === 'in' && connecting) connect(connecting, node.id);
        else if (direction === 'out') { connecting = node.id; notify('拖动或点击目标模块的入口完成连线；校验会拒绝越过门禁。'); }
      });
    }
    card.addEventListener('click', () => { selection = node.id; selectedEdge = null; highlight(); inspect(); });
    card.addEventListener('keydown', (event) => {
      if (mode !== 'design' || !['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(event.key)) return;
      event.preventDefault(); remember();
      node.x = Math.max(0, node.x + ({ArrowLeft: -10, ArrowRight: 10}[event.key] || 0));
      node.y = Math.max(0, node.y + ({ArrowUp: -10, ArrowDown: 10}[event.key] || 0)); changed(); draw();
    });
    card.addEventListener('pointerdown', (event) => {
      if (mode !== 'design' || event.button !== 0 || event.target.closest('.port')) return;
      const x = event.clientX, y = event.clientY, initialX = node.x, initialY = node.y;
      let moved = false; card.setPointerCapture(event.pointerId);
      const move = (e) => {
        if (!moved && Math.hypot(e.clientX - x, e.clientY - y) < 3) return;
        if (!moved) { remember(); moved = true; }
        node.x = Math.max(0, Math.min(1800, initialX + (e.clientX - x) / zoom));
        node.y = Math.max(0, Math.min(1200, initialY + (e.clientY - y) / zoom));
        card.style.left = `${node.x}px`; card.style.top = `${node.y}px`; drawEdges();
      };
      const up = () => { card.removeEventListener('pointermove', move); card.removeEventListener('pointerup', up); if (moved) changed(); };
      card.addEventListener('pointermove', move); card.addEventListener('pointerup', up);
    });
    $('nodes').append(card);
  }
  drawEdges(); highlight(); applyZoom();
}
function highlight() {
  for (const card of $('nodes').children) card.classList.toggle('selected', card.dataset.id === selection);
  $('delete-edge').disabled = selectedEdge === null || mode === 'run';
}
function line(a, b, repair) {
  const x1 = a.x + 225, y1 = a.y + 71, x2 = b.x, y2 = b.y + 71;
  if (repair) return `M${x1},${y1} C${x1 + 100},${y1 + 170} ${x2 - 100},${y2 + 230} ${x2},${y2}`;
  if (x2 < x1 && y2 > y1 + 80) { const mid = (y1 + y2) / 2 + 30; return `M${x1},${y1} C${x1+55},${y1} ${x1+55},${mid} ${x1},${mid} L${x2-35},${mid} C${x2-65},${mid} ${x2-65},${y2} ${x2},${y2}`; }
  const d = Math.max(70, Math.abs(x2 - x1) / 2);
  return `M${x1},${y1} C${x1 + d},${y1} ${x2 - d},${y2} ${x2},${y2}`;
}
function drawEdges() {
  const doc = documentNow(); $('paths').replaceChildren(); if (!doc) return;
  doc.edges.forEach((edge, index) => {
    const a = doc.nodes.find(n => n.id === edge.source), b = doc.nodes.find(n => n.id === edge.target);
    if (!a || !b) return;
    const p = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    p.setAttribute('d', line(a, b, edge.on === 'repair'));
    p.setAttribute('class', `edge ${edge.on}${index === selectedEdge ? ' selected' : ''}${mode === 'run' && b.status === 'running' && edge.on === 'next' ? ' active' : ''}`);
    p.setAttribute('marker-end', 'url(#arrow)');
    p.addEventListener('click', () => { selectedEdge = index; selection = null; drawEdges(); highlight(); inspect(); });
    $('paths').append(p);
  });
}
function connect(source, target) {
  connecting = null; $('ghost').setAttribute('d', ''); if (source === target) return;
  const on = $('edge-kind').value;
  if (graph.edges.some(e => e.source === source && e.target === target && e.on === on)) return;
  remember(); graph.edges.push({source, target, on}); changed(); drawEdges(); notify('连线已添加。导出前必须通过后端结构校验。');
}
window.addEventListener('pointermove', (event) => {
  if (!connecting || mode !== 'design') return;
  const from = graph.nodes.find(n => n.id === connecting); if (!from) return;
  const box = $('world').getBoundingClientRect();
  $('ghost').setAttribute('d', line(from, {x: (event.clientX - box.left) / zoom, y: (event.clientY - box.top) / zoom - 71}, false));
});
window.addEventListener('pointerup', (event) => {
  if (!connecting) return;
  const port = document.elementFromPoint(event.clientX, event.clientY)?.closest('.port.in');
  if (port) connect(connecting, port.dataset.node);
});
$('viewport').addEventListener('pointerdown', (event) => {
  if (event.target.closest('.node') || event.target.classList.contains('edge') || event.button !== 0) return;
  selection = null; selectedEdge = null; connecting = null; $('ghost').setAttribute('d', ''); highlight(); inspect();
  const viewport = $('viewport'), startX = event.clientX, startY = event.clientY, left = viewport.scrollLeft, top = viewport.scrollTop;
  viewport.setPointerCapture(event.pointerId); viewport.classList.add('dragging');
  const move = e => { viewport.scrollLeft = left - (e.clientX - startX); viewport.scrollTop = top - (e.clientY - startY); };
  const up = () => { viewport.removeEventListener('pointermove', move); viewport.removeEventListener('pointerup', up); viewport.classList.remove('dragging'); };
  viewport.addEventListener('pointermove', move); viewport.addEventListener('pointerup', up);
});
function field(label, value, change, type = 'text') {
  const box = el('label', undefined, 'field'); box.append(el('span', label));
  const input = el(type === 'textarea' ? 'textarea' : 'input');
  if (type !== 'textarea') input.type = type;
  input.value = value; input.addEventListener('input', () => { invalidate(); input.setCustomValidity('参数尚未提交或无效'); }); input.addEventListener('change', () => { try { remember(); change(input.value); input.setCustomValidity(''); changed(); draw(); } catch (error) { input.setCustomValidity(error.message); notify(error.message, true); } });
  box.append(input); return box;
}
function inspect() {
  const box = $('inspector'); box.replaceChildren(); const doc = documentNow(); if (!doc) return;
  const node = doc.nodes.find(n => n.id === selection);
  $('inspector-title').textContent = node ? node.label : mode === 'run' ? '运行快照' : '流程设置';
  if (mode === 'run') {
    box.append(el('p', '只读快照。编辑草稿不会改变当前运行；没有真实进程证据不点亮运行指示。', 'hint'));
    box.append(el('pre', JSON.stringify(node ? {type: node.type, status: states[node.status], requested: node.config, resolved_model: node.resolved_model, counts: node.counts} : {run_id: runData.id, mode: runData.mode, state: runData.state, round: runData.round, candidate: runData.candidate, candidate_round: runData.candidate_round, candidate_frozen: runData.candidate_frozen, previous_candidate: runData.previous_candidate, config_sha256: runData.config_sha256, process: runData.process_liveness, delivery: runData.delivery}, null, 2)));
    return;
  }
  if (!node) {
    box.append(field('流程名称', graph.name, v => graph.name = v));
    box.append(field('任务目标（编译到 goal）', graph.goal, v => graph.goal = v, 'textarea'));
    box.append(field('最大审核轮数（1–5）', graph.limits.max_review_rounds, v => graph.limits.max_review_rounds = Number(v), 'number'));
    box.append(field('步骤超时 / 秒', graph.limits.step_timeout_seconds, v => graph.limits.step_timeout_seconds = Number(v), 'number'));
    box.append(el('p', importedTask ? `已导入任务：${importedTask.task_id}。源码、范围、权限由该任务保留。` : '先导入现有完整 task.json，再导出可运行配置；operator.json 不属于画布输入。', 'hint'));
    const bind = el('button', '绑定 task.json（保留此画布）'); bind.onclick = () => { fileKind = 'bind'; $('file-input').value = ''; $('file-input').click(); }; box.append(bind);
    box.append(el('p', '只有 B 模式受约束图可编译。可添加和重排测试；不能自由绕过冻结、独立审核、门禁或扩大交付权限。', 'hint'));
  } else {
    box.append(field('节点名称', node.label, v => node.label = v));
    if (node.type === 'implementer' || node.type === 'reviewer') {
      box.append(field('请求模型（unknown 沿用绑定）', node.config.model, v => node.config.model = v));
      box.append(field('请求推理强度', node.config.effort, v => node.config.effort = v));
      box.append(el('p', '模型、会话、认证、角色 home 仍由操作员批准；画布改变模型后须重新授权。Claude Code 不等于固定的底层 Claude 模型。', 'hint'));
    } else if (node.type === 'verification') {
      box.append(field('验收 / 验证 ID', node.config.id, v => node.config.id = v));
      box.append(field('命令 argv（JSON 数组）', JSON.stringify(node.config.argv, null, 2), v => { const a = JSON.parse(v); if (!Array.isArray(a)) throw new Error('argv 必须是数组'); node.config.argv = a; }, 'textarea'));
      box.append(field('结果格式：junit / controller-json', node.config.result_format, v => node.config.result_format = v));
      box.append(field('最少测试数', node.config.min_cases, v => node.config.min_cases = Number(v), 'number'));
      box.append(field('最多跳过数', node.config.max_skipped, v => node.config.max_skipped = Number(v), 'number'));
      const remove = el('button', '删除此测试节点'); remove.addEventListener('click', () => removeTest(node)); box.append(remove);
    } else {
      box.append(el('p', '受保护的执行环节。改变坐标或名称不会修改权限。门禁、人工授权和 Git 交付由现有 Controller 独立验证。', 'hint'));
    }
  }
}
function autoLayout(doc) {
  const order = ['authorization', 'implementer', 'freeze', ...doc.nodes.filter(n => n.type === 'verification').map(n => n.id), 'reviewer', 'gate', 'delivery'];
  order.forEach((id, i) => { const n = doc.nodes.find(n => n.id === id); if (!n) return;
    const row = Math.floor(i / 4), col = i % 4; n.x = 65 + col * 280; n.y = 85 + row * 215;
  });
}
function applyZoom() { $('world').style.transform = `scale(${zoom})`; $('surface').style.width = `${2000 * zoom}px`; $('surface').style.height = `${1400 * zoom}px`; $('zoom').textContent = `${Math.round(zoom * 100)}%`; }
function switchMode(next) {
  mode = next; selection = null; selectedEdge = null; connecting = null;
  $('design-tab').classList.toggle('selected', mode === 'design'); $('run-tab').classList.toggle('selected', mode === 'run');
  for (const id of ['save', 'compile', 'add-test', 'edge-kind', 'validate', 'export-graph', 'undo', 'redo']) $(id).disabled = mode === 'run';
  $('context').textContent = mode === 'run' ? '只读 · 实际配置与运行事件 · 每秒刷新' : 'B 模式 · 有界修复循环 · 原有门禁不可绕过';
  $('revision').textContent = mode === 'run' ? `Controller run ${runId || '未选择'}` : saved.revision ? `已保存版本 ${saved.revision.slice(0, 12)}` : '未保存的本地草稿';
  if (mode === 'design') { $('viewport').classList.remove('stale'); $('notice').classList.remove('error'); $('notice').textContent = '画布决定测试顺序及节点参数；启动仍须终端中的独立授权。草稿不是运行状态。'; }
  refreshStart(); draw(); inspect();
}
function download(name, value) { const url = URL.createObjectURL(new Blob([JSON.stringify(value, null, 2) + '\n'], {type: 'application/json'})); const a = el('a'); a.href = url; a.download = name; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000); }
async function designs() {
  const list = await api('/api/workflows'); $('workflows').replaceChildren();
  if (!list.length) $('workflows').textContent = '尚未保存';
  for (const item of list) {
    const button = el('button', item.name); button.append(el('small', item.revision.slice(0, 12)));
    button.onclick = () => attempt(async () => { invalidate(); const request = ++loadRequest; const version = editVersion; const data = await api(`/api/workflows/${item.id}`); if (request !== loadRequest || version !== editVersion) return; invalidate(); graph = data.document; saved = {id: data.id, revision: data.revision}; importedTask = null; compiled = null; undoStack = []; redoStack = []; switchMode('design'); notify('已加载画布版本。运行任务配置不随草稿存储；请重新导入 task.json。'); }); $('workflows').append(button);
  }
}
async function poll() {
  if (busy || !meta?.control_configured) return; busy = true;
  try {
    const result = await api('/api/runs'); $('runs').replaceChildren();
    if (!result.runs.length) $('runs').textContent = result.available ? '尚无真实运行' : `等待状态库${result.launcher.controller_exit === null ? '' : ' · Controller exit ' + result.launcher.controller_exit}`;
    for (const run of result.runs) {
      const button = el('button', run.task_id, runId === run.id ? 'active' : '');
      button.append(el('small', `${run.state} · Round ${run.round}`)); button.title = run.id;
      button.onclick = () => { runId = run.id; runData = null; switchMode('run'); poll(); };
      $('runs').append(button);
    }
    if (!runId && mode === 'run' && result.runs.length) runId = result.runs[0].id;
    if (runId) {
      runData = await api(`/api/runs/${runId}`);
      autoLayout(runData.graph);
      if (mode === 'run') { $('revision').textContent = `Controller run ${runId}`; draw(); inspect(); $('notice').textContent = runData.message; $('notice').classList.toggle('error', runData.state === 'BLOCKED'); }
      $('timeline').replaceChildren();
      for (const event of runData.events.slice().reverse()) { const row = el('div', undefined, 'event'); row.append(el('time', new Date(event.at * 1000).toLocaleTimeString()), el('span', event.kind), el('small', event.round ? `Round ${event.round}` : `#${event.seq}`)); $('timeline').append(row); }
      $('rounds').replaceChildren();
      for (const round of runData.rounds) { const row = el('div', undefined, 'round'); row.append(el('span', `Round ${round.round} · ${round.candidate?.slice(0, 8) || 'unknown'}`), el('span', round.verdict, 'tag')); $('rounds').append(row); }
      $('round-label').textContent = `当前第 ${runData.round} 轮`;
    }
    $('connection').textContent = `已连接 · 读取 ${new Date().toLocaleTimeString()}`; $('connection').className = 'chip good'; $('viewport').classList.remove('stale');
    meta.launcher = result.launcher; refreshStart();
  } catch (error) {
    $('connection').textContent = '数据不可用 · 不推断运行'; $('connection').className = 'chip bad'; $('viewport').classList.add('stale');
    $('runs').textContent = error.message;
  } finally { busy = false; }
}
async function attempt(fn) { try { await fn(); } catch (error) { notify(error.message, true); } }
function removeTest(node) {
  if (graph.nodes.filter(n => n.type === 'verification').length === 1) return notify('至少需要一个真实验证节点。', true);
  remember(); const previous = graph.edges.find(e => e.target === node.id && e.on === 'next'), next = graph.edges.find(e => e.source === node.id && e.on === 'next');
  graph.nodes = graph.nodes.filter(n => n.id !== node.id); graph.edges = graph.edges.filter(e => e.source !== node.id && e.target !== node.id);
  if (previous && next) graph.edges.push({source: previous.source, target: next.target, on: 'next'});
  selection = null; changed(); draw(); inspect();
}
$('add-test').onclick = () => { remember(); const id = `verify-${Date.now()}`;
  const old = graph.edges.find(e => e.target === 'reviewer' && e.on === 'next');
  graph.nodes.push({id, type: 'verification', label: '新增验证', x: 910, y: 510, config: {id: `test-${graph.nodes.length}`, argv: ['python3', 'verify.py', '{result}'], result_format: 'controller-json', min_cases: 1, max_skipped: 0}});
  if (old) { const from = old.source; old.source = id; graph.edges.push({source: from, target: id, on: 'next'}); }
  selection = id; changed(); draw(); inspect(); };
$('delete-edge').onclick = () => { if (selectedEdge === null || mode !== 'design') return; remember(); graph.edges.splice(selectedEdge, 1); selectedEdge = null; changed(); drawEdges(); highlight(); };
$('new').onclick = () => { invalidate(); ++loadRequest; graph = clone(meta.template); saved = {}; importedTask = null; compiled = null; undoStack = []; redoStack = []; autoLayout(graph); switchMode('design'); };
$('design-tab').onclick = () => switchMode('design'); $('run-tab').onclick = () => { switchMode('run'); poll(); };
$('layout').onclick = () => { if (mode === 'design') { remember(); autoLayout(graph); changed(); } else if (runData) autoLayout(runData.graph); draw(); };
$('zoom-out').onclick = () => { zoom = Math.max(.35, zoom - .1); applyZoom(); }; $('zoom-in').onclick = () => { zoom = Math.min(1.5, zoom + .1); applyZoom(); };
$('undo').onclick = () => { if (!undoStack.length || mode !== 'design') return; redoStack.push(clone(graph)); graph = undoStack.pop(); changed(); draw(); inspect(); };
$('redo').onclick = () => { if (!redoStack.length || mode !== 'design') return; undoStack.push(clone(graph)); graph = redoStack.pop(); changed(); draw(); inspect(); };
window.addEventListener('keydown', e => { if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'z' && !e.target.matches('input,textarea')) { e.preventDefault(); $(e.shiftKey ? 'redo' : 'undo').click(); } if (e.key === 'Escape') { connecting = null; $('ghost').setAttribute('d', ''); } });
$('validate').onclick = () => attempt(async () => { checkFields(); const result = await api('/api/validate', {document: graph}); notify(`校验通过 · ${result.order.length} 个执行节点。不是授权或正确性证明。`); });
$('save').onclick = () => attempt(async () => { checkFields(); const value = await api('/api/workflows', {document: graph, id: saved.id, expected: saved.revision}); saved = value; $('revision').textContent = `已保存版本 ${value.revision.slice(0, 12)}`; await designs(); notify('已保存不可变画布版本。当前运行不受影响。'); });
$('export-graph').onclick = () => attempt(async () => { checkFields(); download('workflow.json', graph); });
$('compile').onclick = () => attempt(async () => {
  checkFields();
  if (!importedTask) throw new Error('先导入完整 B 模式 task.json；画布不创建源码路径、认证或授权。');
  invalidate();
  const version = editVersion, request = ++compileRequest, snapshot = snapshotKey();
  const result = await api('/api/compile', JSON.parse(snapshot));
  if (request !== compileRequest || version !== editVersion || snapshot !== snapshotKey()) return;
  compiled = {...result, editVersion: version, snapshot};
  download('task.studio.json', compiled.task);
  refreshStart();
  notify(`任务配置已导出 · ${compiled.config_sha256.slice(0, 12)}。变更需独立授权；未生成许可。`);
});
$('start').onclick = () => attempt(async () => {
  if (!canStart() || !confirm('仅启动操作员通过终端绑定并授权的这一份任务。可能产生模型调用费用。确认启动？') || !canStart()) return;
  const hash = compiled.config_sha256; starting = true; refreshStart();
  try { await api('/api/start', {config_sha256: hash}); } finally { invalidate(); starting = false; }
  runId = null; switchMode('run'); notify('Controller 已启动，正在等待真实运行记录；不代表 Agent 或验收成功。'); await poll();
});
for (const [id, kind] of [['import-graph', 'graph'], ['import-task', 'task']]) $(id).onclick = () => { fileKind = kind; $('file-input').value = ''; $('file-input').click(); };
$('file-input').onchange = () => attempt(async () => {
  const file = $('file-input').files[0]; if (!file) return;
  if (file.size > 230000) throw new Error('文件过大；不要导入原始日志或凭据文件。');
  invalidate(); const request = ++loadRequest, version = editVersion, kind = fileKind;
  const data = JSON.parse(await file.text());
  let next;
  if (kind === 'task' || kind === 'bind') next = await api('/api/from-task', {task: data});
  else { await api('/api/validate', {document: data}); next = data; }
  if (request !== loadRequest || version !== editVersion) return;
  invalidate(); importedTask = kind === 'task' || kind === 'bind' ? data : null;
  if (kind === 'bind') { inspect(); notify('已绑定任务配置；当前画布和保存版本未改变。'); return; }
  graph = next; saved = {}; compiled = null; undoStack = []; redoStack = []; autoLayout(graph); switchMode('design'); notify('已导入。仅保存画布，不保存 operator.json 或运行授权。');
});
$('refresh-designs').onclick = () => attempt(designs); $('refresh-runs').onclick = poll;
async function initialize() {
try {
  meta = await api('/api/meta'); graph = clone(meta.template); autoLayout(graph); draw(); inspect();
  $('connection').textContent = meta.control_configured ? '已连接 · 等待记录' : '设计模式 · 未连接运行'; $('connection').className = 'chip good';
  await designs(); await poll(); setInterval(poll, 1000);
} catch (error) {
  $('connection').textContent = '需要本地访问令牌'; $('connection').className = 'chip bad';
  notify(`${error.message}。请打开终端打印的完整 #token= 地址。`, true);
}
}
initialize();
