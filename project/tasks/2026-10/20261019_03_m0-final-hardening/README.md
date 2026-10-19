# M0-R3：最终缺陷修复与冻结准备

## 1. 目标与范围

**实施者自验完成，独立复核 ACCEPT，候选已提交；尚未冻结。** 只修复 P1 响应文件参数绕过与 P2 status 无界，不重设 M0、不增加其他功能、不进入 M1。

| 仓库 | remote / 分支 | 实际 HEAD（开工及结束相同） | 初始状态 |
|---|---|---|---|
| CodeWeave | https://github.com/Silver-Zhang/CodeWeave.git / feat/m0-code-index | 608d4e7821868289028abcbdb89bfd87d9bb224c | staged/unstaged/untracked 均空 |
| DevFlower | https://github.com/Silver-Zhang/DevFlower.git / project/codeweave | 6a693b75be20ae6008f9f53f7cba2b9c5c091ddf | staged/unstaged/untracked 均空 |

两库位于工作区同名子目录；没有回退到旧 SHA。先读两个 AGENTS、DevFlower 当前状态/上下文、工作流及 [M0-R2 独立审核](../20261019_02_m0-r2-independent-review/README.md)，旧任务结论保持原样。本轮依据用户新确认问题开展定向修复，不把旧 ACCEPT 当本候选验收结论。

完整源码候选见 [candidate-source.json](candidate-source.json)：**34 个文件，5 个 unstaged 修改、1 个 untracked 新增，无 staged、无删除**。规范化文件清单摘要 SHA-256：`31f8d5a882ad98711c60264569a0720ce4d84ac870a6e2d6314edb53a6fadc7d`。HEAD 仅是基线，本轮完整成果为该 HEAD 加上述未提交文件。源码与全部测试/文档哈希均在清单中；结束逐文件复核一致。

## 2. 做法与证据

### 两项问题、修正及接口

| 问题 | 根因 → 修正 | 本轮反例与正常对照 | 实施者状态 |
|---|---|---|---|
| P1 响应文件 | `_safe_arguments` 消费带值选项时跳过后一个 token；LLVM 随后在全 argv 展开 @file。现于选项分组、路径归一化和丢弃输出参数之前扫描完整原 argv，任意位置 leading-@ 都以 unsafe_compilation_argument 拒绝。arguments 数组及 command 经 shlex 解析后共用该入口 | 20 组合：两种格式 × 直接或 D/U/I/include/imacros/std/x/target/o 值；分析阶段 guard 不进入、哨兵不变；@、@@、相对/绝对/带空格响应路径；合法宏、内部 @ 字符、头路径及 -std=c++17 成功 | 自验关闭，待独立确认 |
| P2 status | 默认直接返回全 units/inputs，limit 无效。现默认固定摘要；明细显式 details=units/inputs、limit/offset，稳定顺序和剩余数量；序列化预算、字段预览和无损分块均在只读查询层，不改原始数据 | 300 真实 TU、301 输入：默认摘要 752 字节；limit1 两类均 1 条；遍历全部页面无缺失/重复，重复中间页面完全一致。极长多字节/转义 command/diagnostics/path/toolchain 有界且分块字节/哈希一致；查询前后 DB SHA 相同 | 自验关闭，待独立确认 |

修改文件：

- `backend/codeweave/index.py`：完整 raw argv 扫描；status 摘要、分页、字段预算/分块及参数校验。无 schema、事实协议或索引内容改动；与基线 AST 提取出的 SCHEMA 字符串逐字一致。
- `backend/codeweave/cli.py`：新增 status 专用 `--details {units,inputs}`、`--offset`、`--field`、`--field-offset`；不适用/非法组合仍返回 JSON error/exit 2。
- `backend/tests/test_m0_final_hardening.py`：新增 32 项；真实分析、公共隔离和合成存储契约分别标注。
- `backend/tests/test_m0_r2.py`：仅将读取 status 明细的原断言切至显式 details/items；仍断言同一诊断、输入哈希和 Clang 版本，未放宽语义期待。
- `scripts/verify_m0.sh`：将新增回归纳入原先全新构建、零 Skip 门槛。
- `README.md`：完整响应文件策略与 status 新接口、预算、分页和恢复方法。

默认 status 包含 index_id/schema_version/coverage/project_root、unit_count/input_count、diagnostic_summary、编译数据库身份及限制，不再默认返回命令和依赖数组。units 按 source_file、inputs 按 path 排序；明细有 items/returned_count/total_count/remaining_count/has_more/next_offset。跨页应固定 index_id，历史索引仍可明确选择。

