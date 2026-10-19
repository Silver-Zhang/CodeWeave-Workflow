# DevFlower v0.2-A 受控双 Agent 运行器

任务：20261019_01_v02a-orchestrator；B 模式。进度以 task.json 为准；原始裁决及哈希见 evidence.json。

## 1. 目标与范围

把既定 v0.2-A 实现为 Linux 本地顺序 Controller；单源码写入实施者、固定候选独立复核，按 A01–A16 验收。本任务仅 DevFlower 框架及 project/devflower 档案。停止于 v0.2-A，不进入 v0.2-B，不修改 CodeWeave/RMC。

源码分支 flow/multi-agent-orchestration，初始 ff55386eeb49a634a9a28bf796b4cf6872800e2b，依赖 218a6e81652d5c6e20dc8909d93dfd1b9395f58a。实施交付阶段 PR #1 仍 open；后续整理时核实它已于 2026-10-19 19:27（上海）由外部操作合入 main，结果 536a0580b70bffe2cca009fcbd9f4e9d8c5e3459，继承 218a6e8 已核对。本轮仅同步已有结果。原 DevFlower 初检为干净 project/codeweave（39f4ae9）；后续只读复查发现外部已切至干净 flow（ff55386），保留实际状态。另建独立源码与记录 clone，未 stash/reset/clean，未占用或推送 project/codeweave。

## 2. 做法与证据

环境：Python 3.12.3、Git 2.43.0、Codex CLI 0.163.0、Claude Code 2.1.303、Landlock ABI 8，宿主机支持 Bubblewrap。doctor 的认证仅证实本地配置；实际服务能力由真实调用另证。旧基线完整 checkout 上 24/24、0 skip；当前候选 unittest 72/72、0 skip（包含旧 24 项），宿主机隔离 3/3、0 skip，check --baseline 通过。

A0 已实现：doctor/run/status/resume/cancel/audit/deliver；旧 init/new/index/check 兼容。SQLite 事务状态/事件、外部 intent、flock 与进程身份、完整源码字节/mode/链接清单、授权/合同/Controller 哈希、机械 gate、有界进程监督、固定副本与隔离测试。模拟进程覆盖错误身份、缺终态、洪水、超时、取消、矛盾 ACCEPT、零测试/Skip、证据变化和恢复。

A1 已实测：真实 CLI 适配器，project/role/明确 UUID 绑定，不使用 --last/--continue。自有 signed-parser fixture 已由实际 Claude 给出 NEEDS_CORRECTION，再由实际 Codex 修复、8 项真实测试通过（0 skip）、同一明确审核 UUID 返回 ACCEPT。精确当前 Controller（ff6555075c785dc9b91c9c96e4b7df4e417a4a0a641a45329eb1c4be3238eb2c）重放亦为 READY、8/8、Claude ACCEPT，未 commit/push fixture。实施请求 gpt-6.1-sol/xhigh，CLI 缺实际字段按 unknown；该 fixture 审核请求/返回 claude-opus-5-5[1m]，请求 high、实际 effort unknown。fixture 候选和合同与框架不同，不互相冒充。

A2 已实测：仅自有本地 bare remotes，精确 Git tree、用户 index 保护、commit 中断恢复、push 成功但回执丢失后的读回、远端竞争，以及源码成功/记录失败的部分交付和只重试后者。未将产品交付 backend 指向真实业务仓库。

框架独立复核：外部固定 bootstrap（不导入新 Controller）冻结候选并启动专属审核；审核者先读合同、代码、实际证据，再对照实施说明。第 4 轮 DeepSeek 经 Claude Code 实际执行其独立脚本，231 项负例与证据检查全部通过；其中 A15 的 27 项是对真实过程记录的核对，非重新调用模型。外部断网、无凭据 runner 重跑同一脚本亦 231/231、exit 0；脚本 SHA256 640148b2c4fc03e4fc999194fb13c62bbbd779960976c6421724c15da01fbc2d。必需的“ACCEPT+测试失败”“审后/构树中改源码”“push 成功回执丢失”“两库仅一库成功”均有独立负例。

原始大日志、逐轮原始终态、失败与复现脚本现归档于工作区 archives/devflower/v0.2-a/evidence/（受控目录；原目录 devflower-v02a-evidence 的路径映射另存 archives/layout.json），认证、隐藏推理和完整会话不作为 Controller 日志或公开档案。

## 3. 决策记录

2026-10-19 用户完整指令批准既定 v0.2-A 范围内实施与测试，以及有前提的 commit/push，仅允许源码 flow/multi-agent-orchestration、独立档案 project/devflower。禁止 main merge、project/codeweave push、force/tag/release/delete；本提示词不是未来任务永久授权。用户确认 Claude 使用中转站无问题；保留原路由，没有擅自换服务或购买服务。

用户随后说“我可以换成deepseek接入claude code，先暂停”：核对 PID/start/进程组后仅停止本轮审核并保存暂停点。收到“现在好了继续”后，按用户已自行调整的 deepseek-flash[1m]/high 新建明确绑定 DevFlower 独立审核角色的 UUID；第 4 轮终态确认为该模型，实际 effort 无字段仍 unknown。该裁决署名 DeepSeek（通过 Claude Code），不伪称 Anthropic Claude；旧 Claude 裁决保持原意。审核角色的模型调整依据为这次明确暂停、配置变更与恢复指令。

