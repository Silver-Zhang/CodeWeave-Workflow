# M2-R0 — Workspace Snapshot, Incremental Indexing & Semantic Diff Architecture

## 1. 目标与范围

B模式。本轮只整理M0/M1主线PR并交付M2架构/实施合同；**不实现M2-A/B生产功能，不合并main、tag、发布或替用户冻结**。RMC/F11/reference/真实私有项目未访问。技术设计最终结论：**ACCEPT，可进入M2-A实施；实施与用户冻结另行决定。**

开工身份：CodeWeave `feat/m1-interactive-map` HEAD `6c3d1b8cf9c2ff3257c92840dd8531dcc1cceed7`，DevFlower `project/codeweave` HEAD `39f4ae9de970106adf060a5af54ac0f850a99394`，两仓库staged/unstaged/untracked均空。remote分别为Silver-Zhang/CodeWeave.git、Silver-Zhang/DevFlower.git（HTTPS）。实查远端main `676f63d4c8d14f23e263f43e828deae566a9b9ec`、M0 `0e9c093a5a2456814c5543ec1e52089035b4bc2e`，M1/工作流远端与上述HEAD相同。

## 2. 做法与证据

### M0/M1当前版本与PR

`git merge-base --is-ancestor 0e9c093... 6c3d1b8...` exit0，M1继承M0。M0历史34文件SHA256与M0提交相等；M1-Final接受62文件的bytes/mode与M1提交相等。历史报告只用于身份/边界核对，不代替本次运行。

| 当前独立导出、新构建命令 | 本轮实际结果 |
|---|---|
| M0副本 `bash scripts/verify_m0.sh` | exit0；87 passed，0 failure/error/Skip |
| M1副本 `bash scripts/verify_m1.sh` | exit0；110后端+fixture unittest1、35前端、7真实Chromium，0 failure/error/Skip |

环境：Python3.12.3、LLVM/Clang18.1.3、Bubblewrap0.9.0、Node22.23.3；新分析器SHA256 `8562b0369cf35e6affdefe011cc83a8e65cb6e7527fa0a0649de18ab15014e94`。真实Clang/Bubblewrap/CLI/HTTP/Chromium已执行，未用旧binary或全部Skip。Starlette弃用、Monaco包大小及颜色环境提示保留，不作失败或隐藏。

