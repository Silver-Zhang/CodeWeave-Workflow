# M0-R2：结构语义、可信输入、快照一致性和只读查询修正

## 1. 目标与范围

**实施者自验完成，独立复核 ACCEPT，候选已提交。未批准冻结。** 本次按用户 2026-10-19 附件修复 M0-R 剩余核心问题，保留 Clang LibTooling → Python → SQLite → JSON CLI；本轮身份为开发者，不是独立审核者。

| 仓库 | 分支 | 实际 HEAD（开工及结束相同） | 开工工作区 |
|---|---|---|---|
| Silver-Zhang/CodeWeave | feat/m0-code-index | d6490539f7b204351b79393633ec9b08ea6e011d | staged/unstaged/untracked 均空 |
| Silver-Zhang/DevFlower | project/codeweave | 3ac33b8e27d971017a4dda93ded170d0b8a958fa | staged/unstaged/untracked 均空 |

两个 remote 分别为 `https://github.com/Silver-Zhang/CodeWeave.git`、`https://github.com/Silver-Zhang/DevFlower.git`，本地目录为工作区下同名子目录。结果为完整未提交候选，不把 HEAD 当成本轮实现。

源码完整清单见 [candidate-source.json](candidate-source.json)：33 个 tracked/untracked 文件，8 个修改、2 个新增文件，无删除、无 staged；包括生产代码、测试和文档。清单规范化摘要 SHA-256 为 `290550ef33cfd58b3cbce4b93347388edef793218c4546cd91b40268fb8022c1`。开工身份、binary diff 和结束复核在本地证据目录。未观察到其他写入；候选在最终验证后再次逐文件核对。

先读两个 AGENTS、DevFlower 工作流/STATUS/AGENT_CONTEXT、M0 最小合同，以及原 `m0-independent-review`、`m0-correction`。具名 `CodeWeave_M0R_Review_d6490539.md/.zip` 在本地工作区和附件目录未找到；不声称已阅读。已有本地独立审查反例仅用于定位，下面结论由本轮重新执行支持。

## 2. 做法与证据

### 缺陷对应与实施者结论

“关闭”在本表均仅指本轮反例及正常对照通过的**实施者自验关闭**，不代表独立审核关闭。

| 缺陷/原编号 | 根因 → 预期行为 | 修正及源码位置 | 本轮回归与结果 |
|---|---|---|---|
| 查询写旧库；P2-01/P3-01 | query 初始化旧 schema → 拒绝旧库且数据/版本/文件不变 | `index.py:101,374`：mode=ro、完整 schema 3 验证；新库独立初始化、原子无覆盖发布 | A：有效旧四表含数据、空、损坏、版本不兼容、伪造 schema、缺库；C：有效库重启/历史选择。关闭 |
| 可信范围/只读安全；P0-01/P1-01 | cpp 公共父目录、cwd 自动挂载 → 正常 src/inc 可用，输入不扩大宿主权限 | `index.py:124,171,199`、CLI：显式 project/dependency/toolchain/resource 根；相对路径按 cwd；拒绝转发/response/输出变体；Bubblewrap unshare-all、清环境、只读源码 | C：9 种副作用参数、#line、symlink、directory=/、授权依赖只记身份、标准 C/C++ 头、真实 EROFS/外部 ENOENT/PID 逃逸哨兵。公开入口合同内关闭；原始分析器明确内部受信组件 |
| 身份/定义/头/函数归属；P1-02～05 | 内链缺 TU，FunctionDecl 专用遍历 → 内链分、外链合、方法/lambda 归属准确、顺序无关 | `main.cpp:90,200`：统一 TraverseDecl、lambda operator、模板实例；内链物理路径+TU；外部 inline 内闭包继承 ODR 身份；导入定义/Clang ODRHash 冲突检查 | B/C：同 basename static、共享 static/匿名 namespace、外部 inline、6 类方法/生命周期体、嵌套 lambda、共享 inline lambda、简单模板、交换定义 TU、冲突定义。关闭 |
| 调用语义；P1-06/P2-03 | 未求值误报、限定调用混淆 → 可求值显式调用，未知诚实标记 | `main.cpp:149,200`：排除 sizeof/noexcept/decltype；保留 explicit qualifier；依赖模板 unknown-dependent，指针 unknown-function-pointer | B/C：uneval 为 0；取地址不增调用；virtual/direct/unknown 顺序和目标断言。关闭 |
| 调用实例；P1-09/P3-02 | 只有 spelling 行列 → 独立宏实例不合并，跨 TU 观察去重 | `main.cpp:171`、`index.py:216,352`：spelling/expansion 链/offset/hash、内容生成实例键；SQLite 唯一键与 call_units 来源 | B 原始事实、C 入库：两个 HIT 加两个 TWO 共 6 calls，6 instance_id；共享 inline 调用仅 1 条、2 TU 来源；返回 calls=存储数。关闭 |
| 输入快照；P1-07/P1-09 | 同路径后写覆盖、丢宏头 → AST 字节与位置一致，不混版本 | `main.cpp` EndSourceFileAction、`index.py:216`：实际 buffer 字节/哈希、全部项目依赖、每 TU 来源；不同版本拒绝 | A 合成冲突；C 屏障后改 cpp/header/macro/ccdb 均保存原输入；两个 TU 间改 header/macro 均拒绝且旧索引可查；索引后编辑/重启查询通过。关闭 |
| 配置/诊断；P1-08/09 | 只看 tool.run、unit 写死 → driver/frontend error 阻断、warning 可查 | `main.cpp:282`、`index.py:171,284`：真实 DiagnosticConsumer；cwd+规范参数+source+工具链身份；重复命令去重、同 TU 多配置拒绝 | A 合成错误/配置上下文；B 真 driver error 非零；C 非法参数、target、缺头、语法、部分 TU、warning、重复/互斥配置。错误保留旧默认，warning 进入 unit。关闭 |
| JSON/预算/验收；P2-01/02/P3-01/02 | traceback、无界 source、旧 binary/Skip 可绿 → 稳定有界 CLI、真实执行 | `cli.py`、`index.py:374`、`verify_m0.sh`：错误对象+exit 2；200 行/32768 原始字节；每次全新构建、核验哈希、JUnit 零 Skip 门槛 | C 缺参/ID/路径/范围/库/超长 ASCII、多字节、全文件、小 limit；验收 55 项零失败零跳过。关闭 |

