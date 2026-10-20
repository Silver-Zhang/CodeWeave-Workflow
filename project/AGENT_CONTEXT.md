# CodeWeave 接手上下文

1. 用户授权完整M2-A实施、自验、独立复核和同候选ACCEPT后的源码/工作流Git交付。当前任务[m2-usable-beta](tasks/2026-10/20261020_02_m2-usable-beta/README.md)已完成；不是R0设计或只读审核任务。
2. 源码base/main=95620d8da6afb8470d78400468fc4eee120147f2，结果feat/m2-usable-beta=7e1e0750de0c4259c961649804ba1907640fbbe2，已正常推送/远端SHA核验，[PR#3](https://github.com/Silver-Zhang/CodeWeave/pull/3) open/unmerged。DevFlower项目分支base4ae77c6a351cf9430f79bc10dd75f421ab37a227，本任务与导航随本提交归档。
3. 已实现protocol3锚点、schema4完整快照、封存头/ELF沙箱、全量刷新/CAS事务、raw Git HEAD、保守结构Diff、共享CLI/API、React Flow/Monaco双侧源码、本地启动器和自有多TU演示。工作流/LLM不是产品运行依赖。
4. 最终84文件清单40328a84bf1e27948e17d1916ebfd3489a2bc3c4fadadc4560e889703c4a7c95；暂存/提交tree=e3a7cec6f5e4280c67d2065974a0e66d5360ab71逐文件字节/模式完全匹配。接受后没有改源文件或测试/稳定文档；审后只做Git与归档。
5. 原CodeWeave独立审核会话06fd5ee6-78e4-4dbd-ac8c-d442e9c97cb6；用户更换中转站后明确授权api.deepseek.com、DeepSeek Flash/max/auto。旧ae00首次正式NEEDS CORRECTION在review/round-1；新候选正式review/round-2为真实ACCEPT，原生最终exit0/is_error=false，P1/P2/P3 CLOSED。先前中断/超时及harness错误均保留，不能当成功或新独立轮次。
6. Codex与审核者各自verify_m2.sh新构建136后端、fixture1、38前端、7M1+2M2真实Chromium通过，零Skip；另有自拟多TU/读集/预算/UTF8/DB损坏/浏览器证据。原始大日志在本地m2-usable-beta-20261020及/tmp，入库仅必要报告/清单/记录。安全fixture必须在/tmp，workspace内会被VS Code自动Git监控污染；既有失败父链/strace保留。
7. 演示真实服务http://127.0.0.1:8000。CodeWeave源码根目录执行scripts/run_local.sh --demo --state-dir <owned-state>；演示复制到state/demo-project，重启不覆盖编辑。编辑main.cpp的literal7→9和choose alpha→beta，保存后网页刷新/published/比较/源码Diff。自有项目用新state、显式project-root/compilation-database；不运行导入项目构建。
8. 非阻塞限制N1观察TU正读集并集可能过报，N2同定义文件外部常量可能仅文件/源码Diff；不证明行为等价。只做全量重新分析，无M2-B、watcher、未保存缓冲、任意历史构建/PCH/modules/完整隐式生命周期或全程序分派，未访问真实私有项目。
9. 用户验收尚待亲自试用；未自动冻结/合并main、tag、release或进入M2-B。后续任何修正须新候选/针对回归/独立复核，不复用本轮ACCEPT。
10. HTTPS remote保持原样；Git交付仅per-command SSH URL rewrite、BatchMode/StrictHostKeyChecking/ForwardAgent=no，无force/reset/clean/stash。现有Python3.12/LLVM18.1.3/Node22/Bwrap0.9/Chromium；稳定安装说明见源码README，不依赖本机隐藏目录。
