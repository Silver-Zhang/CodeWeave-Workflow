# CodeWeave M0 独立源码与工程验收

任务：`20261018_03_m0-independent-review`。模式、状态和版本引用以 `task.json` 为准。
审查日期：2026-10-18（Asia/Shanghai）。审核者：本次独立审查会话；未参与原 M0 实现。

## 1. 目标与范围

### Executive Summary

**裁决：NEEDS CORRECTION。建议不批准 M0 冻结。**

发现 **1 项 P0、9 项 P1、3 项 P2、2 项 P3**。P0 是编译数据库中的诊断输出参数可覆盖任意当前用户可写的已有文件；独立哨兵文件已被实际覆盖。P1 涉及越界文件导入、内部链接符号误合并、跨 TU 定义丢失、头文件/方法调用漏报、lambda caller 错配、未求值表达式误报、分析与快照竞态、错误配置伪成功和配置来源混合。

纵向链路确实存在，使用真实 Clang LibTooling、真实编译数据库与持久 SQLite；独立全新构建成功。普通重载、不同文件名的 static、多个直接调用点、间接调用未知标记、新进程查询、索引完成后的旧快照读取、重建后删除关系，以及两种失败下旧库事务保留均取得正向证据。上述通过项不足以证明 M0 核心正确性。

范围：当前完整未提交成果，包括 tracked/staged/unstaged/untracked；独立构建、源码审查、自有临时 fixtures、CLI/SQLite 验证和实施报告对照。不开发、不修复、不开始 M1，不分析 RMC 或其他私有工程。

验收依据：`project/plans/NEXT_M0.md` 的五项最小验收、`BASE_v0.1.md` 的 M0 范围、原实施任务 §1、本轮用户 A—E 与独立验证要求。源码阅读前固定的判据保留于本地 `CHECKLIST.md`；验收不按退出码计票。

## 2. 做法与证据

### Reviewed Source Identity

实际工作空间是父目录，Git 仓库在两个子目录；父目录没有 Git 仓库。

| 仓库 | 实际路径 | remote / 分支 | HEAD |
|---|---|---|---|
| CodeWeave | `/home/workspace/CodeWeave_dev/CodeWeave` | `https://github.com/Silver-Zhang/CodeWeave.git` / `feat/m0-code-index` | `676f63d4c8d14f23e263f43e828deae566a9b9ec` |
| DevFlower | `/home/workspace/CodeWeave_dev/DevFlower` | `https://github.com/Silver-Zhang/DevFlower.git` / `project/codeweave` | `a466fd5b1f00737177d07ba2c425773b3c44d379` |

CodeWeave：staged 为空；unstaged 为 `.gitignore`、`README.md`、`analyzer/README.md`、`backend/codeweave/cli.py`。新增未跟踪文件为 `analyzer/{CMakeLists.txt,main.cpp}`、`backend/codeweave/index.py`、`backend/tests/test_m0_index.py`、`tests/fixtures/m0/{CMakeLists.txt,alpha.cpp,beta.cpp,shared.hpp}`。**HEAD 仍是起始版本，绝非待审实现身份。**

DevFlower：staged 为空；既有 unstaged 为 `project/{AGENT_CONTEXT.md,INDEX.md,STATUS.md}`，既有 untracked 为 `20261018_02_m0-code-index/{README.md,task.json}`。本审查未改原实施任务或 AGENT_CONTEXT；新建本任务，并维护生成 INDEX 与当前 STATUS。

候选固定方法：以 `git ls-files --cached --others --exclude-standard -z` 覆盖 29 个源码仓库文件和 26 个工作流文件；逐文件复制前/复制后 SHA-256 与副本比对全等，再从副本构建。staged/unstaged binary diff、完整未跟踪清单及原始状态单独留存。没有用旧 `.build` 二进制。忽略的旧构建/缓存不构成候选输入。

- CodeWeave 文件清单摘要 SHA-256：`b57eea40aa5b7365b20494b628d20b9249a11d4a59c092ac44fc218fe0149121`。
- DevFlower 审查前文件清单摘要 SHA-256：`fd59fa8625a0fc50f65e6cf5e7ce6e66f73bb13cfebccc366885f574fce6c2a6`。
- 清单算法及全部文件哈希、最初 Git 状态见本任务 [reviewed-source.json](reviewed-source.json)。中途及结束保护性复验见本地 `preservation-final.json`。
- 进程检查仅能看到沙箱命名空间，不能证明宿主没有其他 Agent；两次哈希、独立副本及结束复验均未发现非本审查写入。结论只绑定此候选；后续任何修改须重新绑定。

