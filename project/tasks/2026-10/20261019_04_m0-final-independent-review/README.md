# CodeWeave M0-R3 独立审核报告

## 1. 目标与范围

**唯一裁决：ACCEPT。建议用户批准 M0 冻结；本审核不执行冻结、提交、推送、合并、tag、发布或 M1。**

审核对象为完整未提交候选，而非仅 Git HEAD：

- CodeWeave：`feat/m0-code-index`，HEAD `608d4e7821868289028abcbdb89bfd87d9bb224c`；5 个 unstaged 修改（`README.md`、`backend/codeweave/cli.py`、`backend/codeweave/index.py`、`backend/tests/test_m0_r2.py`、`scripts/verify_m0.sh`）及 1 个 untracked 文件（`backend/tests/test_m0_final_hardening.py`）；无 staged/删除。
- DevFlower：`project/codeweave`，HEAD `6a693b75be20ae6008f9f53f7cba2b9c5c091ddf`。独立审核工作流任务由工具建为 `20261019_04_m0-final-independent-review`；本报告保留于本 detached worktree 的 `review/`，以供同步。
- 候选清单：34 文件。按 `sha256(json.dumps(files, sort_keys=True, separators=(",", ":")).encode())` 重新计算为 `31f8d5a882ad98711c60264569a0720ce4d84ac870a6e2d6314edb53a6fadc7d`，与清单一致；复制到 `/home/workspace/CodeWeave_dev/m0-final-independent-review-20261019-claude/candidate` 前逐文件 SHA-256/mode 一致，结束时源候选再核验仍为 34/34 一致。源工作树状态未变。

审核范围是 M0-R3 的两项必过合同：P1（公共索引入口对响应文件 token 的前置拒绝）和 P2（有界 status 摘要、分页、字段恢复、只读）。同时回归 M0 全套、完整 backend 和一组独立多文件 C++ 工程。未访问 RMC、核数据库、reference、F11、凭据或任何真实私有工程；所有动态输入、数据库、哨兵、构建和大日志均为审核目录自有内容。

既有 M0 范围仍适用：Linux/Bubblewrap、LLVM 18；无 PCH/modules、全程序虚分派或隐式生命周期保证。这些已知产品边界不覆盖或削弱 P1/P2 的结论。

## 2. 做法与证据

### 环境、独立性与构建

- Python 3.12.3：`/home/workspace/CodeWeave_dev/.venv/bin/python`
- CMake 3.28.3、GNU C++ 13.3、Bubblewrap 0.9.0、LLVM/Clang 18.1.3。
- 显式资源目录：`/home/workspace/CodeWeave_dev/.toolchain/llvm-18/usr/lib/llvm-18/lib/clang/18`，并现场断言 `include/stddef.h` 存在（SHA-256 `23b9e2c5…9a38625`）。
- 从冻结副本全新 CMake 生成 `/home/workspace/CodeWeave_dev/m0-final-independent-review-20261019-claude/builds/independent-analyzer/codeweave-analyzer`；产物 SHA-256 `8562b0369cf35e6affdefe011cc83a8e65cb6e7527fa0a0649de18ab15014e94`，不是复用实施 binary。
- Bubblewrap 以产品风格 `--unshare-all --clearenv --proc --dev --ro-bind /usr,/lib,/lib64` 运行 `/usr/bin/true`，exit 0。

### 静态调用链审查

1. `backend/codeweave/index.py:114-120` 在 arguments 格式直接取字符串数组、在 command 格式通过 `shlex.split` 生成同一 argv。
2. `index.py:128-132` 在任何分组、路径解析、输出参数剔除或安全 ccdb 生成之前扫描**完整原 argv**，每个 leading-`@` token 都返回 `unsafe_compilation_argument`。`index.py:179-204` 对每条 ccdb 记录先调用该入口，才序列化安全 `arguments`。
3. `index.py:395-460` 的默认 status 仅查询摘要；units/inputs 必须显式 details。分页按 `source_file`/`path` 排序，SQL 只读连接来自 `index.py:93-100` 和查询入口 `index.py:463-521`。`_status_size` 与 CLI 的 `ensure_ascii=False, sort_keys=True` serializer 对齐并计入换行；单字段预览提供 `truncated/utf8_bytes/sha256`，字段读取按原始 UTF-8 byte offset base64 分块。
4. `cli.py:39-61` 将新参数限制于 query/status，再交由 `query()` 作语义校验。查询路径不调用 schema 初始化、迁移或写事务。

