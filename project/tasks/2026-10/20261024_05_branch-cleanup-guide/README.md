# 分支整理、操作指南与研发记录能力核验

任务：`20261024_05_branch-cleanup-guide`。本任务的“已完成”只指分支整理和指南，不表示 PR #17 或软件正式验收通过。

## 1. 目标与范围

用户要求清理旧分支、保留最终开发版本和 project 分支，编写可实际使用的操作指南，并核实最初按时间记录研发过程的功能是否保留。随后用户表达“我认为可以合并了”，本任务记录该合并意向并复核原有合并条件。

范围仅限仓库引用整理、只读能力核验、文档和项目档案。保护全部源码工作树、原生会话、运行数据库、认证、Stable 和历史负面审核；不重新启动已结束任务的模型调用或审核预算，不扩展产品功能。

整理前全部 11 个源码工作树均干净，records 亦干净；建档后 records 的新增变动均属于本任务。main 为 `e35dec13825ecbce39ae4092c3d94a059bc732b8`，最终开发源码 `4ebfcd169b60e203b61d6ce7d32a0f624027c50e`，tree `2e3c444f036e6f2e02bfcddd8301a5f0b1cd8e79`。

## 2. 做法与证据

- 重新 fetch，读取全部本地/远端分支、12 个 worktree 的 HEAD 与 staged/unstaged/untracked 状态、GitHub PR 状态/依赖/CI，逐项判断祖先关系。
- 删除前将全部本地与 remote-tracking 分支打成 Git bundle，真实执行 bundle verify。原始清单、操作输出、备份和核验留在本地 `archives/devflower-branch-cleanup-20261024`；必要摘要见同目录 `cleanup.json`。
- 删除9个冗余本地分支引用，把最终开发工作树的分支名称统一为 `flow/model-session-routing`，把PR15已审工作树的分支名称统一为 `flow/workbench-ux-polish`。旧工作树仅脱离活动分支，文件、提交和目录均保留。
- 以正常远端原子删除操作移除已合并的 flow/agent-workspace-vnext、flow/review-handoff、flow/workbench-canvas-stability、flow/workbench-productization；删除前即时确认远端SHA、已进入main且不是开放PR的head/base，删除后读回全部远端heads。
- 本地保留main、最终开发、PR15依赖和project/devflower；远端另保留project/codeweave。PR17仍依赖PR15，不能把依赖分支当冗余分支删掉。
- 交付本机[使用指南](使用指南.md)，覆盖打开目录、模型执行验证、会话、画布、实际请求/交接、生命周期、研发归档、运行限制及版本区别。依据是实际源码、部署配置、数据库表和真实服务响应，未编造新的人工界面验收。
- 实际检查Development启动器、源码baseline、records结构和Git bundle；Development成功。旧Stable启动器实际失败，其服务HTTP400原因为 `Approved executable or native configuration changed`。没有修改Stable及批准配置来绕过它。

本轮没有应用源码修改，因此不将旧任务547 Python/6host/165browser等结果声称为本轮重跑；前次候选测试及失败运行仍在任务04。没有新Claude调用、新独立审核或旧裁决变更。

## 3. 决策记录

授权来自本次用户“清理branch，保留最终的开发版本，其余的branch清理干净”和明确保留project分支的要求；后续“我认为可以合并了”记录为合并意向。仓库规则要求保护会话/历史及有条件合并，未从这句话推导出豁免必需合同。

主要风险是删到未保留的源码、开放PR依赖或原生历史所需目录。采用整仓refs备份、逐项祖先核验、保留活动依赖、不删worktree、不动源文件的方式整理。没有reset/clean/force-push，没有创建恢复分支或覆盖现有文件。

最终开发4eb完整包含被清理的旧开发提交；远端删除项全部已经合入main。需要恢复引用时先查本地before.json和bundle，在独立恢复目录处理。项目记录历史保留，不把project分支合回main。

## 4. 结论与边界

整理和指南已完成。原项目台账功能仍保留：new/index/check、日期任务目录、五节README、task.json、INDEX、Git历史。Studio另有持久化运行事件、冻结草稿、交接/请求和原生会话。但通用的“Studio运行完成→自动生成可审阅项目档案→隐私核验→同步project分支”尚未实现；当前Development外部验证/交付配置为空。不能把本地SQLite持久化说成云端研发归档已完成。

重新读取PR15/17，二者仍Draft，各三项CI成功。PR17最新4eb原始独立审核仍BLOCKED，I16-A与MA-05 P1均CLOSED，但MA-09真实顺序Claude300秒超时、汇合未运行；MA-10固定Gate实际exit2/BLOCKED。没有新通过证据，故本次未合并，main未变化。PR15旧硬ACCEPT不用于批准PR17，也不擅自改变原有两者全部通过后依次集成的条件。

Development实际入口：`python3 /home/workspace/DevFlower/.local/open-model-admission-workbench.py`。源码候选哈希仍 `7b0c0b3bcc95235e02eadb74b71dd5f50d3d9c88da178b4787ff2090d1978210`，没有因写指南而变成另一个源码候选。Stable源码保持原版本，启动配置失配另待核验，未晋升。

文档自验、此前源码独立审核、用户本人体验验收和Git推送分别记录。本次用户未亲自进行软件可用性验收，没有宣称正式技术验收成功。档案提交/推送及远端读回以本任务本地收尾回执为准。

## 5. 过程记录

| 时间 | 事件、失败及纠正 |
|---|---|
| 2026-10-24 | 读取仓库规则、当前记录入口及分支/工作树；确认源码均干净，所有待清理源码提交由最终开发或main保留。 |
| 2026-10-24 | 用户表达同意合并；重新读取PR CI、原始Claude裁决及固定Gate，仍BLOCKED，保留两PR Draft。 |
| 2026-10-24 | 创建并验证bundle；清理9本地旧引用、统一2活动分支名、正常删除4已合并远端分支并读回。12工作树原HEAD均不变。 |
| 2026-10-24 | 最新Development启动器通过；旧Stable入口失败，定位HTTP400为已批准依赖/配置变化，未重写信任pin。 |
| 2026-10-24 | 完成使用指南、记录能力边界和后续建议，更新任务元数据与导航，进行结构/完整性核验。 |
