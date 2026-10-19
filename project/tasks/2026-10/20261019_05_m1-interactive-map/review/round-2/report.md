# CodeWeave M1 Round-2 独立审核

## 1. 目标与范围

**唯一裁决：ACCEPT。建议用户可批准 M1 候选冻结；本审核不冻结、不提交、不推送、不合并、不发布，亦不启动 M2。**

本轮是完整新候选审核，不复用 round-1 的 `NEEDS_CORRECTION` 或 M0 的历史结论。

- 审核候选：`/home/workspace/CodeWeave_dev/m1-interactive-map-20261019/round-2/candidate`，基线 `0e9c093a5a2456814c5543ec1e52089035b4bc2e`，目标分支 `feat/m1-interactive-map`。
- 候选清单 raw SHA-256：`81b71e32a6094949338fba307a9b85983c463e0830cd4f1323d24b93c68711ae`。
- 60 个文件在开始和结束均逐一核验 byte size、SHA-256、可执行 mode；两次均与清单一致、无错误。候选目录只读，所有新 build、fixture、数据库、浏览器脚本和日志仅在本 `review/round-2` 审查区。
- 范围包括 M1 全部必需合同：M0 SQLite→CLI/HTTP 统一事实、FastAPI 本机只读边界、真实 C++ 索引、React 局部图/身份/预算、快照源码、真实 Chromium 与上一轮 P2 的关闭条件。

先阅读验收合同并写入独立 [`checklist.md`](checklist.md)，再检查候选源码和构造独立 CRLF/Unicode 反例；未先读取实施报告或以实施自验形成结论。未访问 RMC、reference、F11 或真实私有/敏感资料。

## 2. 做法与证据

### 环境与独立构建

- Python 3.12.3（工作区 `.venv`）、CMake 3.28.3、GNU C++ 13.3、LLVM/Clang 18.1.3、Bubblewrap 0.9.0、Node 22.23.3/npm 9.2.0。
- 明确使用并验证 Clang resource dir：`/home/workspace/CodeWeave_dev/.toolchain/llvm-18/usr/lib/llvm-18/lib/clang/18`，其中 `include/stddef.h` 存在。
- 从本轮候选全新 CMake 构建 `builds/analyzer/codeweave-analyzer`，SHA-256 `8562b0369cf35e6affdefe011cc83a8e65cb6e7527fa0a0649de18ab15014e94`；候选 `analyzer/main.cpp` SHA-256 `23ada772…a2842b`。没有使用 round-1 binary。

### 源码与合同核查

- `backend/codeweave/app.py` 将受信启动数据库交由同一个 `index.query()`；HTTP client 不能选择数据库。status/search/symbol/calls/neighbors/source 与 CLI 共用 M0 事实和 index_id。
- `backend/codeweave/index.py` 查询以 SQLite readonly connection、参数化 SQL、分页/limit 和序列化预算执行；source 仅按 index_id 中登记的保存快照读取。neighbors 保留 per-direction 本地图预算；unknown target 保持 `unknown:<instance_id>`，virtual 明示静态目标，不伪造运行时关系。
- `frontend/src/App.tsx` 以 index_id gate、AbortController 与 epoch 阻止旧请求串入；`graph.ts` 以 USR/instance_id 去重、处理环，并设置 100 nodes/150 edges/24 requests 预算。
- **上一轮 P2 复核：** `frontend/src/SourcePanel.tsx:17-22` 保留 UI 中的原始 Clang byte column，但通过 `sourceLocation.monacoColumn()` 将该列转为 Monaco UTF-16 column。`sourceLocation.ts:5-17` 使用每个 Unicode code point 的 UTF-8 byte size 和 JS UTF-16 `.length`，在字符内部/out-of-range 时 clamp 到合法位置；`SourcePanel.tsx:19` 处理 LF/CRLF/CR。候选新增 unit/e2e/backend 真实 facts 覆盖 Han、emoji、组合字符、边界和定义/边定位。

### 实际命令和结果

| 验证 | 实际结果 |
|---|---|
| 全新 analyzer CMake configure/build | exit 0；见 `cmake-configure.log`、`cmake-build.log`、`analyzer-sha256.txt` |
| `CODEWEAVE_LLVM_PREFIX=… CODEWEAVE_RESOURCE_DIR=… PYTHON=… bash scripts/verify_m1.sh` | exit 0；后端 **110 passed**、0 failures/errors/skips，1 条既有 Starlette/httpx 弃用 warning；fixture unittest 1/1；Node22 前端 production build；Vitest **26/26**；真实 Playwright Chromium **3/3**，其中含新 UTF-8→UTF-16 节点/边测试 |
| 自主 CRLF + mixed Unicode 真实反例：`node crlf_unicode_check.mjs` | exit 0；自有 CRLF C++ 源通过公共 CLI + 新 analyzer/Bubblewrap 生成 SQLite，HTTP fact raw byte column=**65**，Monaco position=**61**（预先按 UTF-16 定义的期望），标题仍显示 raw `:2:65`；见 `crlf-unicode-check.log`、`crlf-unicode-result.json` |
| 候选结束身份复验 | raw manifest SHA 正确、60/60 文件一致；见 `candidate-identity-after.json` |

