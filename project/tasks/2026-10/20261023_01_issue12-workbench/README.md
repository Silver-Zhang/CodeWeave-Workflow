# Issue #12：工作台产品化与端到端验收

## 1. 目标与范围
任务`1c9b1656e1ed4790b029a41c9883b40d`；完整父合同SHA256 `a0b13a2cfec18273bdf5a8d0e894628cbd1f3800823ea7c82b0fc350db14eb81`。以独立worktree实施画布、统一会话、真实原生终端、typed交接和执行可视化，复用Runtime及旧可信门禁。旧任务R1–R5/BLOCKED/有限接受不改写。源码分支flow/workbench-productization，记录仅project/devflower；不改CodeWeave/RMC，不晋升Stable，不删除原生会话或历史证据。

## 2. 做法与证据
- 当前main `0a24331da65678b86448cc4a51bb2127a38cda32`，tree `e7804dc723aa09beca82be387db0f97807c84799`。PR11已合并，PR10旧Draft9399476保留；[完整增量PR13](https://github.com/Silver-Zhang/DevFlower/pull/13) 包含PR10基础，不重复分别合并。预检33个Git副本及6个历史脏副本均保护；无确认已合并且闲置的临时分支可删。
- 最终已正常提交、推送并远端读回HEAD `f57b600f3811a75e80590586d03686fb0fd1fe8e`、tree `a0c16fa6dccf9ad9fd9c7d52cd9495ada4db24d5`，完整145文件SHA256 `0e654e2a9a8e34a89b84a56dd8cf815762a17c38c9a7aecbfcf8d02ac355752b`。实际本地HEAD、快照和最新回归绑定一致；此前native预提交回执的历史HEAD1941/content0e如实保留，不重标记成新commit。3项GitHub CI在本次f57提交上均成功，不能借用1941旧绿灯。
- 同一最终源码：459 Python、6宿主隔离、129普通Chromium/HTTP（含24工作台）、6编辑器，Baseline、6语法、独立字节一致前端构建全部退出0，FAIL/ERROR/SKIP均0。原始失败另存，不改写退出码；合成负例与真实模型分列。project记录分支不适用源码`check --baseline`，该不适用失败保留，普通`check`用于记录结构核验。
- 当前源码19次完成的真实原生回合：顺序2、并发汇合3、提前退出2、五轮上限10、真实HTTP恢复1、当前可写Studio开发核验1；另2次取消启动。五轮上限明确FAILED，取消所属进程停止且下游未运行；一个取消Codex在UUID返回前已停止，标unknown/unattested，不计完成绑定。初始化一次、同SID循环、当前轮数据和汇合一次均有实际请求/回执。
- 实际HTTP中断/重启、浏览器刷新、恢复沿用同一暂停worker/run/callcount1，无重放。模型在暂停期间已完成，不声称模型进程在HTTP中断期间仍运行。两个Provider同一原生PTY均实际进入就绪、核对OS/HOME/cwd/UUID/model/effort、拒绝第二写入者，并停止非空捕获进程组，保留历史。旧Claude未就绪exit1与空进程集不算停止成功。
- 真实产品修改：Studio run2dae/session01a1669f修复插入节点与单次Undo/Redo；原生Codex01a1667f修复NativeTerminal迟到响应串用；固定旧Stable CLI监督的01a1672d修复ReactFlow丢失handleBounds/连线测量竞态（不是Studio）。首600秒未返回报告/原PIDunknown，恢复1同HOME/cwd/SID实际exit0，父监督限2路径导入。最终可写Studio run d86118c785b73b8e939728cc7cad3093/session01a1677c在独立完整f57副本运行15项真实产品测试及Baseline，全0，源码前后0e不变，不制造编辑。
- 父Codex按独立反馈修复外部绝对参数固定、条件汇合、重复边、模型准入、只读锁、恢复入口、SQLite WAL/只读查询、元数据请求洪泛。真实旧负例和独立构造反例先失败后通过。测试handler解除错误、超时、observer程序名假设、setup重试等原件均保留，未弱化断言或把工具失败算通过。

## 3. 决策记录
同一新任务最多5源码审核轮，每步最多2安全基础设施重试。源交付前子合同ae3c3555仅覆盖S01–S10，完整父合同a0b13始终不变。R4源硬ACCEPT后，实际调用未改旧Stable gate（SHA12f0b6aa）得ACCEPT，再正常push既有f57并读回GitHub PR/tree与本次CI；随后第5轮按完整父合同审核K与所有要求，不能拿源子合同ACCEPT替代整版许可。整版Gate只能在实际最终裁决后执行；main合并及Stable晋升分开。

## 4. 结论与边界
第5轮原始最终裁决 **ACCEPT**，旧可信完整父Gate **BLOCKED**。未达到技术合并条件，保留Draft，不合并main。 原报告K与I12-09为PASS，却同时保留I12-10 BLOCKED/F-GATE P1 OPEN，形成矛盾ACCEPT；旧Gate实际退出2，原因required contracts not independently passed。五轮预算已用尽，不改写报告、不排除必需合同、不追加第六轮。

R1原始BLOCKED（首次900秒无裁决、同会话恢复1后原始裁决）；R2/R3原始NEEDS_CORRECTION；R3关闭源码问题但发现N-DEV-SOURCE与N-EVIDENCE-MIX，保留原负面报告。R4源合同硬ACCEPT，明确关闭两项补证问题；源码子合同报告SHA d5c356587c663b9c2d8f1982f52356c3570a71fc001f4fb296e74339c790c70a。R5完整父合同原始ACCEPT，不能复用R4批准main。

Development入口：`python3 /home/workspace/DevFlower/.local/open-issue12-workbench.py`；原Stable入口：`python3 /home/workspace/DevFlower/.local/open-stable.py`。两个入口实际`--check`成功；原Stable5816不替换。当前允许DevFlower工作树及本任务隔离副本，其他业务仓库须另授权。部署external_steps为空，verify/delivery节点fail closed，当前Git交付由固定外部监督完成，不声称新Controller一键自批。Copilot及未验证原生删除/分叉/Skills不伪装可用。中转物理后端及实际生效effort unknown。

## 5. 过程记录
预检/独立任务→真实产品开发与R1缺陷→修复/非零测试→R2源参数修复→UI锁与洪泛修复→真实Codex测量竞态修复→冻结0e→实际原生流程/PTY/HTTP恢复→R3补证反馈→当前可写Studio核验和新提交f57同源全回归→R4源ACCEPT/旧Gate→正常push/PR/3CI→R5完整父验收。原始五轮结论、旧任务结束预算、负例及失败过程均不覆盖。

Claude请求deepseek-flash[1m]/high；Code gpt-6.1-sol/xhigh。独立审核明确SID `1d899e35-836e-49fb-a618-c8a9762af1a0`，HOME `/home/workspace/DevFlower/archives/devflower-issue12-20261023/runtime/source-r1`，配置根其`.claude`，cwd `/home/workspace/DevFlower`；原生记录`.claude/projects/-home-workspace-DevFlower/<SID>.jsonl`持久保存。恢复用原HOME/cwd/明确SID和本机原settings挂载并持同一session.lock，审核占用时不启动第二写入者，不使用--last或其他项目会话。

原始日志、截图、完整原生聊天、SQLite和私有能力仅在本机archives/devflower-issue12-20261023。入库仅本五节README、task.json及evidence-summary.json；不把认证/原始聊天/截图推送云端。
