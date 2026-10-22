# DevFlower 当前开发上下文

当前完整产品任务：tasks/2026-10/20261021_02_unified-agent-workbench。先读其README/evidence.json；原始合同及证据在本机archives/devflower-workbench-20261021，不通读旧历史。

源码development/agent-workspace-vnext / flow/agent-workspace-vnext，HEAD/origin仍465a31f523fc265b1bcbcd0ecdef6eca06a6e0e0，有本任务未提交及新增文件，禁止reset/clean/覆盖。当前130文件候选e194382a7e84b309d7d91034a5d093dee1daa10b6bda69b74be954b943bf8f3c；预期tree84070e9471b27e27135ec05df39e61764473e403。main/origin61356ac07aca24382970b72de9607b1daff26767；records/project/devflower独立。未修改CodeWeave/RMC。

最新QA candidate-8：381 Python、6宿主、113 Chromium/HTTP（7套）均通过，baseline/6项语法/diff--check退出0，零Skip。当前真实run13fc637d…6模型调用，Codex/Claude重叠57.191秒、汇合2/2、同UUID初始化一次与两轮退出；99f1293f…实际取消组/worker退出且拒绝恢复；cabd7871…5次模型达到上限，预期原始FAILED。实际原生fork/archive/restore/trash及丢真实RPC回执→RECOVERY_REQUIRED有证据；原外部读错库断言保留，以正确库补充证明，不重复原生副作用。

真实旧Stable验证run6f8e5521…读取当前完整381测试回执，1父断言，不冒充全部在Stable重跑。Studio到固定桥接verify-only四例成功/缺grant/错taskhash/失败测试+ACCEPT；未调用delivery，policy commit/push=false不能借此发布。正常源码发布必须使用固定外部机制，不能新Controller自批。所有授权、旧Stable/配置/桥接依赖固定；不签新Stable。

Claude最新授权claude-opus-5-5[1m]/high；CLI回报该模型，resolved effort及中转物理模型unknown。审核明确会话3e8c1139-9c48-4aab-ba55-ce848ebd1653，HOME本任务runtime/reviewer-round-2，cwd/home/workspace/DevFlower，原生记录持久保存。R1 DeepSeek503无裁决；R2外层中断/准确恢复超时无裁决；R3 BLOCKED缺同最终候选动态矩阵，原意见保留；R4达到1200秒监督时限后准确恢复一次，原始/最终均BLOCKED：B缺真实双Provider会话GUI，K缺实际开发—反例—修复—复审。当前已实际补齐B，以及限定fixture修复与真实外部反例测试，原Claude根据新增明确身份层级仅局部accepted=true；旧false/错误引用不可访问状态保持原样。R5同一e194原始BLOCKED：关闭R4-B/K，A–J/L PASS但全产品K仍BLOCKED；摘要对照300秒及一次准确恢复480秒均超时，无最终裁决。5轮已用尽，停止源审核；不能复用局部接受或旧465有限接受批准整版。最多5轮，不复用旧有限接受，不要求改正为ACCEPT。

本机入口python3 /home/workspace/DevFlower/.local/open-workbench.py（当前42033）。Development预览与旧Stable隔离，私有URL不发聊天/入库。旧native/storage保留，新的最终验收在本任务final-native；丢回执故障测试会话HOME保留RECOVERY_REQUIRED，不能盲重试。浏览器自动化不是用户验收。

新源码不commit/push，保留完整本地候选与35个改动路径，PR10仍Draft/旧465。记录正常同步，原始日志/截图/会话本地。只有当前完整自验、新真实硬ACCEPT、必需缺陷关闭、源/合同/tree一致、固定旧方式复核后才正常明确路径提交推送。记录可单独project/devflower同步，原始日志/截图/会话不上传，不合并main。旧任务20261021_01的五轮预算已尽及有限接受不改变。