本地审查目录下文简称 **A**：`/home/workspace/CodeWeave_dev/m0-independent-review-20261018`。`A/candidate/` 是候选副本，`A/build/` 是全新构建，`A/fixtures/` 是自有 C++ 工程，`A/db/` 是新数据库，`A/logs/` 是原始输出。生产目录、原测试、RMC、核数据、reference、F11 均未写入。

### Architecture Review

真实链路：CLI `main` → `build_index` → 读取并检查 `compile_commands.json` → `subprocess.run` 启动明确指定的分析器 → Clang `CompilationDatabase` / `ClangTool` / `ASTFrontendAction` / `RecursiveASTVisitor` → JSONL → Python 内存导入 → SQLite 事务 → CLI `query`。没有发现正则或写死关系代替语义解析。

实体使用 canonical Clang USR；调用使用 `CallExpr::getDirectCallee`；每条调用写一行而非只存聚合边。数据库含 `indexes/files/symbols/calls`，实体与文件按 index 分区，UUID 选择历史索引，源码文本与 SHA-256 持久保存。查询通过共享 Python 内核，无 DevFlower 运行依赖，适合继续承载未来 Web/Agent 的共同入口。当前 `serve` 仍只是健康检查，不能视作结构 HTTP API。

主要设计缺口：USR 未结合内部链接的物理文件/TU 身份；全局 first-wins 去重不能合并后见定义；主文件过滤和 visitor 上下文不足；presumed path 被当成可信物理路径；源码在 AST 后读取而未验证一致性；编译数据库原始文本哈希不能替代完整构建配置/依赖身份。`coverage` 无条件为 complete，既没有按 TU 的覆盖，也没有持久诊断、解析未知原因或协议/分析器版本。

SQLite 的 `with connection` 对本轮实测失败保持了旧数据，连接在 finally 中关闭。外键只连到 index，不验证 call→symbol、anchor→file；`foreign_key_check` 无错误并不意味着语义关系完整。`calls` 无语义唯一约束和按 caller/target 的索引，重复命令实测重复入库。后续必须保留宏展开实例、配置和 TU 来源，不能只用行列去重而误删合法重复宏调用。

依赖方面：新构建使用本地解包 LLVM/Clang 18.1.3、GNU C++ 13.3.0、CMake 3.28.3、Python 3.12.3、pytest 9.1.1。没有系统安装或下载。生产代码没有强制开发者绝对路径；测试有本机路径默认值且只寻找 `.build`，未构建时会跳过。没有完整依赖锁、schema/JSONL 版本或规模性能证据，不能声称跨机器复现。

### Independent Test Results

每项执行前在 CHECKLIST/执行脚本中写入期望；原始 JSON 日志保存 argv、cwd、exit、stdout、stderr。`A/assessment.json` 比较语义判据；其 PASS/FAIL 是判据结果，不能解释为全部 C++ 覆盖。以下退出码为真实进程码；timeout 不伪造退出码。

独立构建实际命令（完整 argv 在 `logs/{configure,build}.json`）：

```bash
A=/home/workspace/CodeWeave_dev/m0-independent-review-20261018
L=/home/workspace/CodeWeave_dev/.toolchain/llvm-18/usr/lib/llvm-18
cmake -S "$A/candidate/CodeWeave/analyzer" -B "$A/build/analyzer" \
  -DCMAKE_BUILD_TYPE=Debug -DCMAKE_PREFIX_PATH="$L" -DCMAKE_BUILD_RPATH="$L/lib"
cmake --build "$A/build/analyzer" -j2
```

两步退出 0；产物 SHA-256 为 `b4bf115fffdbda5df7c072d12ae8c632796097ad4937cb44405fcc94b7d8de7b`。未发现构建错误；可选依赖 FFI/LibEdit/Terminfo/zstd/LibXml2 未找到但配置、编译和链接均完成。

