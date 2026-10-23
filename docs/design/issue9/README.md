# Issue #9 · Agent 会话工作台候选

## 1. 目标与范围

实现工作区只读打开、受批准存储发现、脱敏会话历史与搜索、原生新建/精确恢复、DevFlower 隐藏、Provider/角色解耦、HTTP/UI 和代表回归。只修改 tools/tests/docs/examples/.github。不修改权威状态、Stable pin 或全局认证，不进行 Git 交付。当前工作目录是无 `.git` 的源码快照；GitHub HEAD 与分支不能由该目录核验。外部主线回归绑定的 `61356ac / 10a19a6d` 是基线资料，不能代替本候选证据。

## 2. 做法与证据

`agent_sessions.py` 白名单读取可见用户/助手消息，拒绝隐藏推理和工具块；会话中心使用 workspace + opaque handle，并在读取前后绑定文件身份/哈希。身份包含 Provider、UUID、Profile、cwd、workspace。扫描有文件、字节、深度及 Profile 上限，缺覆盖明确显示。HTTP 不能传入会话路径或可执行 argv。

原生操作经实际权限预览、单次确认、仓库及 HOME 锁、后台 supervisor 执行，绑定原 UUID、HOME、cwd、模型、effort、进程和真实回执。外部历史仅只读；存储登记不授予执行权限。开发会话入口单独固定候选和操作员配置，完全没有 Controller/Stable/Git 交付权限。v2 Developer/Reviewer 使用实际 Provider 调度，可安全隔离的交换组合要求 bwrap 与独立 HOME；v1 合同保持原语义。

自验命令：`python3 -B -m unittest discover -s tests -p test_agent_sessions.py -v`；外部只读合同探针使用原 `operator-probes`；普通浏览器脚本为 `tests/session_browser.py`，真实原生 API 脚本为 `tests/native_sessions.py`。运行数量、原始失败和最终候选 manifest 由本地 scratch-implementer 证据绑定；本文件不把测试脚本的存在称为已经运行或通过。外部宿主回归与实施者自验分别记账。

## 3. 决策记录

无可靠原生 archive/delete CLI 时保持 capability=false、按钮禁用且 HTTP 拒绝。仅隐藏/取消隐藏修改 DevFlower 自有元数据，绝不删除会话、子会话、源码或 worktree。Copilot、并行 DAG 和子 Agent 明确 unsupported。源目录/存储登记与执行授权分离。候选会话入口用于正式 Stable 晋升前的隔离验收，不生成任何晋升或审查批准。

## 4. 结论与边界

代码实施、自验、外部独立审查、原生使用验收与交付是不同关口。新增会话 API/画布路径不代表完整 Issue #9 已验收；最终仍需当前候选的宿主全回归、真实 Codex/Claude 恢复、Stable 发起的真实非零验证与独立修复复审闭环、普通 Chromium 操作证据及外部 gate。不得复用旧 ACCEPT，也不得因缺批准而自签 Stable。未取得的关键证据按 BLOCKED 保留。

## 5. 过程记录

本轮由 Codex 在可写源码快照实施；Claude 与固定外部 Controller 的实际审查、授权、审核轮次和交付状态由外部执行者记录。初始源码清单及逐次失败日志保存在指定 scratch；不会改写外部 task.json/权威状态或生成替代验收回执。运行报告必须注明实际执行者、命令、源码绑定、FAIL/ERROR/SKIP 与未覆盖项。

第 1 轮接续取消的旧配置交接后，逐文件确认当时初始源码等于外部宿主 baseline binding。当前示例 Claude 已改为 `deepseek-flash[1m]/high`，Codex 为 `gpt-6.1-sol/xhigh`；示例和请求配置不是 resolved 模型证据。实施者命名空间没有 Claude executable，没有重试已知不支持的原生嵌套 bwrap 验收。Chromium/Playwright 安装在指定 scratch，未放入源码。