### P1：真实 LLVM 行为和公共入口拒绝

独立脚本：`review/independent_check.py`；原始结果：`review/independent-results.json`、`review/independent-check.log`。

- 使用审核自有 `main.cpp`、`options with spaces.rsp`，直接运行受信内部 analyzer。完全相同的 `c++ -D @options.rsp -c main.cpp` 让 LLVM 实际展开响应文件，facts 中唯一 call target 为 `c:@F@new_target#`，exit 0。这证明问题不是 Python 字符串匹配假设。
- 再通过**公共** `codeweave index`，以不应执行的 guard analyzer 和普通自有 sentinel 验证拒绝时序。`arguments` 与 shell-quoted `command` 两种 ccdb 格式，分别覆盖直接 token 以及 `-D/-U/-I/-include/-imacros/-std/-x/-target/--target/-o` 后的 token：22 项均 exit 2、错误码 `unsafe_compilation_argument`、guard 未进入、数据库未创建、sentinel 仍为 `UNTOUCHED`。
- 额外 8 项（两格式的 `@`、`@@nested.rsp`、相对 `@relative.rsp`、绝对路径）同样拒绝；合计 30 项。
- 两格式正常对照都实际索引成功：`-DMAIL="a@b"`、`-DNORMAL=7`、带空格前缀无关的正常 `-I inc`、`-std=c++17`；保存的安全 command 仍包含宏和标准选项。内部 `@` 未误判。

**P1 状态：CLOSED。** 未发现另一个 Python/ccdb/LLVM driver 响应文件入口可使 leading-`@` 在公共分析前绕过检查。

### P2：真实 300-TU、预算、恢复和 SQLite 只读

- 独立真实 C++ 项目生成 300 个 TU、共享本地头；公共 CLI + 新 analyzer 实际完成 `units=300`、`inputs=301`、warning=1，且数据库无变更（SHA-256 `c28b737b…7bc25b9b`）。默认摘要 836 serialized UTF-8 JSON bytes，不含 items/units/inputs/toolchain 列表。
- `--details units|inputs --limit 17` 各自遍历所有页：units 300、inputs 301，各 18 页；无重复、无遗漏、稳定字典序，`next_offset == offset + returned_count`，末页 `next_offset=null`。每个实际响应都断言不超过 32768 bytes。
- 索引中 `toolchain_roots` 通过 field chunk 读取并等于唯一正确资源目录，而不是工作区根；确认这轮是真正受限工具链授权配置。
- 自建 SQLite schema-3 极端元数据数据库（仅用于存储/序列化契约，**不替代**真实 Clang 300-TU 验证）：多字节、控制字符、转义以及超长 command/diagnostics/path/toolchain。`--limit 200` 先由预算截为 5 项并显式 `budget_limited=true`；四种字段分别无损重组 63,033 / 50,037 / 72,000 / 99,015 UTF-8 bytes，重组 SHA-256 与 API 逐块报告一致。所有响应 ≤32768 bytes，DB 前后 SHA-256 `ad2c8baf…dce8605` 一致。
- 非法 row offset、超过 SQLite 整数范围 offset、孤立 field-offset、field/details 不匹配、EOF 外 field offset 均稳定 exit 2，错误码分别为 `invalid_offset` 或 `invalid_arguments`。

**P2 状态：CLOSED。** 默认输出有界、明细分页可追溯、超长字段可恢复，并保持 SQLite 查询只读。

### 回归与语义抽查

| 验证 | 独立实际结果 |
|---|---|
| `scripts/verify_m0.sh`，冻结副本、全新 build | **87 passed，0 failed/errors/skipped**，exit 0；脚本自行发现正确 resource-dir |
| 全部 backend 测试，独立 analyzer、显式正确 resource-dir | **88 passed**，exit 0；仅 1 条既有 Starlette/httpx 弃用 warning |
| 独立普通两 TU 多文件工程 | 公共 CLI `index/status/search/show/callers/callees/source/status --details` 均成功；`shared(int)` 跨文件合并为一个 USR、2 callers、1 callee；source 为索引快照；status 为 2 TU/3 inputs |

