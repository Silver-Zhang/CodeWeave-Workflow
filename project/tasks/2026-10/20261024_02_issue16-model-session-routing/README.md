# Issue16：模型、会话与可视化路由

## 1. 目标与范围

任务 `20261024_02_issue16-model-session-routing`，B 模式。完整合同为 Issue16（含 F：Sim Studio 实际界面对照），run `396d0ad7c4644a26bb6c70812dc3ef39`；合同原件 raw SHA256 `dffdbc0bd1fb254e89ade0e8bcfefe0031a94f49673b0ed2df3233ea6f560467`。源分支继承 PR15/cdc53cd，保留全部旧实现。main 仍 e35dec1/tree a0c16fa6；不合并、不升级 Stable，不修改 CodeWeave/RMC，不删除会话/历史。

## 2. 做法与证据

[Draft PR17](https://github.com/Silver-Zhang/DevFlower/pull/17) 已提交并推送，以 `flow/workbench-ux-polish` 为 base，依赖 PR15；后者仍 Draft/cdc53cd。源码 HEAD `89203371f2457bca54998e041de4c9f1c4ea804d`，tree `fa31992832bdfb047e9fcf393313babee681e2e6`，163文件 SHA256 `767cb7fc599473f1715d9c903e7d2e6aa9089658063c731709ee7054ef5d4560`；完整清单见 source-manifest.json，测试/过程身份见 evidence.json。

- 最终同候选：505 Python、6宿主隔离、151 Chromium/HTTP、12投影+6编辑器测试；Baseline、6语法与重建通过，所有命令 exit0，FAIL/ERROR/SKIP=0，source_unchanged=true。重建产物逐字节一致。
- 根因：旧 UI 使用预登记模型与 Profile，Claude 缺真实目录发现，缓存未充分区分来源/失败。Codex0.163.0 实际 model/list7；Claude2.1.303 代理目录404，不能假装全集。修复按 Profile 查询/刷新/TTL/错误、effort映射、真实认证与模式绑定、失败原因。
- 实现关闭/Escape/焦点与每标签草稿三选；关闭视图不停止进程。字段合同、实际连线/轮次/来源/哈希与 A–F 下游请求；初始化幂等与旧结果隔离；规则优先 Router、可选只读分类、Schema/阈值/超时/default、全部目标权限检查。顶层交接从实际 activation 显示第1轮，缺失证据仍 unknown。未预期 worker 异常持久化恢复状态、仅清理本 run 可核验进程。
- 真实模型分列：候选 ae81f579 上，两工具新建会话、顺序暂停刷新恢复、两路汇合下游一次、实际代码/研究路由、原生 PTY同身份及双写拒绝均通过，4个冻结worker exit0且stderr空。早期 a688 的3次worker exit1原件保留；不能把 ae81 的成功用于批准最终候选。最终完整双工具场景因Claude402仍待重跑；最终Codex单会话证据另保留，不冒充整版验收。
- Sim：实际启动官方 v0.9.32 镜像（amd64 manifest54748ea5），本地真实 PostgreSQL18/pgvector，查看编辑器/节点/条件/并行/循环/校验日志/聊天/窄屏并保留6组并排截图。无Sim模型密钥/调用；未配置websocket，重连提示如实记录；无Sim代码/品牌资源移植。
- Jev：核实 TypeSafe System One，有官方API与MIT SDK；SDK许可不等于权重许可。本机无独立key，调用0次，权重、本地部署和论文未确认。通用分类对比固定合成集 n=10：规则10/10、轻量分类器7/10、真实LLM9/10；LLM均值3546ms/P50 2751ms/P95 10774ms，成本unknown，非泛化承诺。

## 3. 决策记录

授权允许正常 commit/push/Draft PR，禁止 main 合并/Stable 晋升。原本全部既有 worktree干净，全部保护；只有本任务独立源码 worktree 与本记录实例改动。公开前逐文件检查普通文件、symlink/特殊文件、生成缓存和实际凭据值，未提交认证、原生会话、运行库或大日志。

本任务最多5轮源码审核、基础设施安全重试最多2次；已完成 R1，尝试 R2（服务402），没有隐式加轮或改模型。Claude deepseek-flash[1m]/high，Codex gpt-6.1-sol/xhigh；物理后端/生效effort无独立证明时unknown。旧 Issue12/14 的预算、BLOCKED/ACCEPT 保留，不用于本任务。

## 4. 结论与边界

**阻塞，保持 Draft，未技术验收。** R1 原始 `NEEDS_CORRECTION` 见 review-r1-original.json：Sim实测/真实汇合路由、worker异常收尾、Jev来源、生成缓存及标签ARIA问题；实现者已修复或补证，必需finding尚待独立关闭。R2 实际 CLI exit1，HTTP402余额不足，未产生有效裁决；不写成ACCEPT。额外原生Codex曾独立构造两项JSON边界反例并返回BLOCKED，已修复并加测试；另一完成核验因当时回归1项归档占用拦截仍返回BLOCKED，原件不改。该回归静默后505项通过，确切触发进程未确认。

外部监督的最终状态 BLOCKED/exit2；固定旧Stable Gate确实拒绝旧报告用于新候选的负例（stale or cross-run review）。**完整最终正向Gate未执行**，因为缺少当前候选有效独审和完整真实双工具验收，不自批。用户本人UX待确认；Agent代操作不代签。Stable5816、用户PR15页面45393与原Development33385均不覆盖。

本机 Development 入口：`python3 /home/workspace/DevFlower/.local/open-issue16-workbench.py`，已验证；不是新Stable。原始日志、截图、候选与原生HOME仅本机 archives/devflower-issue16-20261024。

## 5. 过程记录

|阶段|结果与原件|
|---|---|
|预检|真实main/PR15/CI/worktree/修改检查；建立新B任务与分支；新鲜旧基线473Python/6host/142browser/18JS全0。|
|实施与真实调用|模型/关闭/交接/路由；保留所有中间候选、3次worker真实失败及观察器错误，无盲目重发或重写负面结论。|
|R1与修复|真实Claude NEEDS_CORRECTION；修复异常持久化/ARIA、隔离生成pyc，补Sim官方镜像与Jev主要来源；ae81真实4场景通过。|
|R2停止条件|原生Claude402，无裁决；再次真实新建会话亦显示FAILED/402，不生成假成功；停止计费错误重试。|
|后续修复/冻结|原生Codex发现JSON类别/置信度反例，修复；顶层轮次显示加HTTP/Chromium负例；冻结最终候选，完整回归与隐私检查。|
|交付|正常提交/推送，远端HEAD/tree读回，PR17保持Draft；记录同步project/devflower，main/Stable不动。|

接续时先恢复原通道可用性；使用当前候选重新执行真实双工具流程、补最终证据后从明确SID复审（不得--last），最多剩余3轮源码尝试。HOME `archives/devflower-issue16-20261024/runtime/r1`，cwd `/home/workspace/DevFlower`，SID `19e82b7a-d457-4b61-b6a3-1dc0dea84d2b`，原生位置 `.claude/projects/-home-workspace-DevFlower/<SID>.jsonl`。原冻结监督器 helpers/review.py 可 `--resume-from r2 --name r3 --stable-gate-round 3`；新最终候选/完整证据/合同必须重新核验，不直接复用旧成功。记录分支普通check/index；baseline仅对源码执行。
