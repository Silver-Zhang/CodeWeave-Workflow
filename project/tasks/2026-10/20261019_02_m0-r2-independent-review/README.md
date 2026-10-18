# M0-R2 独立审核

任务：`20261019_02_m0-r2-independent-review`。本记录是独立审核，不重写 M0-R2 实施者报告。

## 1. 目标与范围

**裁决：ACCEPT。建议可以冻结 M0，仍须由用户作冻结/提交/合并决定。**

审核对象是完整的未提交候选，而不是仅 `HEAD`：CodeWeave `feat/m0-code-index` @ `d6490539f7b204351b79393633ec9b08ea6e011d`，无 staged，8 个 unstaged 修改与 2 个 untracked 测试文件；候选共 33 个文件，清单 SHA-256 为 `290550ef33cfd58b3cbce4b93347388edef793218c4546cd91b40268fb8022c1`。remote 为 `https://github.com/Silver-Zhang/CodeWeave.git`。DevFlower 为 `project/codeweave` @ `3ac33b8e27d971017a4dda93ded170d0b8a958fa`，含实施任务和导航的未提交记录。

审核开始前实施者已停止写入。审核者把完整 CodeWeave 候选复制至本地只读审查副本 `/home/workspace/CodeWeave_dev/m0-r2-independent-review-20261019/candidate`，并在结束后重新核对：源候选 33 文件的清单哈希仍为上述值，副本逐文件 SHA-256 无变化。未修改 CodeWeave 原目录、原测试、基准或既有报告；未访问 RMC、核数据库、reference 或真实私有数据；未 commit、push、merge、reset、clean、发布或启动 M1。

## 2. 做法与证据

### 环境与独立构建

- Python 3.12.3、CMake 3.28.3、GNU C++ 13.3、LLVM/Clang 18.1.3、Bubblewrap 0.9.0。
- 使用副本、全新目录 CMake 构建分析器；二进制 SHA-256：`8562b0369cf35e6affdefe011cc83a8e65cb6e7527fa0a0649de18ab15014e94`。
- 使用候选的公开验收入口重新构建并执行：`55 passed, 0 failed/errors/skipped`；再直接执行完整 backend 测试：`56 passed`（仅 1 条既有 Starlette/httpx 弃用 warning）。
- `--resource-dir` 的合同是 Clang 版本目录（例如 `.../lib/clang/18`），而非其 `include/` 子目录；误传 include 子目录会找不到 `stddef.h`，这是命令参数语义而非产品缺陷，README 与脚本均使用正确根目录。

### 七组合同结论

| 组 | 结果 | 本轮独立关键证据 |
|---|---|---|
| A 查询只读 | PASS | 自建含旧四表和数据的数据库经 `query status` 返回 exit 2 JSON `schema_incompatible`；SHA-256 前后相同。缺库不创建；空库、损坏库分别稳定返回 `schema_incompatible`、`database_error`，无 traceback。源码查询路径以 SQLite `mode=ro` 打开并只做 schema 验证。 |
| B 根与沙箱授权 | PASS | 自建 `src/main.cpp` 与 `include/shared.hpp` 实际索引，头内定义和调用可定位。含 `directory=/` 与越界 `-include` 的命令被 public CLI 在分析前以 `outside_authorized_roots` 拒绝。实际 Bubblewrap 探针观察到授权源码写入 `EROFS`、同级哨兵和 `/proc/<pid>/root` 均 `ENOENT`。 |
| C C++ 身份与上下文 | PASS | 独立双 TU、同 basename fixture：local/static、共享头 static 与匿名 namespace 均各 2 个实体；共享 external inline 仅 1 个。构造、析构、普通/静态/虚方法各一条显式 leaf 调用；嵌套 lambda 链独立归属；`sizeof/noexcept/decltype` 为 0 调用；虚/显式限定/函数指针分派依序为 virtual/direct/unknown。 |
| D 宏实例和去重 | PASS | 真实 Clang facts 与 SQLite：两次单调用宏及两次双调用宏共 6 条 calls、6 个不同 instance_id；非宏正常调用仍存在；跨 TU raw observation 33、持久 calls 32，符合共享 inline 观察去重并保留来源。 |
| E 快照与依赖一致性 | PASS | 独立索引后编辑源文件，指定旧 index_id 的 `source` 仍返回旧字节；后续语法失败索引 exit 2，旧 index_id 仍是默认且可查询。候选入口的 55 项验收另实际覆盖分析期间 cpp/header/macro/ccdb 改动和跨 TU 不一致拒绝。 |
| F 配置与诊断 | PASS | 同源文件、不同 `directory`/`-Iinc` 的两命令被 `multiple_configurations` 拒绝；真实 `#warning` 保存为 unit warning 且 status=complete；真实语法错误导致 `analysis_failed` 且没有新库发布。 |
| G CLI 合同 | PASS | 用独立新进程完成 `index → status/search/show/callers/callees/source`，成功 JSON 可解析，定位及快照内容正确；缺参数、未知 index、非法范围、缺库、空库和损坏库均为稳定 JSON 错误/exit 2。原始 `source` 字节/行预算测试随候选验收实际执行。 |

