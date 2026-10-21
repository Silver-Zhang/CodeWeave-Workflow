# DevFlower 当前开发上下文

当前新任务：tasks/2026-10/20261021_02_unified-agent-workbench，依据2026-10-21完整产品升级卡，状态BLOCKED。先读本README与evidence.json，不通读旧历史。原始任务卡、源码冻结、日志、截图、实际会话在本机archives/devflower-workbench-20261021。

工作树：development/agent-workspace-vnext（flow/agent-workspace-vnext），HEAD与origin仍465a31f523fc265b1bcbcd0ecdef6eca06a6e0e0；有本任务完整staged=0的未提交修改及新增文件，禁止reset/clean/覆盖。最终本地候选b1b2cfdf90a16e6347566f2e9123afb5648a46b785effa1dc59ce7e84aab1e11，127文件，预期Git tree d7528dd0915895ddd1c121e50cf81c40b3518b5e（不是HEAD tree）。main/origin最新仍61356ac07aca24382970b72de9607b1daff26767。三个worktree/分支保留，不擅自清理。

当前候选自验：363 Python+6宿主隔离+110普通Chromium检查（7套件，含32会话断言），全退出0/零失败零Skip；check --baseline及6项语法通过。40新增协议测试含在363内。真实Codex gpt-6.1-sol/xhigh成功21回合；并发重叠81.774秒，汇合2/2仅汇总一次；两轮提前退出及五轮10调用终止；精确UUID跨轮与旧会话新运行初始化通过。各原生运行具有自己的候选身份，不把旧动态证据当成最终源码ACCEPT。

Claude保持deepseek-flash[1m]/high。分析进程和固定外部源码审核均真实503 no available channel；源码审核PID3594968/session140b1101-df30-4b88-a8cc-6547cdb865d1，192.866秒/exit1/no timeout。resolved model/effort unknown，无源码裁决；外部监督BLOCKED。原生HOME/config/cwd/恢复资料见reviews/round-1/session.json（本地），不复制全局HOME或认证。本新任务启动过1次源码审核，完成裁决0；不继续无界重试。

未关闭：WB-UI-01冻结运行高级预算显示草稿24而实际冻结/执行10；WB-EXT-01无可信实际验证/交付profile；真实v3原生停止未补测；跨Provider分析、开发—Claude修复复审和最终独立审核仍缺。源码未commit/push，PR10保持Draft及旧465内容。记录允许正常project/devflower同步，原始会话、日志、截图不上传。当前不能声称READY、用户验收或Stable晋升。

本机唯一新版入口：python3 /home/workspace/DevFlower/.local/open-workbench.py，当前产品http://127.0.0.1:42571/，明确Development；私有URL/token不入库或聊天。旧34235、33915 Stable及41053旧会话预览保留；不覆盖当前Stable。源码使用React Flow，前端依赖缓存只在本机archive/ui/node_modules，静态构建与许可证在源码，不向CodeWeave/RMC写入。

旧任务20261021_01_agent-workspace-vnext原五轮预算已尽、运行f3b645…BLOCKED；其R1/R2 NEEDS_CORRECTION、R3/R4 ACCEPT_WITH_LIMITATIONS及用户明确批准的465a31f/088832b Draft发布保持原意。不得恢复旧运行或借其有限接受批准本次新源码。新任务恢复需实际新证据，先修未关项、固定候选、自验并真实Claude复审；main合并与Stable最终批准仍由用户另行决定。