运行器无法在外层隔离内创建 Codex 原生嵌套 namespace；仅显式 isolation=bwrap、external_sandbox=true、授权哈希绑定且实际探针通过时，把执行边界交给外层 Bubblewrap，CLI 使用 danger-full-access。源码副本/专用 home 可写，原 Git/控制状态/交付凭据不挂载；未裸进程绕过隔离，默认仍 workspace-write。不得据本机探针推导任意平台安全。

当前候选自验、真实独立 ACCEPT、旧必需缺陷关闭、代码/合同哈希及外部 Git tree 核对满足本轮交付条件。命令行 Git 没有 HTTPS 写入凭据，实际使用已连接 GitHub API 的普通快进 ref 更新、expected SHA 检查，随后原生 Git fetch 与逐 blob 核对；未导出或索取凭据。新 Controller 未批准、提交或推送自身。

## 4. 结论与边界

A0/A1/A2 在本轮限定范围内完成，框架第 4 轮原始 verdict 为 ACCEPT，findings 为空；此前 5 个 P1 均由独立审核显式 CLOSED。用户最终验收尚未另行确认。

框架候选 SHA256：147da481da3b7ad8025541d1be3cc402baf89f88ff97bc97ca045c3e78320ba7；验收合同 SHA256：ac5715b0567ada01b8464ef21a9eb019d945c0406f1e75033da02719e718ac7f。

源码提交并远端读回：210e208b5872507b9ff5c6471b5ef0acdea9518d；Git tree 0a9a8027c072d01153778627a427e75a2fd0bca0，36 个文件全部 blob 字节/mode 等于被审清单，源码 clone 干净。记录分支的最终 commit/ref 回执放本地外部记录及用户交付回复，不在本档案内嵌自己的最终 SHA。两分支没有原子保证；部分成功必须按实际回执报告。

限制：Linux 本地；测试 runner 要求 Landlock ABI >=6，真实 CLI 可使用经探针核验的 Bubblewrap；网络 egress 不隔离，私有源码外发需独立授权。产品交付仅本地 bare backend，真实业务试点仍未批准。active hooks/filter/submodule/LFS 阻断；C 模式需外部绑定真实 G1–G4。批准的 argv 不应带密钥。非 gpt-/claude- 别名记录 requested/resolved，但精确 resolved-ID 不等校验仅用于 gpt-/claude- 前缀；本地配置变化仍按绑定哈希阻断。审核者实际运行 Landlock 负例；Bubblewrap 三项宿主机测试和 A15 真实过程记录由实施/外部 runner 产生、审核者检查，未冒称审核者亲自重放。

本地整理：工作区顶层仅 CodeWeave/、DevFlower/、archives/。独立源码/档案 checkout 分别迁入 archives/devflower/v0.2-a/checkouts/flow/ 与 records/；CodeWeave 既有 M0/M1 过程目录分类存入 archives/codeweave/m0/、m1/，其源码和云端项目分支未改。11 个目录搬移前后完整文件内容、链接文本和 mode 清单一致，两个关联 worktree 已 repair；原始报告内的历史路径保持不变。旧运行授权绑定旧路径，不能直接作为新地址的恢复许可。

云端整理：PR #2 已面向 main，标题与说明更新为真实实现、验证结果及限制；仍 open，未执行合并。当前源码 210e208、被审候选和合同哈希均未变化。

## 5. 过程记录

| 日期 | 实际结果、失败及处理 |
|---|---|
| 2026-10-19 | 核对原目录、远端与已有修改；独立 clone，旧回归 24/24，现有工具建 B 模式任务 |
| 2026-10-19 | 真实 CLI 早期失败：专用 home 遗漏原 gateway 配置、Claude 不注册 draft-2020-12 URI、原生嵌套 sandbox 不可用；保留证据后分别修复，不改模型换服务 |
| 2026-10-19 | 第 1 轮 Claude：NEEDS_CORRECTION，5 个 P1（home/source 重叠、构树竞态、new 会话可恢复 UUID、自源码可达 READY、Controller 哈希漏入口）；独立设计 6 项负例由外部执行，2 失败、4 通过 |
| 2026-10-19 | 新候选修复；第 2 轮 900 秒超时，没有模型终态/裁决；不视为 ACCEPT |
| 2026-10-19 | 精确当前候选自验 72/72、宿主机隔离 3/3；真实 Codex/Claude fixture 拒绝→修复→复审完成，当前版本重放 8/8/ACCEPT |
| 2026-10-19 | 第 3 轮在用户明确暂停后停止，约 638 秒、exit -15、无终态；属于主动中止，不假称服务自然失败 |
| 2026-10-19 | 用户调整为 DeepSeek 并恢复；第 4 轮约 653 秒、exit 0、真实 ACCEPT，231 项独立检查及外部重跑均通过，5 个旧 P1 CLOSED |
| 2026-10-19 | 外部方式核对被审源码/合同/准提交 tree，源码分支正常快进并 fetch 逐 blob 读回；独立 records 分支归档，不进入下一阶段 |
| 2026-10-19 | 按用户要求同步云端并整理本地：核实 PR #1 已合并，更新 PR #2 实际状态；11 个过程目录迁入 archives/ 并核验字节/mode，修复两个 worktree，更新现行档案路径 |