独立运行脚本实际为 `.venv/bin/python A/run_review.py`、`run_additional.py`、`assess_evidence.py`；T15/T17 的准确复现配方另保留于 `run_tail.py`。T16 单独执行原测试。环境为 `PYTHONDONTWRITEBYTECODE=1`、`PYTHONPATH=A/candidate/CodeWeave/backend`，`LD_LIBRARY_PATH` 指向上述解包工具链的两个库目录。编译数据库由审查脚本生成，未运行导入仓库的脚本。

公共 CLI 命令形式（各场景的具体绝对路径、USR 和全部参数见对应 `logs/T*.json`，无需依赖报告省略的参数）：

```bash
python -m codeweave index --compilation-database <fixture-dir> \
  --database <audit-db> --analyzer "$A/build/analyzer/codeweave-analyzer"
python -m codeweave query <status|search|show|callers|callees|source> [value] \
  --database <audit-db> [--index-id UUID] [--limit N] \
  [--start-line N --end-line M]
```

| 测试 | 预期 | 实际结果 / 退出码 | 关键日志（均在 A/logs） |
|---|---|---|---|
| T01 多 TU、共享头、重载、重复调用 | 2 重载、2 普通 static；跨 TU 定义；所有调用点和头实体可解析 | fixture 的两次 GCC syntax-only 均 0；index 0，15 实体/18 calls。重载和不同文件名 static 正确；alpha→target 两个位置为 a.cpp:11:19 / :29。later 定义丢失，header_inline 搜索空 | `T01-*`、`T02-callees-cw-alpha.json` |
| T02 虚/间接/取地址 | 虚标记、指针 null 目标；取地址 0 调用；限定基类调用 direct | dispatch 仅 3 个调用，无取地址伪调用；虚和间接基础正确；限定 Base::run 错标 virtual。3 个方法的 callees 全为空；lambda 体 target 错归外层 | `T02-callees-cw-{dispatch,Base-run,Base-normal,Derived-run,lambda_user}.json` |
| T03 额外语义 | 方法体调用归方法；未求值表达式 0 调用；构造/析构与全局初始化有覆盖声明 | index 0/complete；4 个方法/生命周期体内 leaf 调用漏报；sizeof/noexcept/decltype 产生 3 个 direct 假调用；构造表达式和全局初始化未表示 | `T03-dispatch-extra-database.json` |
| T03 宏/模板 | 每个调用保存，锚点和目标可解释 | 宏的两个调用均保留但同为 b.cpp:13:32，仅保存展开点；twice 实例 target 没有 symbol，other_name=null。复杂宏/模板不据此通过 | `T02-callees-cw-{macro_user,template_user}.json` |
| T04 部分解析失败 | 非零，旧库保持 | 第三 TU 语法错→2；旧 DB 前后 SHA-256 完全相同。缺失输入→2 | `T04-{partial-failure,preservation,missing-input}.json` |
| T04/T12 错配置与诊断 | error 不得完整成功，诊断可查询 | `-fcodeweave-invalid-flag`：分析器 stderr `error: unknown argument...` 却退出0；CLI也0/complete，stderr空。`#warning` 无持久诊断 | `T12-{driver-direct,driver-cli,driver-status,warning-database}.json` |
| T05 索引后修改 | 旧索引读旧快照 | 从 return n 改为 n+999，查询仍返回 return n；0 | `T05-source-{before,after-change}.json` |
| T06 重启/重复/删除后重建 | 历史可查，无跨 index 污染，最新删除旧边 | 每次都是新 CLI 进程；18→18→16 calls；删 bridge 调用后 callees=[]；显式旧 UUID 仍取旧内容；0 | `T06-*` |
| T07 负例和机器协议 | 有界结果、JSON 错误、明确参数 | search limit1→1项/truncated=true。未知符号[]/0；show不提供符号也[]/0。非法路径/行号/limit/缺库→2但纯文本；坏库→1/Python traceback。缺库查询未创建 DB | `T07-*` |
| T08 伪造 #line | 必须使用物理文件，无越界导入 | index0/complete；符号错误定位到独立根外 private.txt；source 成功返回 AUDIT_ONLY_PRIVATE_SENTINEL；0 | `T08-forged-{presumed-path,search,source,database}.json` |
| T08 shell 哨兵 | 不执行 command 中的 touch | CLI0；哨兵不存在，支持本例无 shell 执行，不能证明全部参数安全 | `T08-{shell-command,shell-sentinel}.json` |
| T09 同名文件的 static | left/unit.cpp 和 right/unit.cpp 两个独立目标 | index0，只有一个 same，USR均为 c:unit.cpp@F@same#I#；right错误链接到left定义 | `T09-same-basename-{search,database}.json` |
| T09 两套宏配置 | 每条关系带配置来源或明确拒绝 | 两套互斥配置边混入同一 index，均为direct，无profile/TU来源；0/complete | `T09-two-profiles-database.json` |
| T10 plugin 哨兵 | 不加载任意插件 | 测试的 -Xclang -load 组合未触发库哨兵；index0。没有据此宣称任意代码执行 | `T10-plugin-{index,sentinel}.json` |
| T11 分析/快照之间编辑 | 拒绝竞态或保存 AST 所见字节 | 真实分析器完成后、导入前受控暂停并保存fixture；index0/complete；搜索before_symbol，source却是after_symbol | `T11-{source-race,race-search,race-source,race-database}.json` |
| T13 头定义和依赖 | inline、TU-local头static、实例和配置头均可追溯 | 6个已知直接调用的 target 均无对应 symbol；only_header 搜索空。只改 config.hpp 后，已存主文件/编译库哈希相同但目标 first→second；config.hpp 未保存 | `T13-*-database.json` |
| T14 输出边界/导入失败 | source有行/字节上限；失败回滚 | source --limit1仍返回5001行/85235字节，0；非UTF8导入→2，旧库字节不变 | `T14-{source-limit,rollback-hash}.json` |
| T15 相同编译命令重复 | 同一真实调用点1条 | index0，calls=2；同caller/target/文件/行列完全相同 | `T15-duplicate-database.json` |
| T17 已有文件保护 | 编译数据库不能指定额外输出并覆盖文件 | index0/complete；32字节已有哨兵变220字节DIAG，SHA改变 | `T17-{existing-file-overwrite,overwrite-proof}.json` |
| T16 原有测试对照 | 单独复现实施者测试，不能替代独立测试 | 新binary下原M0 4 passed/0；unittest 1 passed/0；仓库检查0。backend全套60s timeout；隔离health10s timeout，卡在TestClient/AnyIO，根因未定位 | `T16-*` |