语义抽查原始 JSON：`review/semantic-queries.json`。关键实现/验证原始日志见审核根的 `logs/` 以及本 worktree 的 `review/`。

## 3. 决策记录

用户已授权本地独立审核、独立测试和必要工作流记录；明确禁止源码修复、候选改写、旧档案修改、commit/push/merge/rebase/reset/clean/stash/tag/发布/M1。审核没有执行这些禁止动作。

流程偏差如实记录：我在完成“先独立动态初判、后阅读实施 README”的顺序前，已读取本轮实施 README。该 README 未被用作本结论的运行证据；后续按源码和上列自定义反例/正常对照在冻结副本、独立新 build 上重新执行，并将实施记录只用于比较。故本审核不是严格盲审，但技术结论有独立的可复现实证。

另有两次审核环境/脚本错误，均保留而未计作通过：

1. 初次外部 resource-dir 的 `find` 深度错误，产生空值并被 `Path('')` 解释为工作区根；初次独立动态日志有 `realpath: '': No such file or directory`。该轮 P1/P2 动态结果和其 `many.db` 不作为正确隔离/工具链配置证据。
2. 初次完整 backend 同样因空 resource-dir 使 `test_C_standard_headers` 失败（87 pass/1 fail）；随后用已验证的 Clang 18 resource-dir 重跑为 88 pass。初版自有脚本还含 Python chained-comparison 断言错误，失败后仅修复审核脚本断言、未改产品候选，重跑 PASS。

验收入口本身不受前述外部变量问题影响：其脚本内部自动探测正确 resource-dir，87 项真实执行。所有有效 P1/P2 独立结论以随后显式正确 resource-dir 的 `independent-results.json` 为准。

## 4. 结论与边界

**ACCEPT。** P1 和 P2 均已由独立源码审查、全新 analyzer、真实 LLVM、公共 CLI、Bubblewrap、真实 300-TU 项目、独立极端 JSON/SQLite 契约和完整回归覆盖；没有未关闭 P0/P1/P2 阻塞，也未发现新增确定缺陷。

建议用户批准 **M0 冻结**，但此建议不构成冻结或用户验收本身。裁决仅绑定本报告所列 34 文件、候选清单摘要、Linux/LLVM 18/Bubblewrap 环境；不外推至未测平台、PCH/modules、复杂模板、全程序虚分派或大规模性能。

- 旧 P1：**CLOSED**。
- 旧 P2：**CLOSED**。
- 新问题：无。
- 未关闭阻塞：无。

## 5. 过程记录

| 时间 | 事件 |
|---|---|
| 2026-10-19 | 核对两个仓库 remote/branch/HEAD/status，读取规则、M0 合同和历史 R2 独立审核；固定 34 文件候选副本并核对清单算法。 |
| 2026-10-19 | 发生流程偏差：在动态独立初判前读取本轮实施 README；后续以冻结副本的独立代码和测试补足运行证据。 |
| 2026-10-19 | 全新构建 analyzer；验收入口 87/87；源候选结束身份复核一致。 |
| 2026-10-19 | 初轮外部 resource-dir 检索错误和审核脚本断言错误被保留；未将其解释为产品 PASS。 |
| 2026-10-19 | 使用验证的 resource-dir 重跑：完整 backend 88 pass；独立 P1 LLVM/公共 CLI 及 P2 300-TU/极端字段 PASS；完成语义抽查。 |
| 2026-10-19 | 完成报告；未改变 CodeWeave 候选、旧档案或 Git 历史，未作 Git 提交、推送、发布或向未获授权的第三方上传。固定候选/审核材料发送给 Claude 模型属于用户明确授权的本次审核范围。 |
| 2026-10-19 | 用户另行指示整理 Git 并同步提交；被审核候选提交为 `0e9c093a5a2456814c5543ec1e52089035b4bc2e` 并推送；本审核裁决不变，用户冻结/验收未发生。 |
