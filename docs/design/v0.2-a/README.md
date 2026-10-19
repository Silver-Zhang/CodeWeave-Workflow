# DevFlower v0.2-A：可恢复的双 Agent 执行器

状态：实施设计合同；Controller 候选接口见 [运行说明](../../ORCHESTRATOR.md)。本目录不是已发布的 v0.2，也不能证明真实 Agent 或 Git 门禁已经运行通过；实际证据另在 project/devflower 记录。

## 1. 目标、范围与既有规则

将“Codex 实施 → 自验 → Claude 独立审核 → 修复 → 复审 → 获准后提交推送”从长 Prompt 提炼成可检查、可恢复的本地程序。保留现有 A/B/C、五步研发、五节任务 README、源码与工作流分仓；不建立聊天知识库。

A/B/C 表示人参与深度，execution profile 表示调度方式，delivery policy 表示 Git 权限，三者独立。C 模式的 G1–G4 仍是实际人工事件；程序不能替人勾选。

v0.2-A 只做 Linux 本地、单任务、单写入实施者、单独立审核者，以及显式授权的一个源码目标仓库和一个工作流记录仓库。Codex/Claude 通过可替换 CLI 适配器接入。Jev、自动风险分类、多实施者并行、Web 管理台、GitLab、云队列、模型投票与自动 merge/tag/release 不进入本期。

目录中的 JSON Schema 是合同草案；Schema 只约束格式，授权、候选一致性和证据真实性必须由执行器另外检查。

## 2. 分支与当前基线依赖

本设计依赖通用基线提交 `218a6e81652d5c6e20dc8909d93dfd1b9395f58a`。设计准备时 PR #1 尚未合入 main；当前 main 为 `bd548cd21529b4e088886f32c39a98e6ecd63778`。

本次采用依赖式分支 `flow/multi-agent-orchestration`，从已存在的通用候选出发，不从带 project/ 记录的分支复制。PR 暂以 `refactor/devflower-baseline` 为 base，只显示升级设计差异。PR #1 获人工批准并合并后，核对历史再把升级 PR 改为 main；不擅自合并、不 rebase 已共享分支、不重写历史。

通用分支仅包含规则、合同、工具和测试。项目配置及运行摘要位于 project/<slug> 的 project/ 下。框架自身开发可另用 project/devflower；项目档案不能进入本 flow 分支。现有项目分支若有并发修改，不写入或重建其记录。

## 3. 控制权与最小组件

```text
用户批准的任务/权限/验收合同
              ↓
受信且版本固定的 Controller
   ├─ workspace：隔离工作副本、范围检查、候选冻结
   ├─ process supervisor：真实进程、超时、取消、恢复
   ├─ adapters：Codex / Claude 的输入输出归一化
   ├─ verifier：运行批准的测试、解释机器结果
   ├─ review gate：候选/合同/证据/阻塞项交叉检查
   └─ delivery：确定的 Git commit/push 与远端读回
```

Controller 是 Python 程序，不再添加一个负责拍板的 LLM。Codex 提供代码变更与自验说明；Claude 提供缺陷、独立验证和裁决；均不能修改授权、权威状态、交付程序或把文字 PASS 直接转换为写权限。

建议在 tools/ 下增加小型 orchestration 包，保留 tools/devflower.py 的已有 init/new/index/check 合同；路径可按实际实现微调，不先创建空目录树。标准库用于进程、SQLite 和 Git 编排；如使用 JSON Schema 校验依赖，显式固定并解释，不声称仍然零依赖。

拟议命令（尚未实现）：doctor、run、status、resume、cancel、audit、deliver。run 默认停在 READY，无交付授权则不 commit/push；deliver 不能绕过 gate。

## 4. 可信配置与权限边界

配置拆为三层：

1. 版本化通用合同：阶段、报告格式、默认安全底线。
2. 项目任务配置：目标、允许修改路径、测试命令、模型/会话偏好。
3. 本地操作员授权：实际仓库/分支/远端绑定、已批准配置哈希、允许动作、预算和有效范围；位于 Agent 不可改写的控制区，不入公开 Git。

第 2 层不能自行批准第 3 层。任务/源码/报告中的自然语言指令不能扩大权限。测试脚本内容的修改也要审查；机器测试绿色不是测试未被削弱的证明。

Agent 工作副本默认不含目标仓库可推送凭据、SSH agent socket、交付用 Git 配置和受信控制区。普通 worktree 共享 Git 元数据，不自动构成隔离；自动交付前必须验证实际边界。chmod 或“审核者只读”提示词不足以防止同 UID 进程写入。

明确两种安全状态：enforced（实际边界已验证）与 cooperative（只能遵守提示）。后者允许手动研究和候选生成，但自动 commit/push 门禁关闭。不得把无法隔离自动降级成安全自动模式。实现应复用可用沙箱或权限机制，不强制某个云平台，不擅自 sudo/关闭保护。

运行测试也视为执行项目代码：只执行获准的 argv/cwd，不用 shell=True，不让测试继承模型或 Git 凭据。模型身份认证可通过已批准的受限配置使用，不把 auth 文件、令牌或完整环境打进日志。