T11 使用审查自有包装器只暂停时序，不修改真实分析器或输出 facts；它证明导入阶段的竞态，不把包装器行为当成产品自然运行过程。所有安全攻击输入只访问/覆盖 A 下自有哨兵，没有读取真实凭据。未执行 ASan/UBSan；主要阻塞是已可确定复现的语义、权限与一致性问题，不以增加测试矩阵稀释这些结论。

### Findings

下列位置指与清单哈希一致的 CodeWeave 源码。静态设计观察与当前动态证据分别标明。

#### P0-01 · 编译数据库可覆盖已有任意用户可写文件

**位置：** `analyzer/main.cpp:180-193`；`backend/codeweave/index.py:90-96`。**触发：** compile_commands 的 arguments 加 `-serialize-diagnostics <既有文件>`。ClangTool 默认参数处理没有过滤此额外输出；Python 直接启动分析器，未施加文件写入边界。

**实际证据：** T17 的唯一行为是索引审查自有 main.cpp；CLI exit0/complete。32字节哨兵被替换为220字节二进制诊断，前后 SHA 从 `aa1bb57e…556b32` 变 `bdaf7777…3a1e4a`；完整值在 `T17-overwrite-proof.json`。**影响：** 导入不可信仓库可破坏当前用户可写的源码、staged/unstaged/untracked 或其他数据；“不执行 shell”不能保证只读。没有宣称本轮已执行任意插件代码。

**推荐修正：** 明确允许的语义参数，移除/拒绝所有输出及执行副作用选项；对分析进程实施源树只读、只允许指定临时目录写入的实际隔离，不能只靠参数黑名单。**回归：** 用既有哨兵覆盖测试、诊断/模块缓存等输出参数矩阵和只读挂载验证；被拒绝输入应有明确错误，已有文件哈希保持。

#### P1-01 · #line 伪造路径导致外部文件导入与错误锚点

**位置：** `analyzer/main.cpp:66-77,89-112`；`backend/codeweave/index.py:104-125`。**触发：** 输入源码用 `#line 1 "/某可读文件"`，实体位置取 `getPresumedLoc`，导入端无源根边界或物理 FileID 验证。