每次 status 成功响应最多 **32768 序列化 UTF-8 JSON 字节，含换行**，与 CLI 实际 serializer 一致。超过 2048 原始字节的字段以 truncated/preview/utf8_bytes/sha256 返回；页预算先耗尽时 budget_limited=true，继续 next_offset。命令、诊断、路径可在单行上用 field 分块取回；工具链元数据用 `--field toolchain`，每块至多 4096 原始字节，以 base64 传输并提供全字段哈希/长度/下一字节偏移。逐块解码再拼接可恢复原始存储文本，不因输出限额丢掉配置追溯。

公开入口的未支持响应文件均在分析前拒绝。底层分析器仍按既有内部受信组件合同使用 LLVM，原始真实 LLVM 测试只使用本轮自有文件；本轮没有将它改造成另一个不可信安全入口。LLVM 本地 `clang/Tooling/CompilationDatabase.h` 声明了 expandResponseFiles 包装；真实实验覆盖其实际行为。编译数据库归一化后仅写 arguments 数组，header/source 路径转为绝对值；任意前端/预处理转发、插件和配置注入参数沿用拒绝策略，沙箱继承环境仍清空。

### 实际命令、结果和旧/新对照

本地证据目录 **A**：`/home/workspace/CodeWeave_dev/m0-final-hardening-20261019`。构建、数据库、fixtures 和原始大日志只在 A 或自有 pytest 临时目录，不入库。Python 3.12.3、CMake 3.28.3、GNU C++ 13.3、LLVM/Clang 18.1.3、Bubblewrap 0.9.0、SQLite 3.45.1（JSON 支持）；版本/argv/退出码见 `A/environment.json`。

```bash
# 从工作区父目录执行
CODEWEAVE_LLVM_PREFIX="$PWD/.toolchain/llvm-18/usr/lib/llvm-18" \
CODEWEAVE_BUILD_PARENT="$PWD/m0-final-hardening-20261019" \
PYTHON="$PWD/.venv/bin/python" \
CODEWEAVE_TEST_LOG="$PWD/m0-final-hardening-20261019/logs/acceptance-cli.jsonl" \
bash CodeWeave/scripts/verify_m0.sh
```

实际新建 `A/codeweave-m0-build-cs8xrr/analyzer`，CMake 配置、构建、验收均退出 0。分析器 binary SHA-256 `8562b0369cf35e6affdefe011cc83a8e65cb6e7527fa0a0649de18ab15014e94`；C++ 源 SHA-256 `23ada77249c036cbacf2a21ddc6664601741f77d1d4cdb4d32cc85c817a2842b`。C++ 源未改，二进制哈希与前轮相同是全新实际构建的结果，没有复用旧 binary。

| 验证 | 实际结果 / 退出码 | 证据位置（A 下） |
|---|---|---|
| 现有全部 M0 + 本轮 32 项 | **87 passed，0 failures/errors/skipped，exit 0**；原 55 项函数身份、跨 TU、方法/lambda、宏、快照、SQLite 只读全部执行 | logs/acceptance.log、logs/acceptance-cli.jsonl、构建目录 results.xml |
| 完整 backend，同上新 binary 和资源目录 | **88 passed，0 failed/skipped，exit 0**；1 条既有 Starlette/httpx 弃用 warning | logs/backend.log、logs/backend-cli.jsonl |
| 300-TU 公共隔离索引 | 300 TU、301 inputs、warning=1；摘要 752 字节；limit1=1，分页 300/301 全覆盖且稳定，DB 不变 | logs/status-300-summary.json；正式验收 CLI 日志对应 test_C_status_300_real_units_and_inputs |
| 超长存储字段（合成 fixture） | 响应 ≤32768 字节；页预算提前截断、字段有预览/哈希；完整字段分块恢复字节一致；DB 不变 | logs/status-contract.log、正式验收 CLI 日志对应 extreme_fields；它不代替真实 Clang/300TU 证据 |
| 原 fixture、仓库和工作流检查 | fixture unittest 1 项、check_repository.py、devflower.py check、git diff --check 全 exit 0 | logs/fixture.log、logs/repository.log、logs/workflow.log；结构检查不等于验收批准 |

完整 backend 实际调用：将 CODEWEAVE_ANALYZER 指向上述全新 binary、CODEWEAVE_RESOURCE_DIR 指向 `.toolchain/llvm-18/usr/lib/llvm-18/lib/clang/18`，执行 `PYTHONPATH=CodeWeave/backend .venv/bin/python -m pytest CodeWeave/backend/tests -q`。真实 Bubblewrap 和公共 CLI 均实际执行；外层管理沙箱不能建 namespace，相关命令经受控提权运行，产品隔离没有 bypass/mock/fallback。

旧版用 `git archive 608d4e…` 导出至 A/baseline，使用同一轮新构建分析器和自有普通 C++ 工程，无危险输出攻击。执行 `.venv/bin/python A/compare.py` 退出 0：

