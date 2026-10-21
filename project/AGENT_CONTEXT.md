# DevFlower 当前开发上下文

当前 Issue #9 为 Draft 已发布、最终验收待决策。任务 tasks/2026-10/20261021_01_agent-workspace-vnext；五节 README 与 evidence.json 汇总结论，原始证据仅本地 archives/devflower-vnext-20261021，不通读历史。

main 基线 61356ac07aca24382970b72de9607b1daff26767 / tree 10a19a6d8fe34633ffbc667a33ac518eb7f248dd。源码 worktree development/agent-workspace-vnext，flow/agent-workspace-vnext 提交 465a31f523fc265b1bcbcd0ecdef6eca06a6e0e0 已推送读回，候选 74c7c3d8776a9736556850b632274afe7118e693e70126dd5e2b028d9213704e / tree 087d124f2259b7562e5abfec3d4e9bbda533c16e。Draft PR #10 https://github.com/Silver-Zhang/DevFlower/pull/10 ，未合并。研发记录仅 records 的 project/devflower，不整分支合回 main。

Claude deepseek-flash[1m]/high，实际模型同名、resolved effort unknown；Codex gpt-6.1-sol/xhigh。真实 run f3b645cedd914b9285f8284fbbc738bd 固定旧 Stable 5816 监督，已停止 BLOCKED。main 准入 1 轮 + 开发 4 轮总预算已尽；开发 R1/R2 NEEDS_CORRECTION，R3/R4 ACCEPT_WITH_LIMITATIONS，F1/F2/F3 CLOSED、20 合同 PASS。323 Python+6 隔离+18 固定断言通过，真实原生/API16及普通 Chromium9；实际 Development 另有4原生回合与9浏览器检查。原始失败、裁决与执行者区别保留。

2026-10-21 用户明确批准按当前有限接受提交/推送/Draft PR 和记录同步，使用外部正常 Git 操作；没有恢复旧 run、改变硬 ACCEPT gate 或自签 Stable。首次 HTTPS 推送缺 workflow scope 被拒，后以本机既有 SSH 正常推送；未修改全局认证或远端配置。旧授权基线 d971 与新已提交候选不同，不能直接复用其 resume。

旧 Stable 33915 与用户 34235 保留。Development 会话预览 41053 启动：python3 /home/workspace/DevFlower/archives/devflower-vnext-20261021/real-workspace-acceptance/open-studio.py 。支持真实历史查看、managed 新建/精确续聊；外部导入/多 cwd 只读。原生 archive/delete、任意并行 DAG/子 Agent、Copilot、远程 URI unsupported。Controller/GitHub/Stable 批准 API 禁用；私有 URL/token 不入库或聊天，不复制整个 HOME。

新 RC 均为不可执行晋升提案 approved=false。额外严格服务浏览器试验失败未改写为 PASS；尚无独立真人 GUI 最终验收或新 Stable 晋升。不得把 Draft 等同 READY_TO_MERGE，不自动合并/force/tag/release/删除远端分支。

按用户授权删除4个本地旧flow分支，全部可从main到达；当前仅main、flow/agent-workspace-vnext、project/devflower，3个worktree保留，原生会话/历史证据不删。不reset/clean，不改CodeWeave/RMC。后续审阅Draft和限制后另行决定正式准入，当前不自动进入下一阶段。