**实际证据：** T08 index0；forged 的 declaration/definition 被定位到 A/sentinels/private.txt；query source 返回其中 `AUDIT_ONLY_PRIVATE_SENTINEL`，该文件并未被C++包含。普通 `/etc/passwd` 直接查询被拒绝的测试无法发现此入口。**影响：** 任意可读本地文件可进入 SQLite 并被 source 查询取出，同时定义锚点错配。未测试或读取真实敏感文件。

**推荐修正：** 用 SourceManager 物理 FileID/偏移绑定已实际读取的文件；presumed/展示路径独立保存且不用于文件访问；引入明确项目根/允许的外部依赖根并校验符号链接。**回归：** #line伪造绝对/相对路径、越根符号链接和不存在路径；只能返回物理源码快照或明确拒绝。

#### P1-02 · 同 basename 的不同 TU 静态函数被错误合并

**位置：** `analyzer/main.cpp:51-64,115`；`backend/codeweave/index.py:39-43,130-132`。**触发：** `left/unit.cpp` 和 `right/unit.cpp` 各定义 `static int same(int)`；两者 Clang USR 都是 `c:unit.cpp@F@same#I#`。

**实际证据：** T09 期望2实体，搜索仅1实体；right的调用与left共用target，定义落在left。**影响：** caller/callee与定义导航错误，破坏核心符号身份；不同文件名a.cpp/b.cpp的正例不足以验证此点。

**推荐修正：** 对内部链接实体结合物理文件身份与TU/配置上下文建立键，外部链接实体再按USR归并；不要重写成熟C++名字解析。**回归：** 同目录名/不同目录同basename的static、匿名namespace、头文件static被多个TU包含，并核对每个目标定义。

#### P1-03 · first-wins 跨 TU 去重丢掉后续定义

**位置：** `analyzer/main.cpp:62-83,115,190-192`；`backend/codeweave/index.py:130-132`。**触发：** 先分析a.cpp内`int later(int);`，后分析b.cpp内真实定义；Emitter跨整个ClangTool共用seen集合。

**实际证据：** T01 later的`definition_file/line/column`全null，b.cpp:5明确定义且有调用facts。**影响：** 索引结果依赖TU顺序；用户无法定位真实定义。**推荐修正：** 分TU输出观察事实，在导入时合并声明与定义，不能让后来的null覆盖已有定义；多定义冲突要记录。**回归：** 交换编译数据库TU顺序，声明/定义查询结果应一致，含头声明+实现定义及后见定义。

#### P1-04 · 主文件过滤漏掉项目头文件实体与调用

**位置：** `analyzer/main.cpp:127-136`；`backend/codeweave/index.py:45-49,174-177`。**触发：** inline/模板/方法或static定义放共享头文件；仅以isInMainFile决定收集，不按项目根过滤。

**实际证据：** T01 header_inline为空；T13中only_header、header_static、templ实例的6条直接调用target均没有symbol，头内leaf调用未记录。`foreign_key_check=[]`仍然如此，因为schema没有相应约束。**影响：** 常见C++头文件主体静默缺失，callee无法定义定位；不能把“头内声明恰好被cpp定义带出”当成完整头支持。

**推荐修正：** 根据项目/依赖范围收集头文件事实，保留TU与配置来源并对外部链接共享实体/调用去重；实例化覆盖不足必须标识。**回归：** 两TU共享inline、类内方法、头static及实例化模板，核对实体、caller/callee和精确锚点，不只核节点数。

#### P1-05 · 函数上下文未覆盖方法与lambda

**位置：** `analyzer/main.cpp:121-142`。**触发：** 只重写TraverseFunctionDecl；RAV分派到CXXMethodDecl/构造/析构时未入栈，lambda的operator()也未建立独立caller。

**实际证据：** T02三个实际执行target的类方法callees均[]；T03四个方法/生命周期体内的leaf调用全无。T02 lambda体内target被记为lambda_user直接调用，operator()调用本身target又无symbol。**影响：** 普通面向对象C++调用图大面积漏报，并产生错误caller。

**推荐修正：** 使用Clang AST的统一函数上下文遍历策略覆盖所有FunctionDecl派生类型及嵌套lambda；明确构造/析构表达式和全局初始化模型。**回归：** 普通/静态/虚方法、构造/析构、局部类、嵌套lambda，逐条断言caller与目标；明确隐式调用覆盖边界。

