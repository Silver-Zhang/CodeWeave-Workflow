# m0-code-index

任务：`20261018_02_m0-code-index`。模式、状态和版本引用以同目录 `task.json` 为准；INDEX 是生成导航，不在此复制状态表。

## 1. 目标与范围

要做什么：在自有多文件 C++ fixture 上打通 `compile_commands.json → Clang LibTooling → SQLite → JSON CLI`；以 Clang USR 关联声明/定义、重载、调用方/被调用方和精确调用位置，并保存源码快照。
不做什么：前端、监听、增量/Git 差异、RMC、GitLab、Agent/MCP、向量库、运行时 Trace 和完整动态分派求解。
完成标准：可建立持久索引，重启进程可查询；错误输入不产生空图成功或破坏旧索引；CLI 支持索引、搜索、查看、调用关系、源码片段和状态。
目标仓库、实际分支/HEAD、已有改动：CodeWeave `feat/m0-code-index` 起点 `676f63d4c8d14f23e263f43e828deae566a9b9ec`；DevFlower `project/codeweave` 起点 `a466fd5b1f00737177d07ba2c425773b3c44d379`；初始均干净，当前保留未提交改动。

## 2. 做法与证据

方案：独立 C++ LibTooling 分析器与 Python/SQLite 内核。Clang `generateUSRForDecl` 为身份；AST `CallExpr::getDirectCallee` 记录直接/虚/未知函数指针调用；源码内容与 SHA-256 同索引保存。
变化：CodeWeave 新增分析器、SQLite 核心、CLI 子命令、M0 fixture/测试与使用文档；无提交。
测试：`PYTHONPATH=backend python -m pytest backend/tests -q` → `5 passed, 1 warning`；`python -m unittest discover -s tests -p 'test_*.py' -v` → `1 passed`；`python scripts/check_repository.py` → 通过；M0 测试 `4 passed`。真实 CLI 新索引返回 `entities=11,calls=9,coverage=complete`；`overloaded(int)` 定义于 `alpha.cpp:3`，调用点在 `alpha.cpp:5`、`:7`；`entry` 的 `local` 与 `overloaded` 被调用者和快照源码均正确返回。
未覆盖：完整函数地址引用关系、跨索引比较、复杂宏/模板、全程序虚分派、逐条 Clang 诊断持久化。

## 3. 决策记录

授权：用户于 2026-10-18 明确授权 M0 实施与自验；禁止系统级安装/配置、修改 RMC、提交/推送/合并/发布和自动进入 M1。
B 变更卡：风险为 Clang ABI/开发包匹配和语义覆盖；仅改分析器、Python 内核/CLI、公开 fixture、文档与测试；以真实 fixture 精确断言、错误处理、快照和新进程查询验证；全部未提交文件均可按文件回滚。

## 4. 结论与边界

结论：M0 纵向链路已在用户级隔离 LLVM 18 工具链完成实现与自验，状态为待复核，不是用户已验收。
证据：`/home/workspace/CodeWeave_dev/.toolchain/llvm-18` 为解压的 LLVM/Clang 18 包；最小 LibTooling 程序完成 CMake 编译、链接、运行；M0 与 Bootstrap 测试通过；演示用新 SQLite，不引用旧报告。
边界：仅验证自有 fixture 与 Linux/GNU C++ 13.3/LLVM 18；未验证其他工具链、大型仓库、完整动态分派、宏模板极端案例、并发写入。
自验已完成；独立审核、用户验收、提交和推送均未完成。
下一步：独立复核当前未提交 diff 和真实 CLI 输出；由用户决定提交或后续任务。

## 5. 过程记录

| 时间 | 事件、失败及纠正 |
|---|---|
| 2026-10-18 | 建档并记录两个仓库真实分支/起点 SHA，授权进入 M0 实施。 |
| 2026-10-18 | 系统缺 Clang 开发配置；未 sudo，将匹配 LLVM 18 包解压到工作区隔离目录，最小 LibTooling 程序链接运行成功。 |
| 2026-10-18 | 测试中发现根目录、USR、子进程 Path 类型和行号预期问题；据真实输出修正，最终 M0 `4 passed`。 |
| 2026-10-18 | 完成全量测试、CLI 演示、文档和任务状态更新；保留未提交改动，标为待复核。 |