Controller 的版本、授权、验收规则在启动时固定。开发 DevFlower 本身时，运行旧的受信控制器/人工监督方式验证新候选，不能让待审的新 gate 批准自身。

## 5. 任务身份、候选与证据

一个运行绑定：run_id、task_id、源码仓库身份、base commit/tree、源分支、合同哈希、授权哈希、Controller 版本、适配器版本及模型/会话设置。

候选清单涵盖完整源码树：相对路径、Git mode、文件字节数和 SHA-256；删除项相对于基线单列。普通文件用原字节；符号链接记录链接文本而不是跟随到树外；submodule/LFS 首期不能可靠处理时明确拒绝，不静默漏收。build/cache 的排除规则在任务开始前批准。

禁止仅用 git diff 或 HEAD 代替完整候选。默认要求源码工作树干净；已有修改不自动 stash/reset，需先明确纳入候选或在独立副本保护。检查 staged/unstaged/untracked，禁止顺带提交旁人变更。

冻结候选后：停止写入实施者，创建只读 candidate 副本和独立可写 test artifacts 目录，复制前后核对内容；验证及审核期间内容变化则取消该候选的证据。追加新源码测试同样产生新候选并重审。

每项验证记录 run/candidate/contract、argv/cwd、退出码、机器结果、实际测试数量/失败/跳过和原始输出哈希。审核中新增临时反例可留审核区，但证据注明实际执行者。Controller 代执行的命令不能署名为 Claude 亲自执行。

报告签名式字段和哈希只是绑定，不证明判断正确。真实进程来源由 Controller 捕获；模型自填 session_id、candidate_hash 或 tests_passed 都须与外部记录交叉核对。

## 6. 状态机与恢复

正常路径：

```text
CREATED → PREFLIGHT → IMPLEMENTING → SNAPSHOTTING → VERIFYING
    → REVIEWING → GATING → READY → COMMITTING → PUSHING → COMPLETED
```

无交付授权时 READY 即本次可交付候选终点，不伪称已推送。

| 事件 | 转移/处理 |
|---|---|
| 实施/自验有可修缺陷 | 回 IMPLEMENTING，固定新候选；旧证据保留但失效 |
| Claude NEEDS_CORRECTION | 核对 findings，再回 IMPLEMENTING |
| Claude ACCEPT | 进入 GATING，不直接交付 |
| ACCEPT_WITH_LIMITATIONS | 本期不作自动交付许可；待人工处置 |
| 登录、配额、权限、测试环境、协议问题 | BLOCKED，不能替换为另一个自审 PASS |
| 明确取消 | CANCELLED，停止本任务进程组，保留工作 |
| 重启/进程消失/副作用不明 | RECOVERING，检查真实候选/进程/Git 后决定恢复点 |
| 轮数或预算耗尽 | BLOCKED，不放宽验收追求一致 |

在控制区使用一个本地 SQLite 状态库，以事务同时写当前运行状态和事件。task.json 仍是项目“任务进度/模式”元数据；运行库负责一次执行过程。运行摘要由单一写入器投影到任务，避免双向编辑同一字段。不能把几份 JSON 当成互相覆盖的状态来源。

run/task 和目标仓库各有互斥租约；租约记录 host/boot_id/PID/start identity，不只保存 PID。发现陈旧锁先确认旧执行已停止，再由受控恢复接管；不凭超时删除活锁，不 pkill 其他会话。

外部模型和 Git 操作不承诺 exactly-once。每个外部步骤先落 operation_id、预期状态和 intent，再执行并记录结果；恢复时核验副作用后重试。

## 7. Agent 适配器与会话

doctor 读取已安装 CLI 的 version/help 和受控认证状态，探测机器输出、恢复、权限和终止能力。不能假定网页最新 flag 已在本机存在。

适配器接口至少包括 probe、start、collect、cancel、resume；返回真实 session、requested/resolved model、effort（若可读）、权限模式、终态、用量及结构化结果。保持现有用户偏好，不硬编码某代模型。解析不到实际模型字段时记录 unknown，而不是把请求值写成已确认值。

Codex 可使用 exec 的 JSONL/终态输出与 schema 能力；Claude 可使用 -p 的结构输出。JSON envelope 与其中 structured_output 不能混为一谈。[S1–S4]

用户可以配置 new 或 resume-bound。默认适配现有“沿用本项目 Claude 审核会话”的习惯，但必须绑定明确 session_id、项目和角色，禁止 --last/--continue 猜测会话；禁止把 CodeWeave 的会话 UUID 写进通用模板。恢复失败按策略 BLOCKED 或经授权新建并记录，不能悄悄换模型/强度。

沿用会话仍须每轮重新核验完整候选；称为隔离角色复核，不称严格盲审。审核者不复用实施者会话。可选最终 fresh 审核属于将来的任务策略，不默认再加一个评审模型。

监督 stdout/stderr 同时读出，限制磁盘日志及缓冲，防死锁。安静不等于挂死：区分 heartbeat、无输出告警与明确步骤超时。只取消本任务已确认的进程组；关闭后如结果不完整则 BLOCKED。日志只保留必要事件、工具执行证据及最终报告，不收集或公开模型隐藏推理、认证信息、会话全文。