#### P1-06 · 未求值表达式被当成实际直接调用

**位置：** `analyzer/main.cpp:87-105,132-136`。**触发：** `sizeof(leaf(1))`、`noexcept(leaf(1))`、`decltype(leaf(1))(0)`中的AST CallExpr未区分求值上下文。

**实际证据：** T03 期望unevaluated有0条实际调用，入库3条direct，位置main.cpp:10的35/53/71列。**影响：** 查询把类型检查/性质判断伪装为确定调用；取地址不误报不等于无调用误报。

**推荐修正：** 保留求值上下文，未求值表达式应排除实际调用集合或作为独立事实明确标记；模板依赖和被丢弃分支单独定义。**回归：** 三个反例、requires/decltype及正常可求值调用对照；不可仅检查退出码。

#### P1-07 · AST 与源码快照存在可复现竞态

**位置：** `backend/codeweave/index.py:85-100,120-125`。**触发：** 分析器先读取源码完成AST，Python随后重新读取文件保存；期间编辑器保存。没有前后内容校验或不可变输入。

**实际证据：** T11真实分析器读取before_symbol；受控暂停后把同一fixture改为after_symbol；最终同一UUID搜索before_symbol、source返回after_symbol，index0/complete。**影响：** 正好违反“旧索引不得返回新源码”的核心要求；T05证明的是索引完成后的编辑，不能覆盖此竞态。

**推荐修正：** 从固定不可变源码/依赖快照分析并保存该快照，或对全部实际读取输入在分析前后校验并拒绝变化；编译数据库同样要固定。**回归：** 用同步屏障控制分析中/结束后导入前的源码与配置修改，要求拒绝或事实与内容哈希一致。

#### P1-08 · 编译参数错误被报告 complete，诊断和覆盖未保存

**位置：** `analyzer/main.cpp:191-198`；`backend/codeweave/index.py:94-103,120-140,167-169`。**触发：** Clang驱动报告unknown argument而tool.run仍返回0；导入只检查返回码/非空实体并丢弃成功进程stderr，coverage硬编码complete。

**实际证据：** T12 direct exit0但stderr包含error；CLI exit0/complete/stderr空，DB diagnostic=null。#warning测试同样无持久诊断。T04语法错误能正确阻断，不能证明参数错误也会阻断。**影响：** 配置可能被忽略后产生不对应真实构建的图，用户误认为分析覆盖完整。

**推荐修正：** 捕获驱动及前端的结构化diagnostics/错误计数，建立每TU/命令的状态；失败尝试与上一有效索引分开保存，成功也保留警告与覆盖边界。**回归：** 未知driver参数、错误target、缺头、部分TU失败、warning；错误不得覆盖/伪成功，状态可验证。

#### P1-09 · 配置/依赖来源不足且同一调用重复入库

**位置：** `analyzer/main.cpp:100-105,190-193`；`backend/codeweave/index.py:31-49,104-125,135-140`。**触发：** 同文件多个编译配置或重复命令；只哈希compile_commands文本、只保存主文件及facts提到的文件，calls无profile/TU字段及语义去重。

**实际证据：** T09将互斥宏配置的first/second边放入同一complete索引，无来源可分；T15相同命令两份产生同一调用点2条；T13只改无声明的config.hpp后，两索引已存主文件和编译库哈希相同，但目标first→second，config.hpp根本未保存。

**影响：** 无法重建或解释实际编译配置，重复caller和互斥关系混淆分析；UUID不同只区分两次运行，不能替代完整源码/配置身份。**推荐修正：** 持久化实际命令/工具链/目标环境、完整依赖内容身份及每条事实来源；共享事实按实体/配置/实际调用实例归并。**回归：** 多配置、相同命令重复、宏配置头变化、相同头在不同TU中的internal实体；重复去重同时保留两个宏展开中的真实调用。

#### P2-01 · CLI 错误协议不稳定且缺参数静默成功

**位置：** `backend/codeweave/cli.py:25-31,42-43`；`backend/codeweave/index.py:166-188`。**触发/证据：** T07无效path/limit为exit2纯文本；非数字参数为argparse usage文本；损坏SQLite为exit1 traceback；show不带value为exit0/空items。成功JSON含index_id，但错误没有稳定错误对象/代码。