[M0 PR #1](https://github.com/Silver-Zhang/CodeWeave/pull/1)：M0→main；[M1 PR #2](https://github.com/Silver-Zhang/CodeWeave/pull/2)：M1→M0，仅显示M1差异。创建后再次实际查询均open、mergeable=true、merged=false；GitHub测试merge SHA不是正式合并。M0正式合入后才将M1目标改main；本轮未合并/重写历史/删除分支。

### 完整设计与研究证据

[架构](architecture.md)定义身份、sealed输入向量、全量刷新、单schema4事务、失败状态、TU失效、Diff、共享API/安全、A1–A6/B1–B3路线；[验收合同](acceptance.md)给22组预先oracle与C/D/L/H/B层；[双方案决定](decisions.md)记录具体分歧/反例/取舍；[摘要](research-evidence.json)区分实际运行与未来实现合同。

自有两TU临时工程，先定义期待，再运行真实公共CLI和新分析器：宏/共享头read-set、缺失可选头新增在.cpp不变时one→two、仅移动行号保持关系而instance_id全变、换根改变static身份、旧index仍返回原字节并可重新启动查询，五项PASS。[最小复现脚本](research_probe.py)参数化后在全新目录又跑通：`<venv-python> research_probe.py --source-root <M1副本> --work <新目录> --analyzer <新binary> --resource-dir <Clang资源目录>`。

另两个owned Bubblewrap可行性探针exit0：sealed副本挂到原虚拟路径，host改宏后仍读旧目标/稳定内部身份；仅精确runtime ELF文件与复制头树、无live `/usr`广泛挂载时，`vector/cstddef`正例成功，未挂载owned绝对头文件负例exit1/file-not-found、哨兵未读且不变。**不是descriptor安全capture、完整alias/系统冻结或M2实现安全验收。**

### Claude独立设计、两轮审核与完整身份

用户最新设置明确为**Claude Opus5/high**，沿用`CodeWeave独立审核` UUID `06fd5ee6-78e4-4dbd-ac8c-d442e9c97cb6`、auto。真实model probe及每次native init/argv确认`claude-opus-5`/high/auto。

先写Codex初稿，再让Claude只读源码/需求独立形成[原方案](claude-independent-design.md)；完成前工具规则和prompt禁止其读Codex完整结论/当前任务。随后才提供方案对比。

| 正式轮次 | 独立结论 | 本任务处理 |
|---|---|---|
| [第1轮](review/round-1/report.md) | ACCEPT，但implementation_ready=false | 不作为最终交付关口；补齐五项规范，保留原文和[对比](review/round-1/comparison.md) |
| [第2轮完整v2](review/round-2/report.md) | ACCEPT，implementation_ready=true，无阻塞 | 原样[对比](review/round-2/comparison.md)/[机器结果](review/round-2/result.json)；补读第五份脚本并独立结束身份复核后再次确认 |

当前完整候选：[candidate-manifest.json](candidate-manifest.json)，raw SHA256 **`3e546ddd151ba17df2500ed930e0e2149f1ea314680651efc7124b7d075deb1b`**，5份技术设计/复现文件+62份源码，结束时原工作区/独立副本/固定文档bytes、source mode一致，源码HEAD和干净状态未变。操作README/导航/审核结果是归档记录，不混作新增技术合同。v1固定副本留本地；[v1→v2补丁](review/v1-to-v2.patch)反向重建3份旧设计文件的SHA全部与v1清单相等。

第1轮首次print在Write未完成参数中持续重复空白，被监督SIGINT；exit0但native is_error=true且无裁决，**不计PASS**。恢复同候选/模型/high，仅移除输出JSONSchema格式约束，auto未关闭。首轮身份检查另有工作目录拼错造成的harness失败，随后的正确路径核验通过，未计产品缺陷。第2轮首次报告声称全读5份，但记录仅展示4份语义读取及第5份哈希；监督要求补读研究脚本、重新核对结束身份，Claude自行更正并再次确认ACCEPT。两轮原报告未由Codex改写；[执行来源](review/provenance.json)记录完成/失败尝试和确切范围。

原始argv/exit/stdout/stderr、fixture/数据库、新构建、模型原始流仅在本地`m2-workspace-architecture-20261020/`：baseline-identity/results、m0/m1-regression.log、research-commands/results、mount/minimal-view probe、independent、round-1/attempt-1、round-2/before-supplement等。原始推理/大日志/构建物不入Git。定向key/token/构建物扫描、diff检查及DevFlower结构检查通过；结构检查不等于技术批准。

## 3. 决策记录

本轮用户授权实际研究、PR创建更新、Claude独立设计及最多5轮正式审查、双方同完整候选通过后指定项目/开发分支Commit+Push；最终明确禁止自动main合并、M2生产实现、tag和发布。最新Opus5/high覆盖旧5.5/xhigh，不沿用旧审核裁决。B模式按此授权执行，无伪造人拍板或重复许可。

变更卡：只改DevFlower新任务和必要导航，CodeWeave源码/测试/已验收事实不变。设计选择完整不可变索引+单库schema4，避免独立catalog/事实文件多方发布；sealed向量不冒充全局瞬时磁盘；namespace结构变化先全量失效；semantic relation独立于位置，重复site不猜配对。第一轮对Codex单库、封存后修改的两处误述在第二轮由Claude更正，保留旧原文。

未来M2-A按A1–A6全量正确闭环；M2-B仅在A独立通过后按B1–B3复用TU/全量shadow对照。无watcher、delta事实层或新通用仓库框架。出现安全/身份/快照/删除误报/输出预算失败时不得验收；旧schema3保留作为部署回退，未授权项目命令始终不执行。

## 4. 结论与边界

**M2-R0设计ACCEPT，建议用户冻结该设计并安排M2-A实施。** 没有未关闭设计阻塞。CodeWeave仍为M1 `6c3d1b8...`，本轮未新增生产能力。用户正式冻结/使用验收、M0/M1 main合并、M2-A实现均未发生。

限制：普通FS采集不证明任意多文件同一瞬间；project/dependency symlink初版明确受限，trusted toolchain alias须验证；历史HEAD缺生成输入/ccdb可能只阻塞该比较侧；复杂PCH/modules/全程序虚分派不在范围；call配对不唯一必须unknown/ambiguous；B初始shadow全量有额外成本，不宣称端到端加速。具体风险是后续必测实施合同，不能用此设计ACCEPT冒充实现PASS。

实施者当前原语/回归自验、Claude独立方案/设计审核、用户验收、Git交付分开。项目分支交付由同候选关口控制；精确结果Commit及远端核对见交付消息/Git引用，不以文档仓库SHA冒充源码SHA。本轮到设计交付为止，不自动进入M2-A。

## 5. 过程记录

| 日期 | 事件、失败及纠正 |
|---|---|
| 2026-10-20 | 核对两仓库/远端/完整工作区，读规则/产品基线/当前实现/历史审核，建立B任务。 |
| 2026-10-20 | 独立导出M0/M1，新构建当前回归通过，创建并二次核对两层待合并PR。 |
| 2026-10-20 | 先定义oracle，再执行5项CLI研究、2项最小视图原型；Codex v1先完成，Claude后独立设计。 |
| 2026-10-20 | 第1轮格式失效保留，恢复后ACCEPT但未ready；Codex自审/对比形成v2五规范，未复用旧裁决。 |
| 2026-10-20 | 第2轮完整v2 ACCEPT/ready；补读第五脚本并结束身份复核后再次确认；归档原文、版本补丁与候选清单。 |
| 2026-10-20 | 归档版本补丁的空白上下文触发Git staged diff检查；改等价无上下文补丁，fuzz=0反向重建原hash后通过，不改接受设计。按授权整理项目分支交付，不改源码/合并main/启动M2-A。 |
