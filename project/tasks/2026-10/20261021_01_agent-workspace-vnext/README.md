# DevFlower Agent Workspace vNext — Issue #9

## 1. 目标与范围

执行 [Issue #9](https://github.com/Silver-Zhang/DevFlower/issues/9)：统一工作区入口、Agent 会话中心、原生新建/恢复、受支持生命周期及灵活节点配置。仅 DevFlower，不改 CodeWeave/RMC，不合并 main，不自动批准 Stable，不改全局认证，不删除原生会话。源码与研发记录分支分开；原始日志、截图和原生会话仅留本地。

## 2. 做法与证据

基线 HEAD `61356ac07aca24382970b72de9607b1daff26767`，基线 tree `10a19a6d8fe34633ffbc667a33ac518eb7f248dd`。最终候选 SHA-256 `74c7c3d8776a9736556850b632274afe7118e693e70126dd5e2b028d9213704e`，101 文件；被审及提交 tree `087d124f2259b7562e5abfec3d4e9bbda533c16e`，29 处路径变更。

使用原已批准 5816 Stable、固定外部监督与真实 Studio 运行；未用待审 Controller 自批。初始主线回归为 276 Python、6 宿主隔离、73 Chromium/HTTP 场景通过。最终源码绑定结果：

| 验证 | 实际结果 |
|---|---|
| Python 全回归 | 323 tests，0 failure/error/skip，exit 0 |
| 宿主隔离 / 固定旧 Stable 合同探针 | 6 / 18 全部通过，exit 0 |
| baseline / 5 份 JS 语法 | 全部 exit 0；结构检查不是批准 |
| 原 Chromium/HTTP 回归 | 73 场景通过 |
| 新会话 UI 回归 | 32 项断言通过，合成历史，非真实模型验收 |
| 真实 native/API | 16 检查通过，含 9 项普通 Chromium 续聊与重开检查 |
| 真实 Development worktree 补证 | Codex/DeepSeek 共 4 个原生回合、9 项浏览器检查通过 |

真实模型证据覆盖两提供方新建/同 UUID 恢复/上下文召回、当前实施与独立审核历史共同可见、实际 Claude 开发角色写入单一授权临时 docs 文件并恢复，以及跨工作区、缺权限、源码过期、HOME 占用、真实取消和认证反例。错误 key 调用为 FAILED/timeout，不伪称观察到 401；另有实际缺认证的 FAILED/authentication。真实目录补证的工作台软件为最终候选，项目当时仍为交付前基线 `61356ac/d971d550`，身份分别记录。

实现包括安全发现、脱敏历史/搜索、原生生命周期监督、只读和执行边界、灵活 Provider/角色/Profile/模型/effort/工具/预算、旧合同兼容及 Landlock 祖先遍历修复。命令入口为 `tools/devflower_sessions.py`（Development 会话 GUI）及既有 `devflower_usable.py`（需已批准 Stable）；init/new/index/check 兼容。本次发布前重新核对完整文件清单、Git tree、进程空闲、baseline 和公开内容边界，未另启动模型审核。

## 3. 决策记录

实际 Claude Code 模型 `deepseek-flash[1m]`、请求 effort `high`；CLI 没有可核验生效 effort 字段，记 `unknown`。Codex 为 `gpt-6.1-sol/xhigh`。明确项目/角色会话身份，无 --last 猜测；旧 Opus 运行取消后完整保留。GUI 实际操作人为 Codex、授权 principal 为用户，不声称独立真人 GUI 验收。

总 5 轮审核（main 1 + 开发 4），原意见不改写：

| 轮次 | 原始裁决 | 反馈及修复 |
|---|---|---|
| main 准入 | BLOCKED | 当时缺真实完整闭环；审核沙箱环境失败另列，未复用旧 ACCEPT |
| 开发 R1 | NEEDS_CORRECTION | F1 身份遗漏存储 Profile；F2 自验哈希不匹配冻结候选 |
| 开发 R2 | NEEDS_CORRECTION | F1/F2 CLOSED；新增 P0 F3：Landlock 根目录 O_RDONLY 回归 |
| 开发 R3 | ACCEPT_WITH_LIMITATIONS | F1/F2/F3 全 CLOSED，必需合同 PASS |
| 开发 R4 | ACCEPT_WITH_LIMITATIONS | 相同源码补真实 Development 原生/GUI 证据；20 项必需合同 PASS，无未关 finding |

R2/R3 独立审核通过真实 Landlock ABI 8 反例定位/关闭 F3，没有扩大 allowlist 或放宽断言。原始失败、审核者误计数及后续纠正均保留。固定硬 ACCEPT gate 两次拒绝自动交付，总预算用尽后停止；原 run 仍 BLOCKED。

**2026-10-21 用户随后明确批准按当前 ACCEPT_WITH_LIMITATIONS 提交、推送并创建 Draft PR，代码到 flow/agent-workspace-vnext、精简记录到 project/devflower。** 此次外部人工授权发布不修改产品门禁、原 run 状态或原审核裁决，不复用旧运行授权，也不授予 Stable 身份。

## 4. 结论与边界

当前为**已发布 Draft、最终验收待决策**，不宣称完整 Issue #9 完成或 READY_TO_MERGE。源码提交 `465a31f523fc265b1bcbcd0ecdef6eca06a6e0e0` 已正常推送并读回一致；[Draft PR #10](https://github.com/Silver-Zhang/DevFlower/pull/10) 指向 main，保持未合并。研发档案仅在 project/devflower，本文件不将记录仓库 SHA 当作源码 SHA。

保留限制：审核沙箱无法独立重跑 Chromium、原生 Claude 和真实 Development 目录，相关证据由外部受控执行者运行，独立审核核查绑定与源码；额外严格服务浏览器模式三次 FAILED_NOT_CLAIMED_PASS（Node 版本、AF_UNIX 路径长度、测试专用 /dev/null 写权限），普通必需浏览器测试通过不能替代该额外模式；尚无独立真人 GUI 最终验收或新 Stable 晋升批准。

原生 archive/delete 没有已验证安全接口，明确 unsupported；只有 Studio 元数据隐藏/取消隐藏。外部导入/多 cwd 历史只读，受控 managed HOME 才能经授权原生恢复。Copilot、任意并行 DAG/子 Agent、远程 URI 未支持。现用 Stable 不变，新 main/vNext RC 仅不可执行的未批准提案；Development session-only 预览无 Controller/交付批准权限。正式准入与任何 Stable 晋升仍待另行决策，不自动进入下一阶段。

## 5. 过程记录

2026-10-21：同步 main 与保护工作树 → 完整主线回归/新审核 → 原可信 Stable 真实 GUI 启动 → 模型切换后取消/交接/重冻结 → 四轮真实开发/独立审核/自动修复 → 补真实目录原生与 GUI 证据 → 硬 gate 阻断、预算停止 → 同哈希本地物化 → 用户另行批准有限接受下的 Draft 发布 → 提交/推送/PR。受控身份故障在首轮冻结前注入，记录前后哈希；真实失败与模型修复均未模拟。

额外工具预检被拒绝、错误启动哈希被拒绝、无认证/错误认证及严格服务浏览器实验均原样保留，不改写为通过。首次 HTTPS 推送因 OAuth 缺 workflow scope 被 GitHub 拒绝，远端未更新；随后使用本机现有 Silver-Zhang SSH 认证正常推送并读回，无全局认证/远端配置变更。当前 private runtime 0700、私有服务日志 0600。

按用户授权清理 4 个本地旧分支：flow/devflower-usable-v1、flow/multi-agent-orchestration、flow/studio-mvp、flow/workspace-session-m0；事前逐一确认提交均可从 main 到达且无工作树占用。main、当前 flow、project/devflower 保留；仅移除远端已不存在的本地 tracking refs，未删除任何远端分支、原生会话或证据。

本机启动：`python3 /home/workspace/DevFlower/archives/devflower-vnext-20261021/real-workspace-acceptance/open-studio.py`。实际 Development 会话预览端口 41053，原固定管理 33915 与用户旧 34235 保留；私有 URL 不入库。完整证据在本机 `archives/devflower-vnext-20261021`，必要摘要/哈希在本任务 evidence.json；两分支远端回执由本地 publication 目录另存，不能声称跨分支原子交付。