**影响：** Agent无法统一解析错误或区别缺参数与合法无结果；traceback暴露内部路径。**推荐修正：** 按命令验证必需参数，统一JSON error/code和退出码映射，捕获sqlite3.Error；明确unknown symbol可返回空还是not-found。**回归：** 对全部T07负例解析stdout/stderr，验证一个JSON对象、无traceback、正确非零及无缺库创建。

#### P2-02 · source 查询没有实际输出上限

**位置：** `backend/codeweave/index.py:160-161,178-188`。**触发/证据：** T14 source指定5001行并加--limit1，仍返回5001行/85235字节，exit0；仅列表分支应用limit。

**影响：** 查询可倾倒整份文件，违背M0有界源码输出要求，增加隐私暴露及Agent上下文消耗。**推荐修正：** 单独的源码行数/字节上限、截断或错误协议及分页锚点。**回归：** 超长行、多字节字符、全文件范围、越界行及limit组合，输出大小应有可测试界限。

#### P2-03 · 显式限定虚方法调用被错标动态分派

**位置：** `analyzer/main.cpp:94-98`。**触发/证据：** `b.Base::run(n)`显式限定调用不会虚分派，但T02把它和`b.run(n)`都记为virtual，仅依据method->isVirtual。

**影响：** 丢掉可以确定的直接关系，降低查询准确度；本轮未把普通virtual标记误说成运行时真实派生目标。**推荐修正：** 结合调用表达式的限定语法与静态分派条件，不只看声明属性。**回归：** 普通虚调用、显式基类限定、final方法/类及非虚方法的精确dispatch断言。

#### P3-01 · schema/JSONL 无版本与查询索引

**位置：** `backend/codeweave/index.py:28-50,98,171-177`；`analyzer/main.cpp:69-105`。**触发/静态证据：** 无schema/事实协议版本、字段校验或迁移；calls无index_id+caller/target查询索引。未做规模性能测试，不能声称已出现性能故障。

**影响：** 后续工具链升级/协议演进难以安全拒绝不兼容数据，累积历史可能增加查询扫描成本。**推荐修正：** 用最小版本化协议与显式schema检查，针对真实查询加索引；删除未用_emit/_symbol_rows等局部死代码即可，无需新增复杂服务层。**回归：** 旧/错版本明确拒绝及代表规模查询计划验证。

#### P3-02 · 精确锚点和测试入口边界需补足

**位置：** `analyzer/main.cpp:89-112`；`backend/tests/test_m0_index.py:21-24`；`README.md`本地检查段。**触发/证据：** 宏两真实调用只保存同一个展开行列，没有spelling/offset/extent；测试未找到固定.build二进制就跳过，工具链默认本机路径变量未被实际使用。

**影响：** 复杂宏不能唯一映射源码中的调用子表达式；未构建时绿色测试可能不含分析器验证。现有两个宏调用行都保留，未声称被合并。**推荐修正：** 同存物理范围、spelling/expansion及实例标识；允许显式分析器路径，CI要求M0测试实际执行并记录工具链版本。**回归：** 嵌套/多层宏的不同调用锚点和未构建/已构建两种测试入口，明确复杂模板未覆盖范围。

## 3. 决策记录

用户本轮明确授权：“独立审查，不是继续开发、修复或优化代码”；允许阅读、独立构建和自有临时验证，在DevFlower新建独立任务；禁止改CodeWeave生产/测试、RMC/核数据库/reference/F11，以及commit/push/merge/rebase/reset/clean/发布和M1。按模式B完成授权范围内的工程审核，不制造模式C的G1–G4对话记录。

变更卡：唯一持久写入是独立审查目录、本任务及DevFlower导航/当前关口。风险测试仅用自有哨兵；没有修复实现、改预期或重跑reference。发现P0后立即向用户报告，并将冻结建议设为拒绝；其余证据整理继续使用自有输入，不再接触不可信实际项目。

独立性流程偏差：为获取原任务目标，首次工具读取混合README时一并看到了实施者自验摘要，早于用户要求的“初判后再读报告”。本审查如实记录这一偏差，不能宣称完全盲审。随后先固定CHECKLIST，再读源码和执行全部独立测试；自验摘要没有作为结论证据。完成独立初判后才阅读原测试实现并对照重跑。构建、缺陷及所有裁决均有当前候选独立证据。

## 4. 结论与边界

### Acceptance Decision

**唯一最终裁决：NEEDS CORRECTION。M0冻结不建议批准。**