数据库保留 index→files/units、unit→files、symbol/call→unit 及 call→caller/file 外键。项目实体以外的静态 callee 可只保留 USR；不伪称已有项目定义。失败候选不入库，不另建失败尝试历史；CLI 返回实际诊断，旧成功索引及其状态保持可查。`status` 的 units_complete 只表示所选编译单元成功，随响应明确列出语义限制。

### 三层验证、环境与实际命令

本地原始证据目录 **A**：`/home/workspace/CodeWeave_dev/m0-correction-r2-20261019`。日志不入库。版本：Python 3.12.3、CMake 3.28.3、GNU C++ 13.3、LLVM/Clang 18.1.3、Bubblewrap 0.9.0；详细版本/二进制哈希见 `A/environment.json`，实际动态库见 `A/logs/runtime-libraries.log`。

```bash
# 在工作区父目录运行；源码仓库本身不依赖 DevFlower。
CODEWEAVE_LLVM_PREFIX="$PWD/.toolchain/llvm-18/usr/lib/llvm-18" \
CODEWEAVE_BUILD_PARENT="$PWD/m0-correction-r2-20261019" \
PYTHON="$PWD/.venv/bin/python" \
CODEWEAVE_TEST_LOG="$PWD/m0-correction-r2-20261019/logs/acceptance-current-cli.jsonl" \
bash CodeWeave/scripts/verify_m0.sh
```

该入口为当前源码创建全新 `A/codeweave-m0-build-Ag1HVd/analyzer`，配置、构建和测试退出码均 0。binary SHA-256：`8562b0369cf35e6affdefe011cc83a8e65cb6e7527fa0a0649de18ab15014e94`；`main.cpp` SHA-256：`23ada77249c036cbacf2a21ddc6664601741f77d1d4cdb4d32cc85c817a2842b`。

| 层/入口 | 实际执行与边界 | 结果 / 原始日志 |
|---|---|---|
| A 后端契约 | 10 项：只读 schema、合成协议/冲突/diagnostic、配置身份、缺沙箱拒绝；不能代替真实 Clang | 全通过；`contracts-raw.log` 及正式验收 |
| B 原始真实 Clang | 2 项直接分析自有受信 fixture：实际 buffers/宏实例；driver error/逐 TU diagnostics；不是安全入口证明 | 全通过；`acceptance-current-cli.jsonl` 标记 B 的 argv/exit/facts hash |
| C 公共进程/真实隔离 | 34 项，含 2 项精确语义集成；真实 Bubblewrap→analyzer→SQLite→新 CLI 进程；屏障只控制时序，不改写事实 | 全通过；`acceptance-current-cli.jsonl` |
| 原有 M0/M0-R | 原 9 项，仅按显式项目根新合同调整调用，缺 binary 改为失败 | 全通过 |
| 专用 M0 汇总 | A+B+C 46 项加原 9 项 | **55 passed，0 failed/errors/skipped，exit 0**；`acceptance-current.log`、构建目录 results.xml |
| 完整 backend | 同最终验收 binary、资源目录，`PYTHONPATH=CodeWeave/backend .venv/bin/python -m pytest CodeWeave/backend/tests -q` | **56 passed，0 failed/skipped，exit 0**；`backend-current.log`。1 条既有 Starlette/httpx 弃用 warning，与 Clang 诊断测试分开 |
| fixture/仓库/工作流 | fixture unittest、check_repository.py、devflower.py check、git diff --check | 全退出 0；结构检查不等于正确性或批准 |

