/* Read-only native session metadata. No shell/model execution endpoint. */
(() => {
  const el = (tag, text, className) => {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = text;
    if (className) node.className = className;
    return node;
  };
  async function api(path) {
    const response = await fetch(path, {cache: 'no-store', signal: AbortSignal.timeout(7000),
      headers: {Authorization: `Bearer ${sessionStorage.getItem('devflower-token') || ''}`}});
    const value = await response.json();
    if (!response.ok) throw new Error(value.error || `HTTP ${response.status}`);
    return value;
  }
  const select = document.getElementById('project-workspace');
  const panel = document.getElementById('session-panel');
  const list = document.getElementById('session-list');
  const coverage = document.getElementById('session-coverage');
  const status = document.getElementById('session-status');
  let request = 0, selected = null, workspaces = [];
  const labels = {complete: '扫描完成', partial: '部分覆盖', not_found: '未发现',
    permission_denied: '无权限', refused: '拒绝访问', not_scanned: '未扫描', unsupported: '不支持'};
  function clear(message) {
    list.replaceChildren(); coverage.replaceChildren(); delete status.dataset.scannedAt; status.textContent = message;
  }
  async function refresh() {
    const current = ++request, id = selected;
    clear(id ? '正在读取元数据…' : '请在终端使用 --project-root 登记业务工作区');
    if (!id) return;
    try {
      const data = await api(`/api/workspaces/${id}/sessions`);
      if (current !== request || id !== selected) return;
      if (data.workspace_id !== id) throw new Error('响应工作区身份不匹配');
      const workspace = workspaces.find(x => x.id === id);
      document.getElementById('session-heading').textContent = workspace.path;
      status.dataset.scannedAt = String(data.scanned_at);
      status.textContent = `${data.sessions.length} 个会话 · 机器 ${data.machine.slice(0, 12)} · 只读索引`;
      for (const source of data.coverage) {
        const line = el('p', `${source.provider} · ${source.storage_root} · Profile ${source.profile_id.slice(0, 10)} · ${labels[source.status] || source.status}`);
        if (source.rejected && Object.keys(source.rejected).length) {
          line.append(el('small', `；限制/拒绝：${JSON.stringify(source.rejected)}`));
        }
        coverage.append(line);
      }
      coverage.append(el('p', `不支持：${data.unsupported.join(', ')}。未读取聊天正文；本页面不能恢复或执行会话。`));
      for (const session of data.sessions) {
        if (session.workspace_id !== id) throw new Error('会话归属身份不匹配');
        const row = el('article', undefined, 'session-row');
        row.dataset.identity = session.identity;
        row.append(el('strong', `${session.provider} · ${session.session_id}`));
        row.append(el('p', `存储：${session.storage_root} · Profile ${session.profile_id}`));
        row.append(el('p', `真实 cwd：${session.cwd} · ${session.cwd_verified ? '本机目录已核验' : '目录未验证'} · 归属：${session.association}`));
        row.append(el('p', `工作区：${session.workspace} · 时间：${session.updated || '未知'} · CLI：${session.cli_version || '未知'}`));
        row.append(el('p', '已发现 · 可读取元数据 · 仅查看 · 恢复未验证 · 进程占用未知'));
        if (session.resume_command) {
          const details = el('details');
          details.append(el('summary', '原环境恢复命令建议（未验证，不执行）'));
          const command = el('textarea'); command.readOnly = true; command.value = session.resume_command;
          command.setAttribute('aria-label', '未验证的恢复命令');
          const copy = el('button', '复制命令');
          copy.onclick = async () => {
            try { await navigator.clipboard.writeText(command.value); copy.textContent = '已复制'; }
            catch { command.focus(); command.select(); copy.textContent = '请手动复制选中文本'; }
          };
          details.append(command, copy); row.append(details);
        } else row.append(el('small', '缺少原环境或 cwd 证据，不能生成准确恢复命令。'));
        list.append(row);
      }
    } catch (error) {
      if (current !== request || id !== selected) return;
      clear(`会话列表不可用：${error.message}`);
    }
  }
  const innerSelect = document.getElementById('session-workspace');
  select.onchange = () => {
    innerSelect.value = select.value;
    selected = select.value || null; ++request;
    document.getElementById('session-heading').textContent = workspaces.find(x => x.id === selected)?.path || '业务工作区';
    clear('工作区已切换');
    if (panel.open) refresh();
  };
  innerSelect.onchange = () => { select.value = innerSelect.value; select.onchange(); };
  document.getElementById('open-sessions').onclick = () => { panel.showModal(); refresh(); };
  document.getElementById('close-sessions').onclick = () => panel.close();
  panel.addEventListener('close', () => { ++request; clear('已关闭'); });
  document.getElementById('refresh-sessions').onclick = refresh;
  api('/api/workspaces').then(data => {
    workspaces = data.workspaces;
    select.replaceChildren();
    if (!workspaces.length) select.append(el('option', '未登记业务工作区'));
    for (const workspace of workspaces) {
      const option = el('option', workspace.path); option.value = workspace.id; select.append(option);
    }
    innerSelect.replaceChildren(...Array.from(select.options, option => option.cloneNode(true)));
    selected = workspaces[0]?.id || null;
  }).catch(() => { select.replaceChildren(el('option', '工作区登记不可用')); });
})();
