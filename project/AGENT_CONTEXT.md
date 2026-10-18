# CodeWeave 接手上下文

1. 先读 STATUS.md，再读 PROJECT.md 与当前任务 §1/§3/§4。
2. 已确认：独立 Public/MIT 源码仓库；地图同时供人类与 Agent 使用，不是知识库。
3. M0 任务为 `20261018_02_m0-code-index`；M0-R 修正任务为 `20261018_04_m0-correction`，已获 2026-10-18 用户修复与自验授权。M0-R 当前待复核，不得宣称独立审核关闭、用户验收或自动进入 M1。
4. 当前源码 `feat/m0-code-index`：修正基线 `abf140452b348784bba9516e079fb3a4dbc718dd`，M0-R 候选提交 `d6490539f7b204351b79393633ec9b08ea6e011d`；工作流为 `project/codeweave` @ `6679d5bab1fe18dc111a28d4317b205bef4506d5`。原独立审核报告和实施记录保持不改。
5. 本机 Python 3.12.3、CMake 3.28.3、GNU C++ 13.3.0 可用；系统未装 LLVM/Clang 开发包，但源码工作区外 `.toolchain/llvm-18` 解压包提供 clang、`ClangConfig.cmake` 与 LibTooling 库，可用于构建分析器。
6. 目标是多编译单元源码定位闭环，不是 GitLab、聊天或复杂全程序时序；健康检查成功不能代替分析器验证。
7. 只读 RMC，不改核数据、reference、冻结设计；不把内部代码公开。
8. 新会话不通读全部 tasks；按 INDEX 定位后再展开。
