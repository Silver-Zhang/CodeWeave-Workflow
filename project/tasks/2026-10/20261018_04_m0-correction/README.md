# m0-correction

任务：`20261018_04_m0-correction`。模式、状态和版本引用以同目录 `task.json` 为准；本任务不覆盖原实施记录或独立审核报告。

## 1. 目标与范围

要做什么：修复独立审核基线 `abf140452b348784bba9516e079fb3a4dbc718dd` 的 M0-R 安全、C++ 语义、索引一致性和 CLI 契约问题，保留 Clang LibTooling → Python → SQLite → JSON CLI 架构。
不做什么：前端、M1、RMC/reference/F11、Git 集成、聊天 Agent、复杂增量或无关框架；不自动 commit/push/merge/release。
完成标准：关闭本任务可复现的 P0/P1/P2/P3 缺陷；安全边界不能只依赖 `shell=False`，错误不伪造 complete，快照和物理锚点一致，CLI 错误为稳定 JSON；剩余未支持语义显式记录。
目标仓库、实际分支/HEAD、已有改动：CodeWeave `feat/m0-code-index` @ `abf140452b348784bba9516e079fb3a4dbc718dd`；DevFlower `project/codeweave` @ `6679d5bab1fe18dc111a28d4317b205bef4506d5`。修正前 CodeWeave、DevFlower 均无本轮 staged 改动；DevFlower 保留既有工作流改动。

## 2. 做法与证据

定位依据与方案：先复核报告的源码位置和现行行为，再以自有隔离 fixture 建立确定预期；分析器收集物理 FileID/缓冲区，Python 固定编译数据库与源码快照，Bubblewrap 只读挂载源/工具链并限制输出目录；SQLite 使用版本化 schema、候选索引事务和诊断表；CLI 统一 JSON 错误。
原缺陷编号—根因—修正—回归证据—状态：
- P0-01：Clang 参数可触发诊断/缓存/输出写入；根因是无参数策略和无隔离；修正为允许参数白名单、response/plugin/输出参数拒绝、Bubblewrap 封闭运行；回归为哨兵不变和副作用参数明确拒绝；状态已修正，实施者自验通过。
- P1-01：`getPresumedLoc` 路径进入 files；根因是展示路径当物理路径；修正为物理拼写 FileID/偏移、项目根验证和分析器缓冲区快照；回归 `#line` 物理锚点；状态已修正，实施者自验通过。
- P1-02/03/04：USR 内链冲突、first-wins、头文件过滤；根因是全局去重和 main-file 限制；修正为内部链接附物理文件身份、每 TU 事实、导入归并、头文件缓冲区收集；回归共享头和后见定义；状态已修正，实施者自验通过。
- P1-05/06、P2-03：函数栈/lambda/未求值/显式基类分派不完整；本轮修正未求值上下文和显式限定虚调用，方法/lambda 全覆盖仍需独立复核；状态部分修正。
- P1-07/08/09：分析后重读源码、诊断丢失、配置/重复来源缺失；修正分析器缓冲区导入、stderr 保存、版本化数据库、命令哈希、TU 记录、调用唯一约束和查询索引；状态已修正，实施者自验通过；复杂多配置诊断矩阵仍待复核。
- P2-01/02、P3-01/02：CLI 错误/源码无界、协议无版本/无索引/锚点不足/测试可跳过；修正 JSON error、行/字节预算、schema/JSONL 版本、索引、offset 和强制验收脚本；状态已修正，实施者自验通过。

## 3. 决策记录

授权原文或可核验引用、时间、允许动作与禁改范围：用户于 2026-10-18 授权本任务范围内源码修改、针对性测试和 DevFlower 记录；明确禁止自动 commit、push、merge、发布、M1，以及修改 RMC/reference/核数据库/F11。
B 变更卡：风险是安全隔离能力、Clang 18 API 和事实协议变化；仅修改 CodeWeave 实现/测试/稳定文档及 DevFlower 本任务、导航和当前状态；先测试再修复，失败保留旧索引；停止条件是安全/一致性关键问题无法验证则如实阻塞，不降低标准。
C：不适用；本轮是工程修正，不制造独立复核或用户验收记录。

## 4. 结论与边界

结论：M0-R 实施完成并通过实施者自验，状态为待复核；不代表原独立审核关闭或用户验收。
证据：Bubblewrap 实际可用；`scripts/verify_m0.sh` 在 LLVM 18 前缀下重新配置、构建分析器并执行 9 项 M0/M0-R 测试，退出 0；`pytest backend/tests -q` 为 10 passed；fixture unittest 与仓库边界检查退出 0。公共 CLI 新进程演示索引得到 `entities=11,calls=9,coverage=units_complete`，并完成 symbol、caller、callee、快照 source 查询。
适用边界、未验证部分：参数白名单故意拒绝不在 M0 明确语义范围内的编译选项；隔离依赖 Linux Bubblewrap，缺失时拒绝不可信索引。未独立验证完整模块/PCH、复杂模板、全局初始化、隐式构造析构、嵌套 lambda caller、多配置冲突选择、宏 spelling/expansion 双锚点和逐 TU 前端诊断分类；这些不应被当作已关闭。
自验、独立审核、用户验收、提交与推送：实施者自验已完成；候选已于 2026-10-18 按用户指示提交为 `d6490539f7b204351b79393633ec9b08ea6e011d` 并推送；新的独立审核与用户验收未完成。下一步只能是独立复核当前候选与剩余边界。

## 5. 过程记录

| 时间 | 事件、失败及纠正 |
|---|---|
| 2026-10-18 | 核验两个仓库、当前 HEAD 与未提交状态；确认 CodeWeave HEAD 为审核基线，未覆盖已有 DevFlower 改动。 |
| 2026-10-18 | 阅读独立审核及 reviewed-source；复核现行 analyzer/index/CLI 源码和报告缺陷入口。 |
| 2026-10-18 | 建立 M0-R 任务并记录缺陷对应表；开始 R1–R4 实施。 |
| 2026-10-18 | 实现安全参数净化、Bubblewrap 只读/网络隔离、物理锚点/缓冲区快照、SQLite v2、JSON CLI 错误和有界 source；原 M0 回归暴露并修正 `-o` 安全重写、Clang JSON 字段和沙箱工作目录映射。 |
| 2026-10-18 | 正式验收脚本重建分析器并通过 9 项 M0/M0-R 测试；后端、fixture 与仓库检查通过。任务转为待复核。 |
| 2026-10-18 | 用户另行指示整理 Git 并同步提交；M0-R 候选提交为 `d6490539f7b204351b79393633ec9b08ea6e011d` 并推送；独立复核仍未进行。 |
