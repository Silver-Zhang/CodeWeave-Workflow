# 模型发现与执行准入分离

## 1. 目标与范围

按用户明确授权修复 PR #17 的 I16-A-MODEL-ADMISSION。本任务 run `77f822033450473d8b1040ab620ef4f3` 是新的修复与审核任务；原任务03及其五轮预算、NEEDS_CORRECTION、BLOCKED 保持不变。不增加 Provider/Jev，不晋升 Stable，不重写共享历史。

## 2. 做法与证据

旧审核者原始脚本真实复现：新鲜目录遗漏默认模型仍 ADMITTED。新候选只替换脚本源码根目录后 REJECTED。发现与登记均不能授予执行；显式确认后，用真实 CLI 在独立 HOME、空只读诊断目录验证精确 Provider/模型/effort/模式/Profile/权限/工具/超时/工作区/配置/环境。凭据五分钟有效，配置变化或实际失败撤销；真实成功只可续验自己持有的版本。

新独立R1原始 NEEDS_CORRECTION：原 I16-A-MODEL-ADMISSION CLOSED；独立构造 MA-05-VERIFICATION-REVOCATION-RACE，证明并发撤销可被迟到验证成功覆盖。已修复为同 check ID 且仍为 STARTING 才可发布成功；新增精确反例通过。R1固定旧Stable Gate实际exit2/BLOCKED，原始裁决不改写。

最终源码 `4ebfcd169b60e203b61d6ce7d32a0f624027c50e`，tree `2e3c444f036e6f2e02bfcddd8301a5f0b1cd8e79`，175文件完整候选 `7b0c0b3bcc95235e02eadb74b71dd5f50d3d9c88da178b4787ff2090d1978210`。同版本完整自验：547 Python、6宿主隔离、165 Chromium/HTTP、20前端单元，Baseline/六项语法/字节一致重建通过，FAIL/ERROR/SKIP=0；30项准入测试为合成负例，与真实模型结果分列。

同版本真实 Codex/Claude 诊断成功；真实顺序流程中Codex完成、Claude在300秒上限超时，FAILED且准入撤销；汇合未继续。上一候选bbdf曾完成顺序/汇合及三个真实拒绝负例，但不复用为最终版本通过证据。R2独立原始裁决 BLOCKED：I16-A、MA-01–08全部PASS，两个P1均独立CLOSED；MA-09/10因同版本真实正向流程未完成而BLOCKED。固定旧Stable Gate再次真实执行exit2/BLOCKED；Native Codex完成检查同样BLOCKED，不冒充IMPLEMENTED。

## 3. 决策记录

本轮用户授权正常commit/push及条件式PR15→PR17集成；必须同候选必需测试、独立硬ACCEPT、无必需OPEN finding及固定旧Gate通过，才能合并。SourceController不自批，外部只使用固定Stable5816/Gate12f0b6a。恢复预算2次已用尽（产品Claude验证1次、SourceR1会话恢复1次），不重放超时模型流程。R1首次900秒无原始裁决，属于进程超时，不伪称模型给出BLOCKED；同UUID/HOME明确恢复后取得NEEDS_CORRECTION。新源码复审是R2，不是旧运行第六轮或隐式重试。

## 4. 结论与边界

源码已推送PR17开发分支，Draft；main未合并、Stable不变。当前阻塞是最终候选真实Claude工作流超时、完整真实正向证据未通过；不能以自测、诊断小请求或旧候选成功替代。R2原始BLOCKED与固定Gate exit2/BLOCKED见同目录机器记录。当前无OPEN代码finding，但真实流程超时是必需验收阻塞，不能合并。物理模型后端/有效effort未由服务独立证明时为unknown。Agent操作不是用户本人体验验收。启动入口：`python3 /home/workspace/DevFlower/.local/open-model-admission-workbench.py`，已实际验证，明确Development/验收BLOCKED。

## 5. 过程记录

起点main e35dec1、PR15 546cba4、PR17 a3b22f3，所有已有源码worktree干净。新建model-admission-fix与model-admission-cas-fix工作副本；后一副本修复时前一副本及冻结审核副本不变。保留全部早期失败、原生会话、旧报告/Gate与各候选。原始日志、截图和native HOME仅在 `/home/workspace/DevFlower/archives/devflower-model-admission-20261024`；入库只留本README、机器摘要、完整源码身份及原始结构化裁决。未修改CodeWeave/RMC/全局认证，未删除worktree、会话、历史或Stable。

最终收尾：PR17 HEAD 4ebfcd1，三项CI成功，仍Draft；PR15仍Draft，未进入条件式集成。干净main已fetch/pull --ff-only，仍e35dec1/tree a0c16fa。两轮独立源码审核与两次基础设施恢复均如实保留；不额外续预算、不修改原始裁决。