静态复核确认：query 没有调用数据库初始化/迁移；`_connection(..., readonly=True)` 和 `_validate_schema` 在查询路径中只读运行（[index.py](../../../../../CodeWeave/backend/codeweave/index.py) 的当前候选对应行 89–108、374–430）。公共索引入口在参数授权后强制 Bubblewrap，缺少 Bubblewrap 明确拒绝，且项目/依赖内容及调用锚点均由实际 Analyzer facts 导入（候选 [index.py](../../../../../CodeWeave/backend/codeweave/index.py) 对应行 124–214、216–365）。实体身份、函数栈、宏展开链和诊断写出位于候选 [main.cpp](../../../../../CodeWeave/analyzer/main.cpp) 对应行 90–239、282–340。

原始构建、公共 CLI、SQLite、facts 和独立 fixture 日志留在本机审查目录，未入工作流仓库。

## 3. 决策记录

审核先按 A–G 合同制定独立判据，再阅读候选实现与运行自有普通文件/哨兵；实施者已有报告仅在之后用于交叉对照。历史缺陷允许作为线索，但本记录的 PASS 以本轮实际候选和真实 public CLI/Clang/Bubblewrap 结果为依据。

本轮没有发现需要重新打开的确定阻塞。没有把后端合成契约代替 Clang 或隔离证据：C/D 使用真实分析器；B/G 使用公共 CLI 和实际 Bubblewrap；A/E/F 同时有数据库/失败保持的动态对照与源码静态核查。

## 4. 结论与边界

**ACCEPT：必需合同已通过，当前无未关闭阻塞；建议用户批准冻结 M0。**

这不代表用户已经验收，也不代表提交、推送、合并或 M1 已开始。裁决只绑定上述未提交候选、平台与工具链。已知且已披露的非核心边界包括：Linux Bubblewrap/user namespace 和 LLVM 18 环境；不支持 PCH/modules、任意 `-Xclang`/response/plugin 转发；同一 TU 的多配置需明确选择；只覆盖显式、可求值 CallExpr，不宣称全隐式生命周期或全程序虚分派；系统输入只保存哈希而不归档全文。

## 5. 过程记录

| 日期 | 记录 |
|---|---|
| 2026-10-19 | 核验两个仓库的 remote、分支、HEAD、staged/unstaged/untracked，定位 M0-R2 当前任务和历史独立审核。 |
| 2026-10-19 | 固定完整候选副本，记录 33 文件清单哈希；全新构建分析器并记录二进制哈希/工具链。 |
| 2026-10-19 | 运行候选验收入口（55 项）与完整 backend（56 项）；创建独立 A–G fixtures，运行 public CLI、真实 Clang 和 Bubblewrap 负例。 |
| 2026-10-19 | 结束后重新核验源候选和副本未变化；完成本独立任务与必要导航；审核期间未实施修复或作 Git 外发操作。 |
| 2026-10-19 | 用户另行指示整理 Git 并同步提交；被审核候选提交为 `608d4e7821868289028abcbdb89bfd87d9bb224c` 并推送；本审核裁决不变，用户冻结/验收未发生。 |