上述自主反例的预期在执行前定义：前缀 `int crlf_entry() { const char *s = u8"汉😀"; (void)s; return ` 的 UTF-8 byte column 为 65，UTF-16 column 为 61；不由 analyzer 的结果推导。该用例额外覆盖了候选已有 LF fixture外的 CRLF 行结尾和 mixed Han+non-BMP emoji。

## 3. 决策记录

### Round-1 必需 P2 关闭

`M1-R1-P2-UNICODE-MONACO-COLUMN` **CLOSED**。

Round-1 的根因是将 Clang 物理 UTF-8 byte column 直接交给 Monaco UTF-16 API。round-2 没有改变原始 Clang facts、SQLite schema、HTTP raw call column 或 UI provenance 的真实物理列；而是在 editor boundary 转换。候选真实 e2e 对 LF Han/emoji/combining/ASCII/eol cases 通过，且本审核新增真实 Chromium CRLF mixed-Unicode edge 反例通过。因此既满足精确 editor 定位，也不会把事实伪改为 UTF-16 或混淆快照身份。

本轮审查未确认新的 P0/P1/P2/P3 缺陷。Vite 对 lazy Monaco chunk 约 694.66 kB gzip 发出 >500 kB 建议；它已懒加载、不是无界全库图或功能正确性失败，列为非阻塞工程限制。

审查期间自己的 CRLF harness 有三次失败：初始手算 oracle 误写、等待 Monaco editor 的异步时机不足、edge click 后位置读取过早。均是审核 harness 本身问题，保留原始输出；纠正测试脚本而未改候选后，最终真实 CLI/HTTP/Chromium 用例 exit 0。它们不被误述为产品失败或额外通过。

## 4. 结论与边界

**ACCEPT。** 当前固定候选的 M1 必需闭环有充分实证：新 analyzer 的真实 Clang/Bubblewrap 索引、同一 SQLite CLI/HTTP 查询内核、只读/本机边界、局部身份图/unknown/virtual 语义、snapshot/index_id 隔离、前端错误/空状态与真实 Chromium 操作均已覆盖。上一轮的 Unicode Monaco 定位问题在本轮已以源码、候选回归和独立 CRLF Chromium 反例关闭。

合同判定：

- CLI/HTTP 同一 query/index_id/facts、调用位置、快照：**PASS**。
- FastAPI 本机只读、JSON 错误、预算/分页、path/origin/host 边界：**PASS**。
- 真实 C++ 实体/调用/unknown/virtual、局部递归图和预算：**PASS**。
- React 真实 API 图、USR/instance 去重、展开/收起、搜索、加载/空/错误、索引切换防串用：**PASS**。
- 节点和调用边到 Monaco 精确定位：**PASS**，含 UTF-8/UTF-16 与独立 CRLF mixed-Unicode 验证。
- 全新构建、完整验收和真实 Chromium：**PASS**。

适用边界仍为 M1：Linux/LLVM 18/Bubblewrap/Node22 环境；简单确定性图布局；不主张 PCH/modules、复杂全程序虚分派、大规模性能优化、M2 增量/Git diff 或私有项目分析。用户是否冻结、提交、推送、合并或发布仍是独立决定，本审核未执行这些动作。

## 5. 过程记录

| 时间 | 事件 |
|---|---|
| 2026-10-19 | 阅读 M1 合同和上一轮 P2 关闭判据；建立独立检查表；核验 round-2 raw manifest 与 60 个文件身份。 |
| 2026-10-19 | 审查全候选 API/query、前端图/快照/身份及 source-location 转换链；从本轮候选全新构建 analyzer。 |
| 2026-10-19 | 运行完整 `verify_m1.sh`：110 backend、26 Vitest、3 Chromium e2e 通过，零 skip/failure/error。 |
| 2026-10-19 | 预定义 CRLF mixed-Unicode byte/UTF-16 列期待；审核 harness 三次自身失败后只修正 harness 时序/oracle，最终真实 public CLI/HTTP/Chromium PASS。 |
| 2026-10-19 | 结束前重核清单和所有 60 文件，候选未变化；写入本报告。未修改候选、旧任务或 Git 历史，未 commit/push/merge/release。 |