| M0 验收条款 | 判定 | 当前证据与边界 |
|---|---|---|
| 两TU/共享头；区分重载/static；声明定义归并 | FAIL | 重载和基本跨文件调用通过；P1-02/03/04阻塞 |
| 每条直接调用能定位调用点与定义；虚/指针诚实标记 | FAIL | 多个调用点及间接未知通过；P1-04/05/06、P2-03；复杂宏锚点未完整 |
| 固定源内容、配置、覆盖诊断；编译失败不空图成功 | FAIL | 索引后快照与语法失败回滚通过；P1-07/08/09阻塞 |
| 持久索引，重启查询；错误不破坏旧数据 | PARTIAL | 独立CLI重启、历史UUID、语法/编码失败旧库保留通过；P0-01可破坏任意已有文件 |
| CLI建库/search/show/callers/callees/source/status | PARTIAL | 全部实际运行；成功为JSON且含身份；结果语义缺陷、错误协议与源码界限不通过 |
| 只读分析、源码锚点安全、保护现有工作 | FAIL | P0-01与P1-01；本审查自身保护校验无原实现改动 |
| 精确预期/错误输入/跨文件测试及原始证据 | PASS（审查交付） | 自有T01—T17，记录真实失败，不以原有4个测试PASS推导验收通过 |

审核任务完成不等于代码修复完成；实施自验、独立审核、用户验收与提交推送分别记录。原实施任务仍保持原样；用户验收未发生；没有提交、推送、合并或发布。

### Limitations & Next Steps

未验证其他LLVM版本/平台、大型生产仓库、全程序虚分派、复杂模板/宏全覆盖、PCH/modules、查询并发/写入并发、磁盘耗尽/进程崩溃恢复或跨Git版本。没有分析RMC/F11。没有证明任意插件可执行：所测插件哨兵未触发；已证实的安全问题是额外输出覆盖和伪造路径导入。

backend全套未通过本轮运行：60s timeout；health隔离10s同样timeout，栈停于TestClient/AnyIO。根因未确定，不将它归咎于产品或环境，也不复述实施者“5 passed”为本轮证据。该限制不妨碍已有P0/P1反例裁决；新一轮应单独解决/说明健康检查环境。

建议后续另授权修正任务：先关闭P0及越界导入，再修复身份/归并/visitor语义与不可变输入，补配置来源和真实diagnostics，最后统一CLI协议。修正后重新固定包含未提交文件的新候选，运行本轮反例及正向对照，由独立审查重新裁决；本轮不代为修复或开始M1。

## 5. 过程记录

| 日期 | 实际事件与结论边界 |
|---|---|
| 2026-10-18 | 核验两仓库；识别M0未提交；双读哈希复制候选，记录完整工作区身份。 |
| 2026-10-18 | 固定独立判据并在DevFlower新建审核任务；从副本全新构建。 |
| 2026-10-18 | 自有多TU、头、方法、重载/static、宏/模板、错误配置、快照/重启、SQL与安全反例运行。 |
| 2026-10-18 | 实测P0覆盖自有哨兵，立即向用户报告阻断冻结；原仓库未动。 |
| 2026-10-18 | 初判后阅读原测试并用新构建产物重跑：原M0 4 passed；原全套与health超时如实保留。 |
| 2026-10-18 | 按哈希与Git状态复核保护范围，归档独立报告，结论NEEDS CORRECTION；未冻结、未修复、未提交。 |

对照实施报告：其中“LibTooling→SQLite→CLI”和“索引完成后的快照读取”在本轮得到独立支持；原4项M0测试也可复现。但“语义USR归并、函数/方法覆盖、配置/覆盖完整、旧索引可靠、只读分析”不能从其简单fixture泛化。现有测试仅用不同basename的static、方法体无实际调用、先见定义的TU顺序、缺失编译数据库而非driver错误，以及直接拒绝/etc/passwd而非#line入口，因此漏掉本报告阻塞。报告已声明复杂宏模板与逐条诊断未覆盖，这些声明不豁免普通头文件、方法调用、配置错误或文件保护的M0标准。

大日志/构建物/SQLite/fixtures只留本地A；任务目录仅本README、task.json和一个必要候选身份清单。证据路径不是公开上传许可。本轮没有网络上传、commit、push、merge、rebase、reset、clean或发布操作。