- 旧 public CLI 接受 `-D @options.rsp`；仅将 rsp 从 `UNUSED -DCHANGED=1` 改为 `UNUSED`，choose 的目标由 new_target 变为 old_target，而 command_sha256 相同。新 public CLI 对同一命令返回 exit 2/unsafe_compilation_argument。
- 旧 `status --limit 1` 返回 3 个 units 和 3 个 inputs、3768 字节；新默认摘要为 758 字节、仅保留计数，无数组。新分页 limit1 的实际数量另由真实 300-TU 回归验证。
- 实际 argv/exit/stdout/stderr、两种目标及哈希判据在 `logs/old-new-comparison.json`，源文件、rsp 与 SQLite 留 A。真实 LLVM 原始 facts 测试也断言展开后的 new_target，不把字符串匹配当 LLVM 行为证据。

正常多 TU 演示：`.venv/bin/python A/demo.py`，用最终新 binary 建立新库并以独立进程执行 index/status/search/show/callers/callees/source 及两类明细，全部 exit 0。得到 **2 TU、27 实体、41 去重 calls/44 观察、2 个重载、6 个宏调用点**；两种 status limit1 均只含 1 条。全部命令及关键 JSON 在 `logs/demo.json`。

首次新增回归为 30 pass/2 fail：正常对照误用了 Clang 不支持的 `-std c++17`，真实诊断 unknown argument。纠正 fixture 为原已支持的合法 `-std=c++17` 后 2 项通过，期待仍为宏/头成功、目标正确；没有改变实现或削弱断言以掩盖失败。原阴性日志 `logs/targeted.log` 和纠正后 `logs/normal-parameters.log` 保留。另一次初始身份脚本误选 cwd 后立即失败，未改源码；纠正后保存身份，过程不伪报成功。

## 3. 决策记录

B 模式。用户明确授权两项实施、测试和必要工作流记录，不重复申请开始许可。风险集中于响应文件展开顺序与 status 输出兼容；完整原 argv 先拒绝，对正常宏/路径不做删除；status 接口显式改变并有文档/回归。field 分块仅为有界状态明细保留原始配置/诊断追溯，不扩展其他查询能力。

生产分析器、SQLite schema、索引事实、源码 snapshot 和既有安全隔离不改。未重构 M0、不修改旧任务历史；不访问/修改 RMC、核数据库、reference、F11 或真实私有工程。实施期间所有仓库修改均保留未提交；实施期间未 commit/push/merge/tag/release/reset/clean/stash。后续按用户指示提交，见 §5。没有自动冻结或开始 M1。

## 4. 结论与边界

**本轮 P1/P2 对应反例、正常对照和完整回归均在本候选上通过实施者自验，无已知未解决的本轮 OPEN/BLOCKED 项；独立复核 ACCEPT，任务已完成。** 不是用户冻结或验收。

剩余边界：只验证 Linux/Bubblewrap/LLVM 18 环境；内部分析器仍要求受信输入；响应文件不支持而明确拒绝；status 明细接口需客户端按新合同请求，跨页固定 index_id；预算限制响应输出，不宣称大库查询性能或内存上界。超长字段完整取回需按 byte offset 分块，base64 解码并拼接后核验哈希。现有复杂模板/隐式生命周期、全程序虚分派及 PCH/modules 等既有边界未扩展。1 条现有 Starlette 弃用 warning 留待独立任务处理。

候选身份/哈希固定后已停止写入，交由独立审核 Agent 验证；候选已按用户 2026-10-19 指示提交为 `0e9c093a5a2456814c5543ec1e52089035b4bc2e` 并推送；冻结、合并、tag 或发布仍待用户另行授权。

## 5. 过程记录

| 日期 | 事件 |
|---|---|
| 2026-10-19 | 核验两个仓库 clean 起点和真实 HEAD；阅读规则及前轮审查，建立本 B 模式任务，保存开工身份。 |
| 2026-10-19 | 固定旧副本并新构建分析器；复现响应文件语义/命令身份分离及 status limit 失效；实施两项修复与对应测试。 |
| 2026-10-19 | 新增定向测试初次 30/32，通过真实诊断纠正无效测试参数；原失败完整保留。300-TU 和极端字段预算/恢复验证通过。 |
| 2026-10-19 | 正式入口全新构建，87 passed/零 Skip；完整 backend 88 passed，正常多 TU CLI 全部通过。 |
| 2026-10-19 | 完整候选 34 文件与差异/哈希归档；旧任务保护性复核；更新导航与接手状态为待独立复核，停止写入。 |
| 2026-10-19 | 用户另行指示整理 Git 并同步提交；被审核候选提交为 `0e9c093a5a2456814c5543ec1e52089035b4bc2e` 并推送；用户冻结/验收仍未进行。 |
