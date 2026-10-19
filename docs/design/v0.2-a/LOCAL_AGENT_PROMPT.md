# 交给本地 Codex：DevFlower v0.2-A 实施与 Claude 独立复核

你是本轮实施者 Codex。任务是把 DevFlower 已确认的自动双Agent流程实现为受控程序，不是继续编写更长的Prompt。用户批准推进既定v0.2-A；范围内直接实施和测试，关键权限/范围冲突才暂停。

## 工作区和基线

源码仓库：https://github.com/Silver-Zhang/DevFlower.git
实现分支：flow/multi-agent-orchestration
依赖基线：218a6e81652d5c6e20dc8909d93dfd1b9395f58a（PR #1的通用候选）。

先检查remote/branch/HEAD及staged、unstaged、untracked，保护所有现有修改。此任务修改DevFlower框架，不切换或占用现有project/codeweave目录；使用独立clone/工作目录。不要从旧Bootstrap式main开始覆盖，也不要把project/codeweave整分支合回。

PR #1若未合并，继续既有依赖分支，不擅自merge。若已合并，核对继承关系后报告，不重写共享历史。读取AGENTS.md、WORKFLOW.md及本目录README/ACCEPTANCE和相邻schemas。当前JSON只是设计合同，不能声称运行器已有实现。

框架自己的任务档案放独立project/devflower实例；已存在则接续，否则在独立工作流clone从通用候选创建project/devflower，并用现有工具建立B模式v02a-orchestrator任务。flow分支不放project/历史记录，不修改CodeWeave源码或RMC。

## 实施顺序

1. 运行旧基线回归和check --baseline，记录真实环境与既有失败。探测Python/Git、Codex/Claude的version/help/auth能力，不暴露凭据，不擅自sudo/修改系统或更换模型。
2. A0：确定性状态库、候选冻结、授权/验收合同哈希、机械gate、进程监督和模拟适配器故障测试。现有init/new/index/check保持兼容。
3. A1：实际Codex和Claude CLI适配器，按明确session恢复，保持用户本地已批准的模型/effort。首个真实闭环使用自有小fixture；模拟CLI不等于真实模型验收。
4. A2：仅对本地bare remotes测commit/push、超时读回、远端竞争和源码/记录分仓部分交付。没有独立授权，不把产品自动交付功能指向真实业务仓库。

全部按README及A01–A16判断，不擅自降低合同，不扩展Jev、并行Agent、GitLab、聊天系统、云调度或自动merge。可按职责拆分模块；不要单文件堆全部，也不要先搭企业级框架。

## 关键实施约束

- Controller固定并独立于Agent；Agent不能写权威运行状态、授权和交付凭据。
- 同一任务一个源码写入者，审核读取固定副本，测试产物在隔离可写目录。
- 状态与事件用事务保存，断点恢复先核验真实进程/候选/Git状态。
- 输出格式正确、退出0、Agent说PASS都不够；测试数量/Skip、候选、合同、真实会话与未关缺陷一并核对。
- 私有源码送外部服务需独立授权。日志不保存模型隐藏推理、令牌或会话全文。
- 合作式提示词保护不等于强制隔离；不能验证保护时自动交付必须关闭。
- 本轮在开发新Controller，不能让这个未审新Controller批准自身并推送自己。

## Claude审核与循环

沿用已批准的“Codex实施、Claude审核、修复、复审”启动方式作为本次自举；待开发的Controller是被测对象，不是自身验收裁判。

真实检查Claude CLI及认证，使用用户已经批准、明确绑定DevFlower本项目/审核角色的会话，或按配置新建；不得把CodeWeave会话UUID直接套到本项目，也不能使用--last自动猜测。保持已批准的模型/effort，取不到实际信息如实标unknown，不硬编码旧型号。

每轮固定候选和合同哈希，捕获真实进程/退出/原始裁决。Claude在独立区先看合同、代码与真实证据，再对照实施说明；必须独立构造A01–A16代表性负例，特别测试“ACCEPT但测试失败”“审核后代码变”“push成功后回执丢失”“两库只推成功一库”。

若Claude权限模式不允许必要测试，不伪称完成：独立设计命令可由受控runner执行，记录实际执行者，再交Claude判断；没有足够关键动态证据则BLOCKED。

NEEDS_CORRECTION回修复；新候选必须重验重审。最多5轮，连续2轮同候选/同阻塞无新证据或服务不可用则停，不逼迫模型改为ACCEPT。保留各轮结论原意，不改写负面报告。

## Git交付授权边界

只有当前候选完整自验通过、真实Claude ACCEPT、无未关必需缺陷、源码/合同与被审哈希一致，并由固定旧方式重新检查后，本轮可以沿用用户批准的自动commit/push：
- DevFlower实现仅flow/multi-agent-orchestration；
- 框架研发记录仅独立project/devflower；
- 按明确路径暂存，提交后核对tree与被审源码，正常push并读回；
- 不merge main，不push project/codeweave，不tag/release/force/delete；
- 两分支/仓库操作部分成功必须据实报告，不能回滚已成功远端或伪称原子交付。

真实业务试点及新Controller未来每个任务的自动交付仍需独立授权记录；本提示词不能充当所有任务的永久许可。

最终交付：实际已实现命令、A0/A1/A2完成情况、真实模型及故障测试证据、Claude各轮原始结论、候选哈希、各分支commit/push状态、剩余限制。原始大日志留本地，一任务一份五节README和必要机器记录。完成v0.2-A后停止，不自动进入v0.2-B或CodeWeave下一阶段。