恢复会话的用量字段可能是累计数；按 session 和 provider 合同去重，缺失费用填 unknown。不能将多轮累计花费简单相加。[S3]

## 8. 独立审核与确定性交付门禁

最小机械条件：

```text
authorized AND controller_intact AND isolation_verified
AND implementer_success AND required_verification_passed
AND actual_review_process_succeeded AND verdict == ACCEPT
AND review_candidate == current_candidate
AND review_contract == approved_contract
AND no_open_required_findings AND source_scope_valid
AND reviewed_tree == prospective_commit_tree
AND remote_state_allowed
```

状态 complete、退出码 0、文本含 ACCEPT、格式正确的 JSON，均不能单独满足 gate。矛盾报告（ACCEPT 同时含 FAIL/BLOCKED 必需条款或未关闭 P0/P1/必需 P2）必须阻断。P3 不应机械升级为无穷修复；审核与实施有分歧时用反例证据处理，不能由实施者删掉审核意见。

测试命令和机器判据来自事先批准的合同；命令退出 0 但实际 0 tests/关键 Skip，应判失败。源码质量仍由审核判断，不承诺测试能穷尽正确性。

默认最多 5 轮审核；基础设施重试最多 2 次/步骤，不作为重新开发轮次。连续两轮同一候选哈希且相同阻塞集合没有新证据，停止循环。其他“无实质进展”不由模糊 LLM 评分自动判定。预算可由用户改；额度/账单未知不臆造价格。

## 9. Git 交付与跨仓库补偿

交付默认关闭。开启时只允许指定源码功能分支及工作流 project/<slug> 的 commit/push；main、merge、force、tag、release、删分支仍禁止。

Controller 预先记录目标远端身份、预期分支 tip、意图提交树和 parent。用显式文件清单/独立 index 准备提交，不能 git add .。目标必须是被审核的树；hooks、clean filters、attributes 等可能影响提交，需用获准策略隔离并提交后核对实际 tree，发现变化立即停，不隐式 --no-verify 绕过用户控制。

恢复 commit：先寻找并核对记录的 parent/tree/operation，若提交已存在不要重复创建。恢复 push：先读远端 tip；若已等于 intended commit 则记录成功；若与预期相同则正常快进 push；其他情况 BLOCKED，不自动 rebase/force/覆盖。推送超时属于未知状态，不直接重推再造提交。

源码与工作流没有原子推送：先提交/推送源码，成功后生成记录源码 SHA 的工作流摘要并交付；若第二步失败，标 PARTIAL_DELIVERY 并只重试未完成步骤，不回滚已成功的远端。

工作流摘要不包含它自身最终 commit SHA，避免自引用无限提交；最终两仓库回执存在本地运行记录并在用户交付回复列明。代码审核候选涵盖源码/测试/稳定文档；事后生成的工作流收据只做结构和来源检查，不能借收据名义加未经审核的代码。

## 10. 最小记录与实现顺序

公开版本化：一份任务 README、task.json、最终候选清单和精简 review/receipt；本地控制区：状态库、每轮原始裁决、关键命令输出和必要复现。界面日志/模型输出过大不入 Git。

A0：先实现状态、冻结、假 CLI 故障夹具、机械 gate、恢复；不会调用真实模型也不会推送真实仓库。

A1：接入 Codex/Claude；在自有小仓库完成一次真实“拒绝 → 修复 → ACCEPT”闭环。假 CLI 只证明控制逻辑，不能冒充真实模型验收。

A2：本地 bare remote 验证提交、推送、断线恢复和两仓库部分交付；再以单独批准的公开小任务试点真实功能分支。无需等待 Jev 或并行模式。

本期验收和开发交接见 [ACCEPTANCE.md](ACCEPTANCE.md) 与 [LOCAL_AGENT_PROMPT.md](LOCAL_AGENT_PROMPT.md)。

## 11. 技术依据（2026-10-19 核查）

以下是接口与工程机制依据，不是第三方框架已被集成的声明。版本和许可在真正复用代码前再次核验。

- [S1] OpenAI Codex 非交互模式： https://developers.openai.com/codex/noninteractive/ （当前重定向至 ChatGPT Learn）。可供脚本使用的 JSONL、结构结果和按会话恢复；不直接等于 DevFlower 门禁。
- [S2] OpenAI Codex CLI reference： https://developers.openai.com/codex/cli/reference/ 。适配层运行时探测；不使用已废弃的 flag 拼接固定命令。
- [S3] Anthropic 非交互 Claude Code： https://code.claude.com/docs/en/headless 。结构结果、session resume 及累计费用语义。
- [S4] Anthropic CLI reference： https://code.claude.com/docs/en/cli-reference 。工具允许列表、权限模式与非交互运行；plan 不是可执行所有测试的万能模式。

更早的 Spec Kit/Superpowers/OpenSpec/12-factor 取舍仍见 ../../REFERENCES.md；本期只吸收可验证的控制原则，不安装这些框架。