外层受管理沙箱最初禁止创建 namespace，8 个原回归因此失败；随后通过受控提权实际运行产品 Bubblewrap，未 mock 或去掉隔离。中间完整测试曾发现标准头未找到，修正资源目录入口与固定受信驱动路径后，`stddef.h/stdint.h/vector` 正常对照通过。阴性日志保留于 `first-tests.log`、`backend-full.log`；不将这些旧中间结果当最终候选结论。

### 安全旧/新对照与多 TU 演示

旧提交通过 `git archive d6490539…` 导出到 A/baseline，另建 A/baseline-build，未改共享分支。`A/baseline_compare.py` 的本轮实测：共享头 static 只有 1 个、普通方法体调用 0、6 个宏调用存为 3、decltype 额外 1 个调用；真实旧四表含数据查询退出 1/traceback 且文件改变。对应新测试分别为 2、1、6、0，以及 exit 2/schema_incompatible、原字节不变。见 `logs/baseline-comparison.json`。第一次旧库对照误用了简化的四表形状，未触发预期 traceback；纠正为真实旧 schema 后重新验证，没有改生产实现来迎合预期。未重跑旧版本危险的任意输出写入攻击，不伪造其新旧对照。

`A/demo.py` 用最终 binary、正常多 TU 自有工程，真实调用 index/search/show/callers/callees/source/status。每条 argv、exit、stdout/stderr 见 `logs/demo-current.json`。新库结果：**2 TU、27 实体、41 去重调用、44 AST 观察；2 个 leaf 重载；macros 的 6 个调用均定位到 right/unit.cpp:7**。逐 CLI 启动新进程，源码行返回 `HIT()+HIT()+TWO(1)+TWO(2)`。历史 index_id 选择、失败后旧默认与源码保存由 C 回归单独验证。

## 3. 决策记录

用户最新附件明确将本会话从独立审核切换为开发并授权本轮修改，不重复请求开始许可。采用 B 模式，新任务短名 m0-correction-r2；原审核和原修复任务均不改。

变更卡：改动仅限分析器、内核/CLI、必要测试/入口/稳定文档，以及本任务和导航；风险集中于协议/schema 兼容、实体合并和输入边界。采用 protocol 2/schema 3；旧库只读拒绝，新路径重建，不迁移/覆盖。每 TU 多配置明确拒绝，正常不同 TU 命令合法。直接分析器按内部受信组件约束，公开入口始终经过参数授权及实际隔离。已知风险通过对应反例与正常对照验证，未进行无关架构、系统安装或网络上传。

实施期间所有改动保留未提交，可供逐文件审查；未 reset/clean/stash 或覆盖他人改动。RMC、核数据库、reference、F11 和其他真实私有项目未访问。实施期间未提交/推送/合并/发布或启动 M1；后续按用户指示提交，见 §5。

## 4. 结论与边界

**本轮六组核心修正及 JSON/预算回归在所列环境、fixture 和命令下自验通过，无已知待解决的本轮核心 OPEN/BLOCKED 项；独立复核 ACCEPT，任务已完成。** 这不是用户验收或冻结批准。

明确限制：Linux Bubblewrap/user namespaces 必需；LLVM 18 之外未验。参数白名单以已支持语义为范围，response/plugin/任意前端转发、PCH/modules 明确拒绝；同 TU 多配置需用户先选择。只保证所测显式调用和基本方法/头/lambda/模板；全隐式生命周期、全程序虚分派、复杂模板/宏全部组合、大型工程性能不在本轮。系统/授权依赖只存读取身份，不开放全文；系统头及工具链动态库未整体归档，不能宣称完整构建可复现。Clang ODRHash 冲突检查不是全程序 ODR 证明。`source` 预算按原始字节计，JSON 转义后可更大。

实施者自验已完成；独立复核 ACCEPT；候选已按用户 2026-10-19 指示提交为 `608d4e7821868289028abcbdb89bfd87d9bb224c` 并推送；用户验收与冻结未发生；不自行冻结或进入 M1。

## 5. 过程记录

| 日期 | 事件、失败及纠正 |
|---|---|
| 2026-10-19 | 核验 clean 起点、读取合同与旧报告，保存初始哈希；创建 B 模式任务。 |
| 2026-10-19 | 分组实施只读库、可信根/参数、函数/身份/宏、buffer/配置/diagnostics；全新构建。 |
| 2026-10-19 | 外层 namespace 限制如实记录；通过受控提权运行真实产品隔离；未采用 fallback。 |
| 2026-10-19 | 语义与同步反例通过；标准头对照发现缺口，补资源配置与驱动上下文；旧库对照 fixture 修正为真实 schema。 |
| 2026-10-19 | 最后交叉检查补共享 inline 内 lambda 身份与依赖模板标记；再次全新验收 55/55，完整 backend 56/56。 |
| 2026-10-19 | 最终 CLI 演示、候选 33 文件哈希与差异归档、保护性复核。 |
| 2026-10-19 | 用户另行指示整理 Git 并同步提交；被审核候选提交为 `608d4e7821868289028abcbdb89bfd87d9bb224c` 并推送；用户冻结/验收仍未进行。 |
