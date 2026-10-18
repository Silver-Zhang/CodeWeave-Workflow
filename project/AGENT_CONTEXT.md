# CodeWeave 接手上下文

1. 先读 STATUS.md，再读 PROJECT.md 与当前任务 §1/§3/§4。
2. 已确认：独立 Public/MIT 源码仓库；地图同时供人类与 Agent 使用，不是知识库。
3. M0 任务为 `20261018_02_m0-code-index`；2026-10-18 用户另行授权整理并同步提交，候选提交为 `abf140452b348784bba9516e079fb3a4dbc718dd`。审查问题未修复，不得合并或自动进入 M1。
4. 当前源码 `feat/m0-code-index`：任务起点 `676f63d4c8d14f23e263f43e828deae566a9b9ec`，已提交候选 `abf140452b348784bba9516e079fb3a4dbc718dd`；工作流为 `project/codeweave` @ `a466fd5b1f00737177d07ba2c425773b3c44d379`，规则候选基线 `218a6e81652d5c6e20dc8909d93dfd1b9395f58a`。
5. 本机 Python 3.12.3、CMake 3.28.3、GNU C++ 13.3.0 可用；系统未装 LLVM/Clang 开发包，但源码工作区外 `.toolchain/llvm-18` 解压包提供 clang、`ClangConfig.cmake` 与 LibTooling 库，可用于构建分析器。
6. 目标是多编译单元源码定位闭环，不是 GitLab、聊天或复杂全程序时序；健康检查成功不能代替分析器验证。
7. 只读 RMC，不改核数据、reference、冻结设计；不把内部代码公开。
8. 新会话不通读全部 tasks；按 INDEX 定位后再展开。