实施者自验包括会话 HTTP/SQLite/文件安全、独立 Reviewer 历史、跨 cwd 防泄漏、精确 UUID 绑定、Profile 上限、长期占用、过期预览与实际画布 Provider 交换。新工作流跨运行复用旧会话因 cwd 不一致明确拒绝；原生 archive/delete、Copilot、任意 DAG、子 Agent 仍 unsupported。详细命令、各次真实失败、最终计数和完整候选 manifest 见外部 scratch 的 evidence-summary.json 与 final-source.json；它们不构成独立审核或 Stable 批准。

第 2 轮初始源码为审核候选 `8b04bbb8c40c0b7708bdd7eedfd47cc859deb179da2516ef1824b7a56cbcccdb`，与本轮外部宿主 binding 一致，整体结果为失败。源码中的固定 Profile 覆盖导致登记目录互相覆盖；已移除此覆盖，并增加同 Provider、相同 UUID/cwd/workspace、不同登记根的 HTTP/SQLite/历史搜索/独立隐藏及 Chromium 持久化回归。修复前的 identity 探针返回 false，失败原样保存。F1 的关闭由外部复审决定。

F2 的处理是重新采集修复后完整源码 manifest、命令、原始输出及各项证据哈希，全部写入 `round-2/scratch-implementer`；不得将 `c6aca58f…` 的第 1 轮通过证据套用到 `8b04bbb8…` 或本轮新候选。本轮报告的生成校验源码前后身份，并要求每份测试记录绑定同一最终 manifest；独立审核与 gate 仍由固定外部执行者负责。

外部宿主在 `8b04bbb8…` 上报告真实 Codex/DeepSeek 新建及精确续聊成功，但原生验收整体因无效认证未准确分类而 BLOCKED。这是旧候选的外部证据，不能证明本轮通过。已补充退出码 0 的错误 envelope、403、反向 API key 错误表述及成功聊天引用认证错误的反例；适配器仅在实际失败时分类，不把聊天正文当成服务认证失败，也不持久化原始输出或凭据。真实服务复验待外部宿主。

原生 CLI 因认证错误重试直到超时时，保留认证诊断，实际 timeout 仍记录在 process 回执；显式取消始终保留 cancelled 类别。测试覆盖上述优先级。浏览器测试的失败尝试也原样保留，包括未先打开历史面板及异步刷新期间截图滚动元素脱离 DOM 的测试步骤问题；修正测试操作后重新绑定源码执行，不把这些尝试记为通过。

第 3 轮初始源码为 `5f07f3e8c534ebe34476ff7855b719e31fb9481bb5a5b8cc47eacddb0d9cbf99`，与外部失败 binding 一致。外部复审已关闭 F1/F2，新增 F3：路径遍历先以 O_RDONLY 打开 `/`，在仅授权工作区/单文件读取的 Landlock 下失败。第 2 轮非隔离探针的 18 项通过不覆盖此 gate；此前把相同失败归因临时目录的判断已被真实 Landlock 证据推翻，原始记录保留。外部宿主的 317 项 Python、6 项宿主隔离及 14 项真实原生 HTTP 检查绑定旧候选，不能当作第 3 轮结果或完整任务卡闭环。

修复将祖先目录逐段以 O_PATH/O_NOFOLLOW/O_DIRECTORY 固定，仅在最终目录上从固定描述符打开可读目录，文件仍经固定 inode 和真实只读打开。没有扩大 Landlock allowlist，也没有更改 Controller、验证断言、隔离策略或批准记录。新增 `test_session_landlock.py` 经真实 Landlock 后端 exec 验证目录/单文件授权、父目录与其他工作区拒绝、原记录不可写、符号链接和并发替换，以及受限 HTTP/节点门禁。`tests/session_browser.py --server-landlock` 可让服务及继承的请求线程受限，同时保持 Chromium 为普通浏览器；权限清单与祖先读取拒绝保存于 `server-isolation.json`。这些数据和浏览器交互使用合成原生历史，不冒充模型续聊证据。

本轮自验保存于 `round-3/scratch-implementer`，明确区分真实 Landlock、普通浏览器、非隔离 Python 及外部旧候选证据。最终 manifest 与每次命令/结果绑定，早期失败与中间树结果不覆写。原生 CLI 的当前候选复验、固定 Stable gate、独立 Claude 复审及真实任务卡闭环仍由外部执行者完成，实施者不签发最终 ACCEPT 或 Stable 批准。
