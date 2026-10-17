# 下一步：M0 本地结构内核

本文件是建议，不是已经批准执行的任务。先完成 DevFlower 候选审阅和仓库更名，再在 `project/codeweave` 下建 M0 档案；源码另用 CodeWeave 的独立任务分支。

## 本地 Agent 先做什么

核对两个仓库的 remote、branch、HEAD 和已有改动，阅读工作流入口与本项目 STATUS/AGENT_CONTEXT。检查 Python、CMake、C++ 编译器及匹配的 Clang/LLVM 开发库。现有源码只有 Bootstrap，不把 health 返回成功说成能解析 C++。

## 第一条纵向闭环

只围绕自有多文件 C++ fixture 打通：`compile_commands.json → Clang LibTooling → 函数/调用点事实 → SQLite → CLI`。回答“函数在哪里、谁调用它、它调用谁”，返回与快照匹配的源码范围。此阶段暂不制作网页，也不分析 RMC 全量工程。

先把下列最小验收写进同一任务 README，再取得实施授权：

- 至少两个 translation units 和共享头文件；区分重载与同名静态函数，合并声明/定义。
- 每条直接调用可定位调用点和定义；虚调用/函数指针保留解析限制，不伪造真实目标。
- 固定源内容身份、配置身份、覆盖和诊断；编译失败不能变成空图成功。
- CLI 输出受限、机器可读，可取必要源码，不倾倒全仓库。
- 测试含精确预期、错误输入与跨文件关系；记录实际命令与结果。

完成后先自验和复核 M0，再推进 M1 网页。不要把 GitLab、聊天、AI 解释或生命周期推断混入本任务。
